import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from transformers import ViTConfig, ViTModel
from experiments.full_page_omr.datasets import pitch_target_data as data
from experiments.full_page_omr.training import placement_experiment as experiment
from experiments.full_page_omr.training.overfit_pilot import make_model


class PlacementTests(unittest.TestCase):
    def test_shared_holdout_and_fixed_update_wiring(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(data,'PITCHES',('C4','D4')):
                manifest=data.export(root/'data',placement_comparison=True)
                _,samples=data.load(root/'data')
                self.assertEqual(len(samples['train']),32)
                self.assertEqual(len(experiment.control_indices(samples['train'])),8)
                train_pos={tuple(s['record']['translation_pixels']) for s in samples['train']}
                val_pos={tuple(s['record']['translation_pixels']) for s in samples['validation']}
                self.assertFalse(train_pos & val_pos)
                for name in ('weights','config'): (root/name).write_text('fixture')
                args=SimpleNamespace(dataset=str(root/'data'),output=str(root/'run'),
                    encoder_weights=str(root/'weights'),encoder_config=str(root/'config'),
                    device='cpu',seed=7,lr=.0001,steps=64,max_train_seconds=60,evaluation_steps=[32,64])
                def encoder(*a):
                    return ViTModel(ViTConfig(image_size=32,patch_size=16,hidden_size=32,
                        num_hidden_layers=1,num_attention_heads=4,intermediate_size=64),add_pooling_layer=False)
                with patch.object(experiment,'local_encoder',side_effect=encoder), \
                     patch.object(experiment,'make_model',side_effect=lambda enc,*a:make_model(enc,32,256,32,2)), \
                     patch.object(experiment,'image_tensor',side_effect=lambda d,r,n:data.image_tensor(d,r,32)), \
                     patch('experiments.full_page_omr.training.pitch_target_experiment.greedy',return_value=[1,2]):
                    result=experiment.run(args)
                self.assertTrue(result['matched_steps'])
                for name,expected in [('control',8),('expanded',2)]:
                    r=result['versions'][name]
                    self.assertEqual(set(r['presentations'].values()),{expected})
                    self.assertEqual([h['step'] for h in r['validation_history']],[32,64])
                    self.assertEqual(r['controls']['selected']['validation']['count'],8)
                    self.assertTrue(r['encoder_frozen'])
                    self.assertTrue(r['initial_state_identical'])
