from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from experiments.full_page_omr.datasets.clean_page_data import (
    CleanPageDataset, KINDS, check_disjoint, composition_seed, export_dataset,
    make_score, musical_fingerprint,
)
from experiments.full_page_omr.training.clean_page_experiment import prediction_metrics
from experiments.full_page_omr.diagnostics.clean_page_diagnostics import token_roles
from experiments.full_page_omr.representation.score_codec import VOCABULARY, W2I, encode
from experiments.full_page_omr.representation.score_semantics import inspect_score


class CleanPageTests(unittest.TestCase):
    def test_teacher_roles_separate_pitch_duration_and_measure_attributes(self):
        source = make_score(51,'horn')
        root = ET.fromstring(source)
        tokens = encode(source)
        roles = token_roles(tokens)
        self.assertEqual(len(roles),len(tokens))
        self.assertEqual(roles.count('text_value:step'),len(root.findall('.//pitch/step')))
        self.assertEqual(roles.count('text_value:duration'),len(root.findall('.//duration')))
        self.assertEqual(roles.count('attribute_value:measure@number'),16)
        for token,role in zip(tokens,roles):
            if role == 'text_value:step':
                self.assertIn(VOCABULARY[token],['V:'+s for s in 'ABCDEFG'])
        self.assertIn('attribute_value:measure@id',roles)

    def test_deterministic_complete_polyphonic_scores(self):
        for kind in KINDS:
            source = make_score(51, kind)
            self.assertEqual(source, make_score(51, kind))
            self.assertNotEqual(source, make_score(52, kind))
            summary = inspect_score(source)
            bars = summary['parts'][0]['measures']
            self.assertEqual(len(bars), 8 if kind == 'piano' else 16)
            self.assertTrue(all(b['length'] == '4' for b in bars))
            root = ET.fromstring(source)
            self.assertIsNone(root.find('work'))
            self.assertTrue(root.findall('.//dynamics'))
            if kind == 'piano':
                events = [e for b in bars for e in b['events']]
                self.assertEqual({e['voice'] for e in events}, {'1', '2', '3'})
                self.assertEqual({e['staff'] for e in events}, {'1', '2'})
                self.assertTrue(any(e['chord'] for e in events))

    def test_seed_domains_and_variant_fingerprint(self):
        seeds = {composition_seed(71, s, i) for s in ('train', 'validation', 'test') for i in range(36)}
        self.assertEqual(len(seeds), 108)
        source = make_score(51, 'horn')
        root = ET.fromstring(source)
        for octave in root.findall('.//pitch/octave'):
            octave.text = str(int(octave.text)+1)
        root.find('part-list/score-part/part-name').text = 'Different label'
        self.assertEqual(musical_fingerprint(source), musical_fingerprint(ET.tostring(root,encoding='unicode')))
        self.assertNotEqual(musical_fingerprint(source), musical_fingerprint(make_score(52,'horn')))

    def test_all_split_collision_guards(self):
        fields = ('composition_id','family_id','musical_fingerprint','target_sha256','image_sha256')
        left = dict(name='a',split='train',**{f:'a' for f in fields})
        right = dict(name='b',split='test',**{f:'b' for f in fields})
        check_disjoint([left,right])
        for field in fields:
            changed = dict(right,**{field:'a'})
            with self.assertRaisesRegex(ValueError,field):
                check_disjoint([left,changed])

    def test_metrics_distinguish_wrong_music_and_invalid_stream(self):
        source = make_score(51,'horn')
        target = encode(source)
        result, _ = prediction_metrics(target,target)
        self.assertTrue(result['exact'])
        self.assertEqual(result['structural']['event_edit_distance'],0)
        root = ET.fromstring(source)
        pitch = root.find('.//pitch/step')
        pitch.text = 'D' if pitch.text != 'D' else 'E'
        result, _ = prediction_metrics(target,encode(ET.tostring(root,encoding='unicode')))
        self.assertTrue(result['valid_score'])
        self.assertGreater(result['structural']['event_edit_distance'],0)
        result, _ = prediction_metrics(target,target[:-1])
        self.assertFalse(result['valid_score'])
        self.assertTrue(result['truncated'])
        self.assertIsNone(result['structural'])

    def test_export_split_loading_hash_checks_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'pages'
            manifest = export_dataset(path,train_count=3,validation_count=3,test_count=3)
            check_disjoint(manifest['records'])
            self.assertTrue(all(r['systems'] == 4 for r in manifest['records']))
            for split in ('train','validation','test'):
                data = CleanPageDataset(path,split,resolution=32)
                self.assertEqual(len(data),3)
                self.assertTrue(all(r['split']==split for r in data.records))
                _,inputs,labels = data[0]
                self.assertEqual(inputs[0,0].item(),W2I['<bos>'])
                self.assertEqual(labels[0,-1].item(),W2I['<eos>'])
            with self.assertRaises(FileExistsError):
                export_dataset(path,train_count=3,validation_count=3,test_count=3)
            with (path/manifest['records'][0]['image']).open('ab') as stream:
                stream.write(b'tamper')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                CleanPageDataset(path,'train',32)


if __name__ == '__main__':
    unittest.main()
