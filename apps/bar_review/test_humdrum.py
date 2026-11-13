"""Direct-source generation, native rendering, canonical references and portability."""
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import unittest

from experiments.full_page_omr.generation.humdrum_scores import EXAMPLES, make_score, _stable_ids


class HumdrumTests(unittest.TestCase):
    def test_generated_sources_replay_without_touching_global_rng(self):
        state = random.getstate()
        for example in EXAMPLES:
            first = make_score(example, 7)
            self.assertEqual(first, make_score(example, 7))
            self.assertNotIn('<score-partwise', first.source)
            self.assertTrue(first.source.endswith('\n'))
            self.assertIn('**kern', first.source)
            if example != 'cross_staff':
                self.assertNotEqual(first.source, make_score(example, 19).source)
        self.assertEqual(random.getstate(), state)
        for example, seed in (('unknown',7),('note',-1),('note',True)):
            with self.assertRaises(ValueError):
                make_score(example,seed)

    def test_derived_ids_rewrite_references_and_definition_order(self):
        left = '<svg><defs><symbol id="E2-random"/><symbol id="E1-random"/></defs><g id="random"><use href="#E1-random"/><g class="pageMilestoneEnd random"/></g></svg>'
        right = '<svg><defs><symbol id="E1-other"/><symbol id="E2-other"/></defs><g id="other"><use href="#E1-other"/><g class="pageMilestoneEnd other"/></g></svg>'
        self.assertEqual(_stable_ids(left), _stable_ids(right))
        self.assertIn('href="#id1"', _stable_ids(left))
        self.assertIn('class="pageMilestoneEnd id3"', _stable_ids(left))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            _stable_ids('<svg><g id="x"/><g id="x"/></svg>')

    def test_native_sources_artifacts_replay_and_project_restore(self):
        # Keep native engraving on a subprocess's main thread, including repeated
        # font changes, to exercise the same lifetime as the desktop warm worker.
        code = r'''
import builtins, hashlib, io, json, tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
from unittest.mock import patch
from PIL import Image
import curriculum, lab_project
from desktop import CurriculumDesktop
from experiments.full_page_omr.generation.humdrum_scores import EXAMPLES, make_score
original_import = builtins.__import__
def guarded(name,*args,**kwargs):
    if name.startswith('experiments.full_page_omr.datasets') or name.endswith(('score_codec','codec_fixtures','score_semantics')):
        raise AssertionError('Legacy MusicXML pipeline imported: '+name)
    return original_import(name,*args,**kwargs)
with tempfile.TemporaryDirectory() as temporary, patch('builtins.__import__', side_effect=guarded):
    data=Path(temporary)
    manifests=[]
    for index,example in enumerate(EXAMPLES):
        stage=next(stage['id'] for stage in curriculum.STAGES if example in stage['examples'])
        request=dict(stage=stage,example=example,font='Leipzig',music_seed=7,settings=dict(recipe=[],seed=42))
        manifest=curriculum.preview(data,request,[])
        assert {'source.krn','source.svg','source.mei'} <= manifest['files'].keys()
        assert 'source.musicxml' not in manifest['files']
        source=curriculum.artifact(data,manifest['id'],'source.krn').read_text()
        assert source == make_score(example,7).source
        for name,digest in manifest['files'].items():
            assert hashlib.sha256(curriculum.artifact(data,manifest['id'],name).read_bytes()).hexdigest()==digest
        with Image.open(curriculum.artifact(data,manifest['id'],'source.png')) as image:
            assert image.size==(1400,1980)
            assert image.convert('L').getextrema()==(0,255)
        mei=ET.parse(curriculum.artifact(data,manifest['id'],'source.mei'))
        notes=[n for n in mei.iter() if n.tag.rsplit('}',1)[-1]=='note']
        if example.startswith('drums'):
            assert sum(n.get('head.shape')=='x' for n in notes)==make_score(example,7).measures*4
        if example=='cross_staff':
            assert sum(n.get('staff')=='1' for n in notes)==2
        manifests.append(manifest)
    request=manifests[0]['request']
    for font in ('Bravura','Petaluma','Leipzig'):
        variant=curriculum.preview(data,{**request,'font':font},[])
        assert curriculum.artifact(data,variant['id'],'source.krn').read_text()==make_score('note',7).source
    repeated=curriculum.preview(data,request,[])
    assert repeated['files']==manifests[0]['files']
    reused=curriculum.preview(data,request,[],source_preview=repeated['id'])
    assert reused['source_reused'] and reused['files']==repeated['files']
    desktop=CurriculumDesktop(data)
    try:
        desktop.latest=manifests[0]
        desktop.update_images()
        assert desktop.kern_text.text==make_score('note',7).source
        document=desktop.project_document()
        bundle=lab_project.bundle(document,data,[])
        project=data/'direct-source.musvitlab'
        project.write_bytes(bundle)
        restored,scan=lab_project.unbundle(project,data/'restored')
        latest=next(iter(restored['previews'].values()))
        for name in ('source.krn','source.svg','source.mei'):
            assert curriculum.artifact(data/'restored',latest['id'],name).read_bytes()==curriculum.artifact(data,latest['id'],name).read_bytes()
        with __import__('zipfile').ZipFile(io.BytesIO(curriculum.export_preview(data,repeated['id']))) as archive:
            assert {'source.krn','source.svg','source.mei'} <= set(archive.namelist())
    finally:
        desktop.close()
print(json.dumps(dict(examples=len(EXAMPLES),fonts=3,replay=True,source_reuse=True,portable_assets=True)))
'''
        environment = os.environ.copy()
        if Path('/opt/homebrew/lib/libcairo.2.dylib').is_file():
            environment['DYLD_FALLBACK_LIBRARY_PATH'] = '/opt/homebrew/lib'
        run = subprocess.run([sys.executable,'-c',code], capture_output=True,text=True,
                             timeout=60,env=environment)
        self.assertEqual(run.returncode,0,run.stdout+'\n'+run.stderr)
        self.assertEqual(json.loads(run.stdout)['examples'],8)
