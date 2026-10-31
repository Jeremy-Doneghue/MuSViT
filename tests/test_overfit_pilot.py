import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import torch
from transformers import ViTConfig, ViTModel

from experiments.full_page_omr.overfit_pilot import CachedGreedy, greedy, make_model
from experiments.full_page_omr.pilot_data import PilotDataset, export_pilot, pilot_scores
from experiments.full_page_omr.score_codec import W2I, decode, encode


class OverfitPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temporary.name) / "dataset"
        cls.manifest = export_pilot(cls.directory)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def model(self):
        torch.manual_seed(4)
        encoder = ViTModel(ViTConfig(image_size=32, patch_size=16, hidden_size=32,
                                    num_hidden_layers=1, num_attention_heads=4, intermediate_size=64))
        return make_model(encoder, resolution=32, maxlen=600, width=32, layers=2)

    def test_self_contained_distinct_pages_and_no_invisible_metadata(self):
        records = self.manifest["records"]
        self.assertEqual(len(records), 8)
        self.assertEqual(len({r["composition_id"] for r in records}), 8)
        self.assertEqual(len({r["image_sha256"] for r in records}), 8)
        self.assertTrue(all(r["page"] == r["total_pages"] == 1 for r in records))
        for name, source in pilot_scores():
            root = ET.fromstring(source)
            self.assertFalse(any(root.find(tag) is not None for tag in ("work", "identification", "credit")))
            self.assertTrue(root.findtext("part-list/score-part/part-name"))
            self.assertTrue(decode(encode(source)))

    def test_next_token_shifts_include_profile_and_eos(self):
        data = PilotDataset(self.directory, resolution=32, limit=1)
        image, inputs, labels = data[0]
        self.assertEqual(image.shape, (1, 3, 32, 32))
        self.assertEqual(image.dtype, torch.float32)
        self.assertGreaterEqual(image.min().item(), 0)
        self.assertLessEqual(image.max().item(), 1)
        self.assertEqual(inputs[0, 0].item(), W2I["<bos>"])
        self.assertEqual(labels[0, 0].item(), W2I["musvit-score-v1"])
        self.assertEqual(labels[0, -1].item(), W2I["<eos>"])
        self.assertTrue(torch.equal(inputs[0, 1:], labels[0, :-1]))

    def test_cached_logits_match_full_prefix_at_every_position(self):
        model = self.model().eval()
        prefix = encode(next(pilot_scores())[1])[:20]
        with torch.no_grad():
            features = model.forward_encoder(torch.rand(1, 3, 32, 32)).permute(0, 2, 1)
            cache = CachedGreedy(model, features)
            full = model.forward_decoder(features, torch.tensor([prefix])).logits
            for index, token in enumerate(prefix):
                torch.testing.assert_close(cache.step(token, index), full[0, :, index], atol=2e-6, rtol=2e-5)

    def test_correct_shift_backward_and_frozen_encoder(self):
        model = self.model()
        image, inputs, labels = PilotDataset(self.directory, 32, 1)[0]
        with torch.no_grad():
            features = model.forward_encoder(image).permute(0, 2, 1)
        logits = model.forward_decoder(features, inputs).logits
        loss = torch.nn.functional.cross_entropy(logits, labels)
        loss.backward()
        self.assertTrue(torch.isfinite(loss))
        self.assertGreater(model.adaptor.weight.grad.abs().sum().item(), 0)
        self.assertGreater(model.decoder.embedding.weight.grad.abs().sum().item(), 0)
        self.assertTrue(all(not p.requires_grad and p.grad is None for p in model.encoder.parameters()))

    def test_greedy_eos_and_truncation_are_not_repaired(self):
        model = self.model().eval()
        with torch.no_grad():
            features = model.forward_encoder(torch.rand(1, 3, 32, 32)).permute(0, 2, 1)
            model.decoder.out_layer.weight.zero_()
            model.decoder.out_layer.bias.zero_()
            model.decoder.out_layer.bias[W2I["<eos>"]] = 10
            self.assertEqual(greedy(model, features, 10), [W2I["<bos>"], W2I["<eos>"]])
            model.decoder.out_layer.bias.zero_()
            model.decoder.out_layer.bias[W2I["<text>"]] = 10
            result = greedy(model, features, 5)
            self.assertEqual(len(result), 5)
            self.assertNotEqual(result[-1], W2I["<eos>"])

    def test_overwrite_and_manifest_mismatch_rejected(self):
        with self.assertRaises(FileExistsError):
            export_pilot(self.directory)
        with tempfile.TemporaryDirectory() as directory:
            manifest = dict(self.manifest, vocabulary_sha256="incorrect")
            Path(directory, "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "vocabulary mismatch"):
                PilotDataset(directory)


if __name__ == "__main__":
    unittest.main()
