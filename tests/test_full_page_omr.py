import unittest
from unittest.mock import patch

import torch
from transformers import ViTConfig, ViTModel

from experiments.full_page_omr.runtime import runtime_settings
from experiments.full_page_omr.smt_foundation.configuration_smt import SMTFoundationConfig
from experiments.full_page_omr.smt_foundation.modeling_smt import (
    IMPL_DICT,
    SMTFoundationModelForCausalLM,
)


class FullPageOMRTests(unittest.TestCase):
    def make_model(self, device="cpu"):
        # A real, small ViT exercises the encoder/adapter/decoder together
        # without downloading weights or loading any training datasets.
        encoder = ViTModel(ViTConfig(
            image_size=32, patch_size=16, hidden_size=32,
            num_hidden_layers=1, num_attention_heads=4, intermediate_size=64,
        ))
        config = SMTFoundationConfig(
            foundation_architecture="ViTMAEBase", foundation_weights="unused",
            maxh=64, maxw=64, maxlen=8, out_categories=5,
            d_model=16, dim_ff=32, num_dec_layers=2,
            w2i={"<bos>": 1}, i2w={0: "<pad>", 1: "<bos>", 2: "<eos>", 3: "4c", 4: "<b>"},
        )
        with patch.dict(IMPL_DICT, {"ViTMAEBase": [ViTModel, 32]}), patch.object(
            ViTModel, "from_pretrained", return_value=encoder
        ):
            return SMTFoundationModelForCausalLM(config).to(device)

    def check_training_and_prediction(self, device):
        torch.manual_seed(7)
        model = self.make_model(device)
        self.assertEqual(model.positional_2D.pe.shape, (1, 16, 4, 4))
        self.assertEqual(model.positional_2D.pe.device.type, device)
        self.assertEqual(model.decoder.positional_1D.pe.device.type, device)
        # Deterministic buffers are regenerated, preserving older checkpoints.
        self.assertFalse(any(key.endswith(".pe") for key in model.state_dict()))
        for resolution in (32, 64):
            image = torch.rand(1, 3, resolution, resolution, device=device)
            tokens = torch.tensor([[1, 3, 4, 3]], device=device)
            labels = torch.tensor([[3, 4, 3, 2, 0]], device=device)
            model.zero_grad(set_to_none=True)
            result = model(image, tokens, labels=labels)
            self.assertEqual(result.logits.shape, (1, 5, 4))
            self.assertTrue(torch.isfinite(result.loss).item())
            result.loss.backward()
            self.assertTrue(torch.isfinite(model.adaptor.weight.grad).all().item())
            self.assertGreater(model.adaptor.weight.grad.abs().sum().item(), 0)
            self.assertIsNotNone(model.decoder.embedding.weight.grad)
            self.assertTrue(all(p.grad is None for p in model.encoder.parameters()))
        model.eval()
        with torch.no_grad():
            model.decoder.out_layer.weight.zero_()
            model.decoder.out_layer.bias.zero_()
            model.decoder.out_layer.bias[2] = 10
        sequence, _ = model.predict(image)
        self.assertEqual(sequence, [])  # EOS terminates generation immediately.

    def test_cpu_training_and_prediction(self):
        self.check_training_and_prediction("cpu")

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS unavailable")
    def test_mps_training_and_prediction(self):
        self.check_training_and_prediction("mps")

    def test_runtime_defaults(self):
        with patch("torch.cuda.is_available", return_value=False), patch(
            "torch.backends.mps.is_available", return_value=True
        ), patch("sys.platform", "darwin"):
            self.assertEqual(runtime_settings(configured_workers=20), ("mps", "32-true", 0))
            self.assertEqual(runtime_settings("cpu", "32-true", 2), ("cpu", "32-true", 2))
        with patch("torch.cuda.is_available", return_value=True), patch("sys.platform", "linux"):
            self.assertEqual(runtime_settings(configured_workers=20), ("cuda", "16-mixed", 20))
        with patch("torch.cuda.is_available", return_value=False), patch(
            "torch.backends.mps.is_available", return_value=False
        ), patch("sys.platform", "linux"):
            self.assertEqual(runtime_settings(), ("cpu", "32-true", 0))
        with self.assertRaises(ValueError):
            runtime_settings(num_workers=-1)


if __name__ == "__main__":
    unittest.main()
