"""Complete project round trips, multi-level comparison and portable assets."""
from copy import deepcopy
from concurrent.futures import Future
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from PIL import Image, ImageDraw
import curriculum
import lab_project
import recipes

HAS_BUI=importlib.util.find_spec('blenderui') is not None
if HAS_BUI:
    from desktop import CurriculumDesktop,write_recipe


@unittest.skipUnless(HAS_BUI,'Install the desktop extra')
class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.app=CurriculumDesktop(self.root/'original')

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def source(self):
        image=Image.new('RGB',(480,680),'white')
        draw=ImageDraw.Draw(image)
        for y in range(60,130,12):
            draw.line((20,y,460,y),fill='black',width=2)
        return image,dict(kind='synthetic'),'<score-partwise/>'

    def generate_levels(self):
        def preview(data,payload,documents,**kwargs):
            return curriculum.preview(data,payload,documents,**kwargs)
        with patch.object(curriculum,'synthetic',return_value=self.source()),patch.object(self.app.worker,'preview',side_effect=preview):
            self.app.generate_all()
            self.app.future.result(timeout=20)
            self.app.poll()
        self.assertTrue(all(item.get('latest') for item in self.app.levels))

    def save(self,path):
        data=lab_project.bundle(self.app.project_document(),self.app.data,self.app.documents)
        write_recipe(path,data,backup_folder='.project-backups')
        return data

    def test_entire_project_roundtrip_restores_previews_and_controls_in_new_data_directory(self):
        app=self.app
        app.stage_choice.value='Short passages'
        app.font.value='Petaluma';app.music_seed.value=19
        app.recipe=[recipes.entry('rotation','rotate'),recipes.entry('black_white','binary')]
        app.recipe[0]['ranges']={'angle':[-3,3]}
        app.recipe[1]['ranges']={'threshold':[130,190]}
        app.preview_values={'rotate':{'angle':1.5}}
        app.render_recipe();app.rename_level('Light copy')
        self.generate_levels()
        app.effect_cards.children[0].body.children[1].children[0].fixed.value=2
        app.effect_cards.children[0].collapsed=True
        app.source_panel.children[0].children[2].collapsed=True
        app.workspaces.value='Compare';app.resolution.value='Model 1024';app.zoom.value='150%'
        app.link_views.value=False;app.view_centers=[(.2,.3),(.7,.6)]
        app.compare_centers[app.levels[2]['id']]=(.4,.2)
        app.main_split.panes[0].weight=.35
        app.compare_split.panes[2].weight=1.4
        document=app.project_document()
        path=self.root/'lab.musvitlab';self.save(path)
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(json.loads(archive.read('project.json')),document)
            self.assertTrue(any(name.endswith('augmented.png') for name in archive.namelist()))
        other=CurriculumDesktop(self.root/'restored')
        try:
            other.load_project(path)
            self.assertEqual(other.project_document(),document)
            self.assertEqual(other.workspaces.value,'Compare')
            self.assertEqual(len(other.compare_images),len(other.levels)+1)
            self.assertTrue(all(view.picture is not None for view in other.compare_images))
            for item in other.levels:
                manifest=item['latest']
                for name,digest in manifest['files'].items():
                    self.assertEqual(hashlib.sha256(curriculum.artifact(other.data,manifest['id'],name).read_bytes()).hexdigest(),digest)
            angle=other.effect_cards.children[0].body.children[1].children[0]
            self.assertTrue(angle.toggle.value)
            self.assertEqual(angle.fixed.value,2)
            self.assertTrue(other.effect_cards.children[0].collapsed)
            self.assertTrue(other.source_panel.children[0].children[2].collapsed)
            self.assertEqual(other.latest['effects'][0]['sampled_parameters']['angle'],1.5)
            self.assertEqual(other.payload()['settings']['preview_values'],{'rotate':{'angle':2}})
        finally:
            other.close()

    def test_levels_are_independent_switching_preserves_each_recipe_and_duplicate(self):
        app=self.app
        mild=app.active_level_id
        app.recipe=[recipes.entry('rotation','r')];app.recipe[0]['ranges']={'angle':[-2,2]}
        app.preview_values={'r':{'angle':1}}
        app.augmentation_seed.value=71
        app.select_level('Moderate')
        self.assertNotEqual(app.recipe[0]['type'],'rotation')
        app.clear_recipe();app.add_effect('black_white')
        app.select_level('Mild')
        self.assertEqual(app.active_level_id,mild)
        self.assertEqual(app.recipe[0]['ranges'],{'angle':[-2,2]})
        self.assertEqual(app.augmentation_seed.value,71)
        self.assertEqual(app.preview_values,{'r':{'angle':1}})
        app.duplicate_level()
        self.assertNotEqual(app.active_level_id,mild)
        app.recipe[0]['parameters']['angle']=2
        app.select_level('Mild')
        self.assertEqual(app.recipe[0]['parameters']['angle'],-1) # original fixed fallback
        self.assertEqual(app.preview_values,{'r':{'angle':1}})
        self.assertEqual(len(app.levels),5)
        app.select_level('Mild copy');app.remove_level()
        self.assertEqual(len(app.levels),4)
        app.select_level('Mild')
        app.move_level(-1)
        self.assertEqual(app.levels[0]['id'],mild)
        self.assertEqual(app.compare_ids[1],mild)

    def test_portable_selected_scan_and_previews_do_not_modify_annotations(self):
        app=self.app
        folder=app.data/'scan';folder.mkdir(parents=True)
        image=self.source()[0];image.save(folder/'page-3.png')
        doc=dict(id='scan',title='Development scan',sha256='source-file-sha',pages=[dict(number=3,width=480,height=680)])
        app.project_documents=[doc];app.refresh_documents();app.stage_choice.value='Real scans'
        self.generate_levels()
        path=self.root/'scan.musvitlab';self.save(path)
        other=CurriculumDesktop(self.root/'other')
        try:
            other.load_project(path)
            self.assertEqual(other.stage,'4')
            self.assertEqual(other.payload()['page'],3)
            loaded=other.data/other.payload()['document_id']/'page-3.png'
            self.assertEqual(loaded.read_bytes(),(folder/'page-3.png').read_bytes())
            self.assertFalse((other.data/'annotations.sqlite3').exists())
            other.refresh_documents()
            self.assertEqual(other.payload()['page'],3)
        finally:other.close()

    def test_corrupt_or_unexpected_archive_assets_are_rejected_before_restore(self):
        self.generate_levels()
        original=self.save(self.root/'valid.musvitlab')
        with zipfile.ZipFile(io.BytesIO(original)) as source:
            entries={name:source.read(name) for name in source.namelist()}
        for kind in ['corrupt','traversal']:
            changed=dict(entries)
            if kind=='corrupt':
                filename=next(name for name in changed if name.endswith('augmented.png'))
                changed[filename]=b'corrupted'
            else:changed['../outside.txt']=b'not allowed'
            path=self.root/(kind+'.musvitlab')
            with zipfile.ZipFile(path,'w') as archive:
                for name,content in changed.items():archive.writestr(name,content)
            destination=self.root/kind
            with self.assertRaises(ValueError):lab_project.unbundle(path,destination)
            self.assertFalse(destination.exists())

    def test_project_save_dialog_snapshots_all_levels_and_updates_existing_bundle(self):
        app=self.app
        path=self.root/'lab.musvitlab'
        with patch('desktop.FileDialog') as dialog:
            dialog.return_value.finished=False
            app.save_project_dialog()
            callback=dialog.call_args.kwargs['on_result']
            app.rename_level('Edited after opening dialog')
            callback(str(path))
            with zipfile.ZipFile(path) as archive:
                saved=json.loads(archive.read('project.json'))
            self.assertEqual(saved['levels'][1]['name'],'Mild')
            old=path.read_bytes()
            app.save_project_dialog();dialog.call_args.kwargs['on_result'](str(path))
        self.assertNotEqual(path.read_bytes(),old)
        self.assertEqual(next((self.root/'.project-backups').iterdir()).read_bytes(),old)

    def test_switching_editor_during_render_keeps_result_with_original_level(self):
        app=self.app
        original=app.active_level_id
        request=app.payload()
        with patch.object(curriculum,'synthetic',return_value=self.source()):
            result=curriculum.preview(app.data,request,[])
        pending=Future()
        with patch.object(app.executor,'submit',return_value=pending):
            app.generate()
        app.select_level('Clean')
        pending.set_result(result);app.poll()
        self.assertEqual(app.active_level()['name'],'Clean')
        self.assertIsNone(app.latest)
        self.assertEqual(next(level for level in app.levels if level['id']==original)['latest']['id'],result['id'])
        app.select_level('Mild')
        self.assertEqual(app.latest['id'],result['id'])

    def test_preview_id_collision_preserves_local_files_and_restores_new_identity(self):
        self.generate_levels()
        path=self.root/'project.musvitlab';self.save(path)
        manifest=self.app.levels[0]['latest']
        destination=self.root/'conflict'
        folder=destination/'curriculum'/manifest['id'];folder.mkdir(parents=True)
        original=b'preexisting local artifact'
        (folder/'source.png').write_bytes(original)
        (folder/'manifest.json').write_text('{}')
        document,_=lab_project.unbundle(path,destination)
        identity=document['levels'][0]['preview_id']
        self.assertNotEqual(identity,manifest['id'])
        self.assertEqual((folder/'source.png').read_bytes(),original)
        self.assertEqual(document['previews'][identity]['restored_from_preview_id'],manifest['id'])
        self.assertTrue((destination/'curriculum'/identity/'augmented.png').is_file())
