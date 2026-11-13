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
        return image,dict(kind='synthetic'),'**kern\n4c\n*-\n'

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

    def test_custom_curriculum_stage_management_uses_stable_source_types(self):
        app = self.app
        editor = app.curriculum_editor
        original = deepcopy(app.stages)
        app.stage_fields['title'].value = 'My first lesson'
        app.stage_fields['focus'].value = 'Ledger lines'
        editor.duplicate()
        identity = app.active_stage_id
        self.assertNotEqual(identity, original[0]['id'])
        app.stage_fields['focus'].value = 'Rhythm'
        self.assertEqual(app.stages[0]['focus'], 'Ledger lines')
        editor.move(1)
        self.assertEqual(app.active_stage_id, identity)
        self.assertEqual(app.stages[2]['id'], identity)
        app.stage_template.value = 'Short passages'
        self.assertEqual(app.payload()['stage'], '1')
        self.assertEqual(app.payload()['example'], 'passage')
        self.assertEqual(app.active_stage_id, identity)
        self.generate_levels()
        self.assertTrue(all(stage['latest']['request']['stage'] == '1' for stage in app.levels))
        editor.add()
        self.assertEqual(len(app.stages), 7)
        self.assertEqual(editor.active()['title'], 'New stage')
        editor.remove()
        self.assertEqual(len(app.stages), 6)
        editor.refresh(next(stage for stage in app.stages if stage['id'] == identity))
        editor.reset()
        self.assertEqual(editor.active()['focus'], curriculum.STAGES[1]['focus'])
        self.assertEqual(app.active_stage_id, identity)
        self.assertEqual(curriculum.STAGES, [
            {key:value for key,value in stage.items() if key != 'template'} for stage in original])

    def test_custom_curriculum_roundtrip_and_legacy_defaults(self):
        app = self.app
        app.curriculum_editor.add()
        identity = app.active_stage_id
        app.stage_fields['title'].value = 'Page reading'
        app.stage_fields['description'].value = 'Read several systems in order.'
        app.stage_fields['mix'].value = 'Start clean, then add scans.'
        app.stage_template.value = 'Systems & pages'
        app.example.value = 'Piano · full page'
        app.curriculum_editor.move(-1)
        expected = app.project_document()
        path = self.root/'stages.musvitlab'
        self.save(path)
        other = CurriculumDesktop(self.root/'restored')
        try:
            other.load_project(path)
            self.assertEqual(other.project_document(), expected)
            self.assertEqual(other.active_stage_id, identity)
            self.assertEqual(other.stage_choice.value, 'Page reading')
            self.assertEqual(other.stage_fields['description'].value, 'Read several systems in order.')
            self.assertEqual(other.stage_template.value, 'Systems & pages')
            self.assertEqual(other.payload()['stage'], '2')
            self.assertEqual(other.payload()['example'], 'piano_page')
            self.assertFalse(other.recipe_panel.visible)
            self.assertFalse(other.image_split.panes[1].visible)
        finally:
            other.close()
        legacy = deepcopy(expected)
        legacy['schema_version'] = 1
        del legacy['curriculum_stages']
        del legacy['active_curriculum_stage']
        restored = lab_project.validate(legacy)
        self.assertEqual(len(restored['curriculum_stages']), 5)
        self.assertEqual(restored['active_curriculum_stage'], '2')
        legacy_path = self.root/'legacy.musvitlab'
        with zipfile.ZipFile(legacy_path, 'w') as archive:
            archive.writestr('project.json', json.dumps(legacy))
        app.load_project(legacy_path)
        self.assertEqual(app.stage_choice.value, 'Systems & pages')
        self.assertEqual(app.active_stage_id, '2')
        self.assertEqual(app.project_document()['schema_version'], 2)

    def test_curriculum_stage_validation_and_bounds(self):
        from curriculum_plan import MAX_STAGES, validate_stages
        app = self.app
        editor = app.curriculum_editor
        name = editor.active()['title']
        app.stage_fields['title'].value = ''
        self.assertEqual(editor.active()['title'], name)
        app.stage_fields['title'].value = app.stages[1]['title']
        self.assertEqual(editor.active()['title'], name)
        malformed = deepcopy(app.stages)
        malformed[0]['template'] = 'unknown'
        with self.assertRaises(ValueError):
            validate_stages(malformed)
        malformed = deepcopy(app.stages)
        malformed[0]['examples'] = ['invented']
        with self.assertRaises(ValueError):
            validate_stages(malformed)
        document = app.project_document()
        missing_plan = deepcopy(document)
        del missing_plan['curriculum_stages']
        with self.assertRaises(ValueError):
            lab_project.validate(missing_plan)
        document['active_curriculum_stage'] = 'missing'
        with self.assertRaises(ValueError):
            lab_project.validate(document)
        while len(app.stages) > 1:
            editor.remove()
        editor.remove()
        self.assertEqual(len(app.stages), 1)
        for _ in range(MAX_STAGES+1):
            editor.add()
        self.assertEqual(len(app.stages), MAX_STAGES)
        self.assertEqual(len({stage['id'] for stage in app.stages}), MAX_STAGES)
        self.assertEqual(validate_stages(app.stages), app.stages)

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

    def test_save_shortcuts_use_current_path_and_save_as_changes_it(self):
        app = self.app
        first, second = self.root/'first.musvitlab', self.root/'second.musvitlab'
        with patch('desktop.FileDialog') as dialog:
            dialog.return_value.finished = False
            # Cocoa maps Command to modifier bit 2; Ctrl uses the same binding.
            app.app.key('', 's', mods=2)
            self.assertEqual(dialog.call_count, 1)
            dialog.call_args.kwargs['on_result'](str(first))
            original = first.read_bytes()
            app.rename_level('Saved in place')
            app.app.key('', 's', mods=2)
            self.assertEqual(dialog.call_count, 1)
            self.assertEqual(app.project_path, first.resolve())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(json.loads(archive.read('project.json'))['levels'][1]['name'], 'Saved in place')
            self.assertEqual(next((self.root/'.project-backups').iterdir()).read_bytes(), original)

            # Shift+Save always asks for another filename and becomes current.
            app.app.key('', 'S', mods=3)
            self.assertEqual(dialog.call_count, 2)
            dialog.call_args.kwargs['on_result'](str(second))
            self.assertEqual(app.project_path, second.resolve())
            first_bytes = first.read_bytes()
            app.rename_level('Second project')
            app.app.key('', 's', mods=2)
            self.assertEqual(first.read_bytes(), first_bytes)
            self.assertEqual(dialog.call_count, 2)

            app.app.key('', 'o', mods=2)
            self.assertEqual(dialog.call_args.args[1], 'open')
            dialog.call_args.kwargs['on_result'](str(first))
            self.assertEqual(app.project_path, first.resolve())
            app.rename_level('Loaded then saved')
            app.app.key('', 's', mods=2)
            self.assertEqual(dialog.call_count, 3)
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(json.loads(archive.read('project.json'))['levels'][1]['name'], 'Loaded then saved')

    def test_save_in_place_failure_preserves_project_and_current_path(self):
        app = self.app
        path = self.root/'current.musvitlab'
        self.save(path)
        app.load_project(path)
        original = path.read_bytes()
        app.rename_level('Unsaved change')
        with patch('desktop_storage.os.replace', side_effect=OSError('replacement failed')):
            app.app.key('', 's', mods=2)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(app.project_path, path.resolve())
        self.assertIn('Project save failed', app.status.text)
        self.assertEqual(list(self.root.glob('.*.tmp')), [])

    def test_file_menu_clicks_open_save_as_and_recipe_actions(self):
        app = self.app
        def pick(label):
            app.app.render_raster()
            button = app.menu_bar.buttons[0]
            x, y = button.x+button.w//2, button.y+button.h//2
            app.app.press(x, y); app.app.release(x, y)
            app.app.render_raster()
            rows = app.app.ctx.menu_rows(0)
            _, (x, y, w, h) = next(row for row in rows if row[0] == label)
            app.app.press(x+w//2, y+h//2); app.app.release(x+w//2, y+h//2)

        with patch('desktop.FileDialog') as dialog:
            dialog.return_value.finished = False
            for label, kind, title in [
                ('Open project…', 'open', 'Open Curriculum Lab project'),
                ('Save project as…', 'save', 'Save Curriculum Lab project'),
                ('Import recipe…', 'open', 'Open scan recipe'),
                ('Export recipe…', 'save', 'Save scan recipe'),
            ]:
                pick(label)
                self.assertEqual(dialog.call_args.args[1], kind)
                self.assertEqual(dialog.call_args.kwargs['title'], title)
                dialog.call_args.kwargs['on_result'](None)
            pick('Export preview ZIP…')
            self.assertIn('Generate a preview', app.status.text)
            app.app.key('', 'E', mods=3)
            self.assertIn('Generate a preview', app.status.text)

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
