"""Preview reproducibility, source isolation and artifact export boundaries."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import subprocess
from unittest.mock import patch
import numpy as np
from PIL import Image
import curriculum
import recipes
from copy import deepcopy
from test_server import page_image


class CurriculumTests(unittest.TestCase):
    def test_manual_preview_values_apply_without_changing_ranges(self):
        steps=[recipes.entry('rotation','rotate'),recipes.entry('black_white','binary')]
        steps[0]['ranges']={'angle':[-3,3]}
        steps[1]['ranges']={'threshold':[140,180]}
        overrides={'rotate':{'angle':1.5},'binary':{'threshold':170}}
        config=curriculum.settings(dict(recipe=steps,seed=42,preview_values=overrides))
        result,records=curriculum.augment(page_image(),config)
        fixed=deepcopy(steps)
        fixed[0].pop('ranges');fixed[1].pop('ranges')
        fixed[0]['parameters']['angle']=1.5
        fixed[1]['parameters']['threshold']=170
        expected,_=curriculum.augment(page_image(),dict(recipe=fixed,seed=42))
        self.assertEqual(result.tobytes(),expected.tobytes())
        self.assertEqual(records[0]['requested_ranges'],{'angle':[-3,3]})
        self.assertEqual(records[0]['sampled_parameters']['angle'],1.5)
        self.assertEqual(records[1]['parameters']['threshold'],170)
        self.assertEqual(records[1]['preview_overrides'],{'threshold':170})
        self.assertEqual(steps[0]['ranges'],{'angle':[-3,3]})
        for value in [[],{'unknown':{'angle':0}},{'rotate':{'angle':4}},
                      {'binary':{'threshold':170.5}},{'binary':{'radius':20}},
                      {'rotate':{'angle':float('nan')}}]:
            with self.subTest(value=value),self.assertRaises(ValueError):
                curriculum.settings(dict(recipe=steps,seed=42,preview_values=value))

    def test_parameter_ranges_replay_and_preserve_independent_streams(self):
        import random
        rotation=recipes.entry('rotation','rotate')
        rotation['ranges']={'angle':[-3,3]}
        threshold=recipes.entry('black_white','binary')
        threshold['ranges']={'threshold':[120,190]}
        steps=[rotation,threshold]
        state=random.getstate()
        first,records=curriculum.augment(page_image(),dict(recipe=steps,seed=42))
        repeated,replay=curriculum.augment(page_image(),dict(recipe=steps,seed=42))
        self.assertEqual(first.tobytes(),repeated.tobytes())
        self.assertEqual(records,replay)
        self.assertEqual(random.getstate(),state)
        _,new=curriculum.augment(page_image(),dict(recipe=steps,seed=43))
        self.assertNotEqual(records[0]['sampled_parameters']['angle'],new[0]['sampled_parameters']['angle'])
        _,reversed_records=curriculum.augment(page_image(),dict(recipe=steps[::-1],seed=42))
        self.assertEqual({r['id']:r['sampled_parameters'] for r in records},
                         {r['id']:r['sampled_parameters'] for r in reversed_records})
        for record in records:
            for key,(low,high) in record['requested_ranges'].items():
                self.assertLessEqual(low,record['sampled_parameters'][key])
                self.assertLessEqual(record['sampled_parameters'][key],high)
        self.assertIsInstance(records[1]['sampled_parameters']['threshold'],int)
        self.assertEqual(records[1]['parameters']['threshold'],records[1]['sampled_parameters']['threshold'])
        normalized=recipes.validate([threshold])[0]
        normalized['ranges']['threshold']=[150,151]
        values={recipes.sample_parameters(normalized,seed)['threshold'] for seed in range(32)}
        self.assertEqual(values,{150,151})
        angle=recipes.validate([rotation])[0]
        values=[recipes.sample_parameters(angle,seed)['angle'] for seed in range(32)]
        self.assertLess(min(values),0)
        self.assertGreater(max(values),0)

    def test_parameter_range_validation(self):
        for kind,ranges in [('rotation',{'angle':[3,-3]}),('rotation',{'angle':[-4,3]}),
                            ('rotation',{'angle':[False,3]}),('rotation',{'angle':[0,float('nan')]}),
                            ('rotation',{'angle':[0]}),('rotation',{'angle':'-3,3'}),
                            ('rotation',{'unknown':[0,1]}),('rotation',[]),
                            ('black_white',{'threshold':[120.5,180]}),
                            ('black_white',{'method':[0,1]})]:
            step=recipes.entry(kind,'effect'); step['ranges']=ranges
            with self.subTest(ranges=ranges),self.assertRaises(ValueError):
                recipes.validate([step])
        step=recipes.entry('rotation','effect'); step['ranges']={'angle':[1,1]}
        _,record=curriculum.augment(page_image(),dict(recipe=[step],seed=7))
        self.assertEqual(record[0]['sampled_parameters']['angle'],1)

    def test_range_preview_exports_requested_and_sampled_values(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'doc').mkdir()
            source=root/'doc/page-1.png'; page_image().save(source)
            original=source.read_bytes()
            steps=[recipes.entry('rotation','rotate'),recipes.entry('black_white','binary')]
            steps[0]['ranges']={'angle':[-3,3]}
            steps[1]['ranges']={'threshold':[140,180]}
            request=dict(stage='4',document_id='doc',page=1,settings=dict(recipe=steps,seed=42,
                preview_values={'rotate':{'angle':1.25},'binary':{'threshold':160}}))
            result=curriculum.preview(root,request,[dict(id='doc',sha256='fixture',pages=[dict(number=1)])])
            with zipfile.ZipFile(io.BytesIO(curriculum.export_preview(root,result['id']))) as archive:
                manifest=json.loads(archive.read('manifest.json'))
                self.assertEqual(manifest['settings']['recipe'],recipes.validate(steps))
                self.assertEqual(manifest['request'],request)
                self.assertEqual(manifest['effects'],json.loads(json.dumps(result['effects'])))
                self.assertEqual(manifest['effects'][0]['preview_overrides'],{'angle':1.25})
                with Image.open(io.BytesIO(archive.read('augmented.png'))) as image:
                    self.assertEqual(image.mode,'1')
            self.assertEqual(source.read_bytes(),original)

    def test_clean_and_pixel_only_recipes_do_not_import_augraphy(self):
        import builtins
        original_import = builtins.__import__

        def guarded(name, *args, **kwargs):
            if name == 'augraphy' or name.startswith('experiments.scan_degradation'):
                raise AssertionError('Unneeded Augraphy import')
            return original_import(name, *args, **kwargs)

        image = page_image()
        with patch('builtins.__import__', side_effect=guarded):
            for config in [dict(profile='clean'), dict(profile='clean', rotation=1),
                           dict(recipe=[]), dict(recipe=[recipes.entry('dirty_drum','disabled',)])]:
                if config.get('recipe'):
                    config['recipe'][0]['enabled'] = False
                curriculum.augment(image, curriculum.settings(config))
            curriculum.augment(image, curriculum.settings(dict(recipe=[
                recipes.entry('rotation','rotate'), recipes.entry('scan_dpi','dpi'),
                recipes.entry('black_white','bw')])))

    def test_source_reuse_checks_inputs_code_and_artifact_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            request = dict(stage='2', example='horn_page', font='Leipzig', music_seed=7,
                           settings=dict(recipe=[], seed=42))
            source = (page_image(), dict(kind='synthetic'), '**kern\n4c\n*-\n')
            events = []
            with patch.object(curriculum, 'synthetic', return_value=source) as render:
                first = curriculum.preview(data, request, [], progress=events.append)
                changed = deepcopy(request)
                changed['settings'] = dict(recipe=[recipes.entry('rotation','rotate')], seed=19)
                reused = curriculum.preview(data, changed, [], source_preview=first['id'], progress=events.append)
                self.assertEqual(render.call_count, 1)
                self.assertTrue(reused['source_reused'])
                self.assertEqual(first['files']['source.png'], reused['files']['source.png'])
                self.assertEqual(reused['request'], changed)
                self.assertEqual(reused['effect_timings_seconds'][0]['label'], 'Antialiased rotation')
                self.assertGreater(reused['timings_seconds']['worker_total'], 0)
                self.assertTrue(any('Effect 1/1' in event['label'] for event in events))
                self.assertEqual(events[-1]['fraction'], .99)
                for key, value in [('font','Petaluma'), ('music_seed',8), ('example','piano_page')]:
                    other = {**request, key: value}
                    result = curriculum.preview(data, other, [], source_preview=first['id'])
                    self.assertFalse(result['source_reused'])
                with patch.object(curriculum, 'source_fingerprint', return_value='new-code'):
                    self.assertFalse(curriculum.preview(data, request, [], source_preview=first['id'])['source_reused'])
                curriculum.artifact(data, first['id'], 'source.png').write_bytes(b'corrupted-cache')
                recovered = curriculum.preview(data, request, [], source_preview=first['id'])
                self.assertFalse(recovered['source_reused'])
                self.assertEqual(render.call_count, 6)

    def test_isolated_worker_delivers_progress_and_timings(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            (data/'doc').mkdir()
            page_image().save(data/'doc/page-1.png')
            events = []
            result = curriculum.preview_isolated(data,
                dict(stage='4', document_id='doc', page=1, settings=dict(recipe=[],seed=42)),
                [dict(id='doc', sha256='fixture', pages=[dict(number=1)])], progress=events.append)
            self.assertEqual(events[0]['label'], 'Starting preview worker')
            self.assertEqual(events[-1]['fraction'], .99)
            self.assertEqual(sorted(event['fraction'] for event in events), [event['fraction'] for event in events])
            self.assertFalse(result['source_reused'])
            self.assertIn('save_images_and_hashes', result['timings_seconds'])

    def test_added_augraphy_effects_replay_and_preserve_source(self):
        import random
        from numba import config as numba_config
        kinds={'dirty_drum':'DirtyDrum','dirty_rollers':'DirtyRollers','dirty_screen':'DirtyScreen',
               'lines_degradation':'LinesDegradation','low_ink_periodic':'LowInkPeriodicLines',
               'low_ink_random':'LowInkRandomLines','markup':'Markup','subtle_noise':'SubtleNoise'}
        source=page_image(); original=source.tobytes()
        for kind,name in kinds.items():
            with self.subTest(effect=kind):
                config=dict(recipe=[recipes.entry(kind,'effect')],seed=42)
                python_state=random.getstate(); numpy_state=np.random.get_state(); jit=numba_config.DISABLE_JIT
                first,records=curriculum.augment(source,config)
                second,replay=curriculum.augment(source,config)
                self.assertEqual(first.tobytes(),second.tobytes())
                self.assertEqual(first.size,source.size)
                self.assertNotEqual(first.tobytes(),original)
                self.assertEqual(source.tobytes(),original)
                self.assertEqual(records,replay)
                self.assertEqual(records[0]['name'],name)
                self.assertEqual(random.getstate(),python_state)
                np.testing.assert_array_equal(np.random.get_state()[1],numpy_state[1])
                self.assertEqual(numba_config.DISABLE_JIT,jit)

    def test_black_white_thresholds_and_methods(self):
        values=np.tile(np.arange(256,dtype=np.uint8),(40,1))
        values[15:20,100:110]=0  # A local ink mark, not just a smooth illumination gradient.
        source=Image.fromarray(values).convert('RGB')
        for method in ['fixed','otsu','adaptive_gaussian']:
            steps=[recipes.entry('black_white','bw',method=method,threshold=160)]
            result,records=curriculum.augment(source,dict(recipe=steps,seed=42))
            self.assertEqual(set(np.unique(result)),{0,255})
            self.assertEqual(result.size,source.size)
            self.assertFalse(records[0]['geometry_changed'])
            if method=='fixed':
                self.assertEqual(result.getpixel((160,0)),(0,0,0))
                self.assertEqual(result.getpixel((161,0)),(255,255,255))
        low,_=curriculum.augment(source,dict(recipe=[recipes.entry('black_white','bw',threshold=80)],seed=42))
        high,_=curriculum.augment(source,dict(recipe=[recipes.entry('black_white','bw',threshold=200)],seed=42))
        self.assertGreater(np.count_nonzero(np.asarray(low)),np.count_nonzero(np.asarray(high)))

    def test_binary_export_and_subsequent_grayscale_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'doc').mkdir(); page_image().save(root/'doc/page-1.png')
            steps=[recipes.entry('scan_dpi','dpi'),recipes.entry('black_white','bw')]
            docs=[dict(id='doc',sha256='test',pages=[dict(number=1)])]
            payload=dict(stage='4',document_id='doc',page=1,settings=dict(seed=42,recipe=steps))
            result=curriculum.preview(root,payload,docs)
            with Image.open(curriculum.artifact(root,result['id'],'augmented.png')) as image:
                self.assertEqual(image.mode,'1')
            with Image.open(curriculum.artifact(root,result['id'],'augmented-1024.png')) as image:
                self.assertEqual(image.mode,'RGB')
                self.assertTrue(np.any((np.asarray(image)>0)&(np.asarray(image)<255)))
            steps.append(recipes.entry('rotation','rotate'))
            result=curriculum.preview(root,payload,docs)
            with Image.open(curriculum.artifact(root,result['id'],'augmented.png')) as image:
                self.assertEqual(image.mode,'RGB')
                self.assertTrue(np.any((np.asarray(image)>0)&(np.asarray(image)<255)))

    def test_scan_dpi_dimensions_detail_loss_and_restore(self):
        # A 10-inch-wide raster at 200 DPI; alternate one-pixel lines.
        values=np.tile(np.array([0,255],dtype=np.uint8),1000)
        source=Image.fromarray(np.tile(values,(200,1))).convert('RGB')
        steps=[recipes.entry('scan_dpi','scan',dpi=100,width_mm=254)]
        result,records=curriculum.augment(source,dict(recipe=steps,seed=42))
        self.assertEqual(result.size,(1000,100))
        self.assertLess(np.asarray(result).std(),1)
        self.assertEqual(records[0]['parameters']['effective_scan_dpi'],100)
        self.assertTrue(records[0]['geometry_changed'])
        steps[0]['parameters']['output']='restore_size'
        restored,records=curriculum.augment(source,dict(recipe=steps,seed=42))
        self.assertEqual(restored.size,source.size)
        self.assertLess(np.asarray(restored).std(),1)
        self.assertFalse(records[0]['geometry_changed'])
        self.assertEqual(records[0]['parameters']['scan_dimensions'],[1000,100])

    def test_scan_dpi_source_limit_bypass_and_validation(self):
        source=page_image()
        for dpi in [100,300]:
            result,records=curriculum.augment(source,dict(seed=42,recipe=[recipes.entry('scan_dpi','scan',dpi=dpi,width_mm=203.2)]))
            self.assertEqual(result.tobytes(),source.tobytes())
            self.assertEqual(records[0]['parameters']['source_limited'],dpi>100)
        for params in [dict(dpi=0),dict(width_mm=0),dict(dpi=75.5),dict(output='invalid')]:
            with self.assertRaises(ValueError):
                recipes.validate([recipes.entry('scan_dpi','scan',**params)])

    def test_ordered_recipe_replay_order_and_disable(self):
        source = page_image()
        steps = [recipes.entry('framing','frame'), recipes.entry('bindings','holes'), recipes.entry('badphotocopy','copy')]
        config = curriculum.settings(dict(recipe=steps,seed=19))
        first, records = curriculum.augment(source, config)
        replay, repeated = curriculum.augment(source, config)
        self.assertEqual(first.tobytes(),replay.tobytes())
        self.assertEqual(records,repeated)
        self.assertEqual([r['id'] for r in records],['frame','holes','copy'])
        reordered, reverse_records = curriculum.augment(source,dict(recipe=list(reversed(steps)),seed=19))
        self.assertEqual({r['id']:r['seed'] for r in records},{r['id']:r['seed'] for r in reverse_records})
        self.assertNotEqual(first.tobytes(),reordered.tobytes())
        disabled = deepcopy(steps)
        for item in disabled: item['enabled']=False
        untouched, empty = curriculum.augment(source,dict(recipe=disabled,seed=19))
        self.assertEqual(untouched.tobytes(),source.tobytes())
        self.assertEqual(empty,[])

    def test_recipe_validation(self):
        for recipe in [None, [{}], [recipes.entry('ink','same')]*2,
                       [recipes.entry('ink','ink',strength=99)],
                       [recipes.entry('bindings','b',foreground='/tmp/file')],
                       [recipes.entry('rotation','r',angle=float('nan'))],
                       [recipes.entry('framing',str(i)) for i in range(13)]]:
            with self.subTest(recipe=recipe), self.assertRaises(ValueError):
                curriculum.settings(dict(recipe=recipe))

    def test_binding_types_and_recipe_manifest(self):
        for kind in ['punch_holes','binding_holes','clips','triangle_clips']:
            _,records=curriculum.augment(page_image(),dict(seed=7,recipe=[recipes.entry('bindings','b',kind=kind)]))
            self.assertEqual(records[0]['parameters']['use_figshare_library'],0)
            self.assertEqual(records[0]['name'],'BindingsAndFasteners')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'doc').mkdir(); page_image().save(root/'doc/page-1.png')
            recipe=deepcopy(recipes.PRESETS['bound-copy'])
            result=curriculum.preview(root,dict(stage='4',document_id='doc',page=1,settings=dict(seed=42,recipe=recipe)),
                                      [dict(id='doc',sha256='test',pages=[dict(number=1)])])
            self.assertEqual(result['settings']['recipe'],recipes.validate(recipe))
            self.assertEqual([e['id'] for e in result['effects']],[e['id'] for e in recipe])
            self.assertIn('changed',result['geometry'])
            with zipfile.ZipFile(io.BytesIO(curriculum.export_preview(root,result['id']))) as archive:
                self.assertEqual(json.loads(archive.read('manifest.json'))['effects'],json.loads(json.dumps(result['effects'])))

    def test_rotation_smooths_edges_without_clipping_or_changing_zero_control(self):
        source = page_image()
        self.assertEqual(curriculum.rotate_antialiased(source,0).tobytes(),source.tobytes())
        for angle in [-3, -1, 1, 3]:
            rotated = curriculum.rotate_antialiased(source,angle)
            values = np.asarray(rotated.convert('L'))
            self.assertGreater(rotated.width,source.width)
            self.assertGreater(rotated.height,source.height)
            self.assertGreater(np.count_nonzero((values > 0) & (values < 255)),100)
            self.assertEqual(rotated.getpixel((0,0)),(255,255,255))
            # Preserve integrated ink within 5%, instead of smoothing away lines.
            ink_before = np.sum(255-np.asarray(source.convert('L')))
            ink_after = np.sum(255-values)
            self.assertLess(abs(float(ink_after)/float(ink_before)-1),.05)

    def test_native_worker_failure_and_timeout_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            failure = subprocess.CompletedProcess([], -6, '', 'Bravura font could not be loaded')
            with patch.object(curriculum.subprocess, 'run', return_value=failure):
                with self.assertRaisesRegex(RuntimeError, 'exit -6.*'):
                    curriculum.preview_isolated(Path(temp), {}, [])
            with patch.object(curriculum.subprocess, 'run', side_effect=subprocess.TimeoutExpired([],120)):
                with self.assertRaisesRegex(RuntimeError, '120 seconds'):
                    curriculum.preview_isolated(Path(temp), {}, [])

    def test_augraphy_seed_replay_and_no_source_mutation(self):
        source = page_image()
        before = source.tobytes()
        config = curriculum.settings(dict(profile='library-scan', rotation=-1, ink=1))
        first, effects = curriculum.augment(source, config)
        second, _ = curriculum.augment(source, config)
        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertEqual(source.tobytes(), before)
        self.assertNotEqual(first.size, source.size)
        self.assertEqual(len(effects), 3)

    def test_clean_control_and_validation(self):
        source = Image.new('RGB', (20, 30), (70, 80, 90))
        result, effects = curriculum.augment(source, curriculum.settings(dict(profile='clean')))
        self.assertEqual(result.tobytes(), source.tobytes())
        self.assertEqual(effects, [])
        for value in [dict(seed=-1), dict(rotation=8), dict(strength=1.5), dict(ink=True), dict(profile='unknown')]:
            with self.assertRaises(ValueError):
                curriculum.settings(value)

    def test_scan_preview_export_is_immutable_and_unapproved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'doc').mkdir()
            source = root/'doc/page-1.png'
            page_image().save(source)
            before = source.read_bytes()
            docs = [dict(id='doc', sha256='source-hash', pages=[dict(number=1)])]
            request = dict(stage='4', document_id='doc', page=1, settings=dict(profile='light-copy'))
            first = curriculum.preview(root, request, docs)
            second = curriculum.preview(root, request, docs)
            self.assertNotEqual(first['id'],second['id'])
            self.assertEqual(first['files'],second['files'])
            self.assertEqual(source.read_bytes(),before)
            with zipfile.ZipFile(io.BytesIO(curriculum.export_preview(root,first['id']))) as archive:
                manifest = json.loads(archive.read('manifest.json'))
                self.assertIn('not approved',manifest['status'])
                self.assertNotIn('source.krn',archive.namelist())
                for name, digest in manifest['files'].items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),digest)
                with Image.open(io.BytesIO(archive.read('augmented-1024.png'))) as image:
                    self.assertEqual(image.size,(1024,1024))
            self.assertEqual(docs,[dict(id='doc', sha256='source-hash', pages=[dict(number=1)])])

    def test_path_and_stage_boundaries(self):
        for preview_id, filename in [('../secrets','source.png'), ('a'*32,'../../secret'), ('a'*32,'annotations.sqlite3')]:
            with self.assertRaises(ValueError):
                curriculum.artifact(Path('/tmp'),preview_id,filename)
        with tempfile.TemporaryDirectory() as temp:
            for request in [dict(stage='5'),dict(stage='0',example='piano'),dict(stage='4',document_id='missing')]:
                with self.assertRaises(ValueError):
                    curriculum.preview(Path(temp),request,[])

    def test_process_rng_is_restored(self):
        import random
        random.seed(913)
        np.random.seed(913)
        python_state, numpy_state = random.getstate(), np.random.get_state()
        curriculum.augment(page_image(), curriculum.settings(dict(ink=2, rotation=1)))
        self.assertEqual(random.getstate(),python_state)
        after = np.random.get_state()
        self.assertEqual(after[0],numpy_state[0])
        np.testing.assert_array_equal(after[1],numpy_state[1])
        self.assertEqual(after[2:],numpy_state[2:])


if __name__ == '__main__':
    unittest.main()
