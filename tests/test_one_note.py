from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import torch
from transformers import ViTConfig, ViTModel

from experiments.full_page_omr.datasets.clean_page_data import CleanPageDataset, check_disjoint, musical_fingerprint
from experiments.full_page_omr.datasets.one_note_data import CAP, HELD_OUT, PITCHES, export, make_note
from experiments.full_page_omr.representation.score_codec import W2I, decode, encode
from experiments.full_page_omr.training.one_note_experiment import evaluate, gate, musical_result, summarize, training_args
from experiments.full_page_omr.training.short_staff_experiment import donors, events


class OneNoteTests(unittest.TestCase):
    def test_complete_scores_and_finite_support(self):
        for pitch in PITCHES:
            source = make_note(pitch)
            tokens = encode(source)
            self.assertLess(len(tokens), CAP)
            self.assertEqual(events(source), [[((pitch[0], '0', pitch[1]), '1')]])
            self.assertEqual(events(source), events(decode(tokens)))
            self.assertEqual(ET.fromstring(source).find('part/measure').get('implicit'), 'yes')
        # Why the absolute-pitch policy must be explicit for this diagnostic.
        self.assertEqual(musical_fingerprint(make_note('C4')), musical_fingerprint(make_note('G5')))
        training = set(PITCHES) - set(HELD_OUT)
        self.assertEqual({p[0] for p in training}, set('CDEFGAB'))
        self.assertEqual({p[1] for p in training}, {'4', '5'})
        with self.assertRaises(ValueError):
            make_note('C6')

    def test_export_splits_variants_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data'
            manifest = export(path)
            self.assertEqual(manifest['family_counts'], dict(train=10, validation=4))
            check_disjoint(manifest['records'])
            self.assertEqual(len(manifest['records']), 112)
            data = {s: CleanPageDataset(path, s, 32) for s in ('train', 'validation')}
            self.assertEqual(len(data['train']), 80)
            self.assertEqual(len(data['validation']), 32)
            for dataset in data.values():
                for i, j in enumerate(donors(dataset.records)):
                    self.assertNotEqual(dataset.records[i]['pitch'], dataset.records[j]['pitch'])
                    self.assertEqual(dataset.records[i]['variant'], dataset.records[j]['variant'])
            changed = deepcopy(manifest['records'])
            changed[0]['split'] = 'validation'
            with self.assertRaisesRegex(ValueError, 'cross-split'):
                check_disjoint(changed)
            with self.assertRaises(FileExistsError):
                export(path)
            inconsistent = deepcopy(manifest)
            inconsistent['records'][1]['family_id'] = 'different-family-for-the-same-source'
            (path / 'manifest.json').write_text(json.dumps(inconsistent))
            with self.assertRaisesRegex(ValueError, 'inconsistent one-note source family'):
                CleanPageDataset(path, 'train', 32)
            (path / 'manifest.json').write_text(json.dumps(manifest))
            record = data['validation'].records[0]
            (path / record['image']).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                CleanPageDataset(path, 'validation', 32)

    def test_autonomous_metrics_and_gate(self):
        target = encode(make_note('E4'))
        good = musical_result(target, target)
        wrong_octave = musical_result(target, encode(make_note('E5')))
        invalid = musical_result(target, [W2I['<bos>'], W2I['<eos>']])
        self.assertTrue(good['joint_correct'])
        self.assertFalse(wrong_octave['pitch_correct'])
        self.assertTrue(wrong_octave['duration_correct'])
        self.assertFalse(invalid['valid'])
        two_notes = ET.fromstring(make_note('E4'))
        bar = two_notes.find('part/measure')
        bar.insert(list(bar).index(bar.find('barline')), deepcopy(bar.find('note')))
        extra = musical_result(target, encode(ET.tostring(two_notes, encoding='unicode')))
        self.assertTrue(extra['valid'])
        self.assertEqual(extra['predicted_notes'], 2)
        self.assertFalse(extra['joint_correct'])
        summary = summarize([good, wrong_octave, invalid])
        self.assertEqual(summary['musical_unscorable'], 1)
        self.assertEqual(summary['rates']['joint_correct'], 1 / 3)
        self.assertFalse(gate(summary, summary, summary)['passed'])
        perfect = summarize([good])
        self.assertTrue(gate(perfect, perfect, perfect)['passed'])
        self.assertFalse(gate(perfect, perfect, summary)['passed'])
        self.assertFalse(gate(perfect, perfect, perfect)['advancement_authorized'])

    def test_bounded_training_and_both_checkpoint_controls(self):
        from experiments.full_page_omr.training.clean_page_experiment import train

        def tiny(*args):
            return ViTModel(ViTConfig(image_size=32, patch_size=16, hidden_size=32,
                num_hidden_layers=1, num_attention_heads=4, intermediate_size=64), add_pooling_layer=False)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            with patch('experiments.full_page_omr.datasets.one_note_data.PITCHES', ('C4', 'D4', 'E4', 'A4')), \
                 patch('experiments.full_page_omr.datasets.one_note_data.LAYOUTS', ((0, 0),)):
                manifest = export(path / 'data')
            # Narrow the report's finite support to match this wiring fixture.
            manifest['held_out_pitches'] = ['E4', 'A4']
            (path / 'data/manifest.json').write_text(json.dumps(manifest))
            for name in ('weights', 'config'):
                (path / name).write_text('test placeholder')
            args = SimpleNamespace(dataset=str(path / 'data'), output=str(path / 'run'),
                encoder_weights=str(path / 'weights'), encoder_config=str(path / 'config'),
                device='cpu', seed=7, steps=8001, max_train_seconds=60, eval_every=1)
            with self.assertRaisesRegex(ValueError, 'limited'):
                training_args(args)
            args.steps, args.max_train_seconds = 1, 301
            with self.assertRaisesRegex(ValueError, 'limited'):
                training_args(args)
            args.max_train_seconds = 60
            training_args(args)
            self.assertTrue(args.skip_test)
            args.extended, args.steps, args.max_train_seconds = True, 40000, 900
            training_args(args)
            self.assertEqual(args.snapshot_steps, [8000, 16000, 24000, 40000])
            args.steps = 40001
            with self.assertRaisesRegex(ValueError, 'limited'):
                training_args(args)
            args.steps, args.max_train_seconds = 3, 60
            training_args(args)
            args.snapshot_steps = [1, 3]
            args.resolution, args.width = 32, 32
            with patch('experiments.full_page_omr.training.clean_page_experiment.local_encoder', side_effect=tiny), \
                 patch('experiments.full_page_omr.training.one_note_experiment.local_encoder', side_effect=tiny), \
                 patch('experiments.full_page_omr.training.clean_page_experiment.greedy', return_value=[W2I['<bos>'], W2I['<eos>']]):
                result = train(args)
                controls = evaluate(args.output)
                args.output = str(path / 'run_without_snapshots')
                args.snapshot_steps = []
                train(args)
            left = torch.load(path / 'run/last.pt', map_location='cpu', weights_only=True)
            right = torch.load(path / 'run_without_snapshots/last.pt', map_location='cpu', weights_only=True)
            self.assertTrue(all(torch.equal(value, right['trainable_state'][key])
                                for key, value in left['trainable_state'].items()))
            self.assertFalse(result['test_scored'])
            self.assertEqual(set(controls['trajectory']), {'1', '3'})
            self.assertEqual(controls['trajectory']['1']['matched']['train']['count'], 2)
            self.assertEqual(controls['trajectory']['3']['predictions'], 'reuse last checkpoint outputs')
            for checkpoint in controls['checkpoints'].values():
                self.assertEqual(checkpoint['matched']['train']['count'], 2)
                self.assertEqual(checkpoint['matched']['validation']['musical_unscorable'], 2)
                self.assertEqual(checkpoint['swapped_against_donor']['musical_unscorable'], 2)
                self.assertFalse(checkpoint['gate']['passed'])
                self.assertIn('text_value:octave', checkpoint['gold_prefix']['matched']['roles'])
            with self.assertRaises(FileExistsError):
                evaluate(path / 'run')


if __name__ == '__main__':
    unittest.main()
