from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from transformers import ViTConfig, ViTModel

from experiments.full_page_omr.datasets.clean_page_data import CleanPageDataset
from experiments.full_page_omr.datasets.one_note_data import PITCHES, make_note
from experiments.full_page_omr.datasets.pitch_target_data import export, load, pitch_from_tokens, pitch_to_musicxml, pitch_tokens
from experiments.full_page_omr.representation.score_codec import W2I, encode
from experiments.full_page_omr.representation.score_semantics import inspect_score
from experiments.full_page_omr.training.pitch_target_experiment import donor_indices, measure, run, selection_rank, summarize


class PitchTargetTests(unittest.TestCase):
    def test_compact_grammar_and_musicxml(self):
        for pitch in PITCHES:
            tokens = pitch_tokens(pitch)
            self.assertEqual(len(tokens), 4)
            self.assertEqual(pitch_from_tokens(tokens), pitch)
            self.assertEqual(pitch_to_musicxml(tokens), make_note(pitch))
            self.assertEqual(inspect_score(pitch_to_musicxml(tokens)), inspect_score(make_note(pitch)))
            for bad in (tokens[:-1], tokens + [W2I['<eos>']],
                        [W2I['<bos>'], W2I['V:6'], tokens[2], W2I['<eos>']]):
                with self.assertRaises(ValueError):
                    pitch_from_tokens(bad)

    def test_export_appearance_policy_and_tamper_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data'
            manifest = export(path)
            _, data = load(path)
            self.assertEqual(len(manifest['records']), 112)
            for split in ('train', 'validation'):
                self.assertEqual(len(data[split]), 56)
                self.assertEqual({s['record']['pitch'] for s in data[split]}, set(PITCHES))
                records = [s['record'] for s in data[split]]
                for i,j in enumerate(donor_indices(records)):
                    self.assertNotEqual(records[i]['pitch'], records[j]['pitch'])
                    self.assertEqual(records[i]['translation_pixels'], records[j]['translation_pixels'])
            with self.assertRaisesRegex(ValueError, 'unsupported dataset'):
                CleanPageDataset(path, 'validation', 32)
            with self.assertRaises(FileExistsError):
                export(path)
            bad = deepcopy(manifest)
            bad['records'][0]['compact_tokens'] = pitch_tokens('D4')
            (path / 'manifest.json').write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError, 'compact label mismatch'):
                load(path)
            bad = deepcopy(manifest)
            bad['records'][1]['image_sha256'] = bad['records'][0]['image_sha256']
            (path / 'manifest.json').write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError, 'duplicate raster'):
                load(path)
            (path / 'manifest.json').write_text(json.dumps(manifest))
            (path / manifest['records'][0]['image']).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                load(path)

    def test_shared_musical_metrics_and_selection(self):
        for arm, target in (('score', encode(make_note('E4'))), ('pitch', pitch_tokens('E4'))):
            good, source = measure('E4', target, target, arm)
            self.assertTrue(good['pitch_correct'])
            self.assertTrue(good['music_exact'])
            self.assertEqual(inspect_score(source), inspect_score(make_note('E4')))
            wrong = encode(make_note('E5')) if arm == 'score' else pitch_tokens('E5')
            wrong_metrics, _ = measure('E4', target, wrong, arm)
            self.assertTrue(wrong_metrics['valid'])
            self.assertFalse(wrong_metrics['pitch_correct'])
            bad, source = measure('E4', target, [W2I['<bos>'], W2I['<eos>']], arm)
            self.assertFalse(bad['valid'])
            self.assertIsNone(source)
            summary = summarize([good, wrong_metrics, bad])
            self.assertEqual(summary['rates']['pitch_correct'], 1/3)
            self.assertEqual(summary['musical_unscorable'], 1)
        better_pitch = {'totals':dict(pitch_correct=2, valid=2, target_exact=1)}
        better_structure = {'totals':dict(pitch_correct=1, valid=100, target_exact=1)}
        self.assertGreater(selection_rank(better_pitch), selection_rank(better_structure))

    def test_paired_training_wiring(self):
        def tiny(*args):
            return ViTModel(ViTConfig(image_size=32, patch_size=16, hidden_size=32,
                num_hidden_layers=1, num_attention_heads=4, intermediate_size=64), add_pooling_layer=False)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            with patch('experiments.full_page_omr.datasets.pitch_target_data.PITCHES', ('C4','D4')):
                export(path / 'data')
                for name in ('weights', 'config'):
                    (path / name).write_text('test placeholder')
                args = SimpleNamespace(dataset=str(path / 'data'), output=str(path / 'run'),
                    encoder_weights=str(path / 'weights'), encoder_config=str(path / 'config'),
                    device='cpu', seed=7, presentations=1, max_train_seconds=60,
                    resolution=32, width=32, layers=2, lr=.001)
                with patch('experiments.full_page_omr.training.pitch_target_experiment.local_encoder', side_effect=tiny), \
                     patch('experiments.full_page_omr.training.pitch_target_experiment.greedy',
                           return_value=[W2I['<bos>'], W2I['<eos>']]) as decoding:
                    report = run(args)
                self.assertEqual({c.args[2] for c in decoding.call_args_list}, {8,256})
                self.assertTrue(report['matched_steps'])
                self.assertTrue(report['matched_order'])
                self.assertFalse(report['test_scored'])
                for arm in ('score', 'pitch'):
                    result = report['arms'][arm]
                    self.assertEqual(result['steps'], 8)
                    self.assertTrue(result['initial_state_identical'])
                    self.assertTrue(result['encoder_frozen'])
                    self.assertEqual(set(result['presentations'].values()), {1})
                    for label in ('selected', 'final'):
                        self.assertEqual(result['controls'][label]['validation']['musical_unscorable'], 8)
                        self.assertFalse(result['controls'][label]['gate']['passed'])
                with self.assertRaises(FileExistsError):
                    run(args)
                args.output = str(path / 'capacity')
                args.capacity_comparison = True
                with patch('experiments.full_page_omr.training.pitch_target_experiment.local_encoder', side_effect=tiny), \
                     patch('experiments.full_page_omr.training.pitch_target_experiment.greedy',
                           return_value=[W2I['<bos>'], W2I['<eos>']]) as decoding:
                    capacity = run(args)
                self.assertEqual(set(capacity['arms']), {'small', 'medium'})
                self.assertEqual({c.args[2] for c in decoding.call_args_list}, {256})
                self.assertTrue(capacity['matched_steps'])
                self.assertTrue(capacity['matched_order'])
                config = json.loads((path / 'capacity/config.json').read_text())
                self.assertGreater(config['versions']['medium']['trainable_parameters'],
                                   config['versions']['small']['trainable_parameters'])
                for result in capacity['arms'].values():
                    self.assertTrue(result['encoder_frozen'])
                    self.assertEqual(set(result['presentations'].values()), {1})
                args.capacity_comparison = False
                args.medium_lr_baseline = str(path / 'capacity')
                args.output = str(path / 'lower_lr')
                args.lr = .0001
                with patch('experiments.full_page_omr.training.pitch_target_experiment.local_encoder', side_effect=tiny), \
                     patch('experiments.full_page_omr.training.pitch_target_experiment.greedy',
                           return_value=[W2I['<bos>'], W2I['<eos>']]):
                    lower = run(args)
                self.assertEqual(set(lower['arms']), {'medium'})
                self.assertTrue(lower['baseline_initial_tensors_identical'])
                self.assertTrue(lower['matched_order'])
                self.assertTrue(lower['matched_steps'])




if __name__ == '__main__':
    unittest.main()
