from pathlib import Path
import tempfile
import unittest
from fractions import Fraction
import json
from types import SimpleNamespace
from unittest.mock import patch
from transformers import ViTConfig, ViTModel

from experiments.full_page_omr.datasets.short_staff_data import export, make_passage, CAP
from experiments.full_page_omr.training.short_staff_experiment import donors, events, music_metrics, prior_baseline
from experiments.full_page_omr.datasets.clean_page_data import CleanPageDataset, check_disjoint
from experiments.full_page_omr.representation.score_codec import encode, decode


class ShortStaffTests(unittest.TestCase):
    def test_controlled_edits_and_roundtrips(self):
        for seed in range(20):
            base=make_passage(seed)
            self.assertEqual(base,make_passage(seed))
            a=events(base)
            for variant in ('base','pitch','rhythm'):
                source=make_passage(seed,variant)
                self.assertEqual(events(source),events(decode(encode(source))))
                self.assertLess(len(encode(source)),CAP)
                self.assertTrue(all(sum(Fraction(e[1]) for e in b)==4 for b in events(source)))
            pitch=music_metrics(base,make_passage(seed,'pitch'))
            rhythm=music_metrics(base,make_passage(seed,'rhythm'))
            self.assertEqual(pitch['pitch_correct'],7)
            self.assertEqual(pitch['duration_correct'],8)
            self.assertEqual(rhythm['pitch_correct'],8)
            self.assertEqual(rhythm['duration_correct'],6)
            self.assertEqual(prior_baseline([base],[base])['notes'],8)

    def test_train_and_evaluation_wiring(self):
        from experiments.full_page_omr.training.clean_page_experiment import train
        from experiments.full_page_omr.training.short_staff_experiment import evaluate
        from experiments.full_page_omr.representation.score_codec import W2I
        def tiny(*args):
            return ViTModel(ViTConfig(image_size=32,patch_size=16,hidden_size=32,
                num_hidden_layers=1,num_attention_heads=4,intermediate_size=64),add_pooling_layer=False)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            export(path/'data',train_count=2,validation_count=2)
            for name in ('weights','config'): (path/name).write_text('test placeholder')
            args=SimpleNamespace(dataset=str(path/'data'),output=str(path/'run'),
                encoder_weights=str(path/'weights'),encoder_config=str(path/'config'),
                steps=1,eval_every=1,max_tokens=CAP,max_train_seconds=60,device='cpu',
                seed=7,resolution=32,width=32,layers=2,lr=.001,skip_test=True,evaluate_last=True)
            with patch('experiments.full_page_omr.training.clean_page_experiment.local_encoder',side_effect=tiny), \
                 patch('experiments.full_page_omr.training.short_staff_experiment.local_encoder',side_effect=tiny), \
                 patch('experiments.full_page_omr.training.clean_page_experiment.greedy',return_value=[W2I['<bos>'],W2I['<eos>']]):
                result=train(args)
                controls=evaluate(args.output)
            self.assertFalse(result['test_scored'])
            for c in controls['checkpoints'].values():
                self.assertEqual(c['musical_unscorable'],6)
                self.assertIsNone(c['musical_summary']['base']['valid_only_totals'])
                self.assertIn('text_value:step',c['swapped_minus_matched_by_field'])

    def test_export_adapter_families_and_immutability(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data'
            m=export(path,train_count=2,validation_count=2)
            check_disjoint(m['records'])
            self.assertEqual(len(CleanPageDataset(path,'train',32)),2)
            v=CleanPageDataset(path,'validation',32)
            self.assertEqual(len(v),6)
            for i,j in enumerate(donors(v.records)):
                self.assertNotEqual(v.records[i]['family_id'],v.records[j]['family_id'])
                self.assertEqual(v.records[i]['variant'],v.records[j]['variant'])
            with self.assertRaises(FileExistsError): export(path,train_count=2,validation_count=2)
            r=v.records[0]
            (path/r['target']).write_text('{}')
            with self.assertRaisesRegex(ValueError,'hash mismatch'): CleanPageDataset(path,'validation',32)


if __name__=='__main__': unittest.main()
