"""Desktop state, BUI input/layout, worker recovery and immutable export checks."""
from concurrent.futures import Future
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from PIL import Image, ImageDraw
import curriculum

HAS_BUI = importlib.util.find_spec('blenderui') is not None
if HAS_BUI:
    from desktop import CurriculumDesktop, NumericParameter, WORKSPACES, read_documents, write_new, write_recipe


@unittest.skipUnless(HAS_BUI, 'Install the optional desktop extra for BUI integration checks')
class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        self.desktop = CurriculumDesktop(self.data)

    def tearDown(self):
        self.desktop.close()
        self.temp.cleanup()

    def click(self, node, fraction=.5):
        app = self.desktop.app
        app.render_raster()
        x, y = node.x + int(node.w * fraction), node.y + node.h // 2
        app.press(x, y)
        app.release(x, y)

    def preview(self):
        image = Image.new('RGB', (1400, 1981), 'white')
        draw = ImageDraw.Draw(image)
        for y in range(100, 150, 10):
            draw.line((50, y, 900, y), fill='black', width=2)
        with patch.object(curriculum, 'synthetic', return_value=(image, {'kind': 'synthetic'}, None)):
            manifest = curriculum.preview(self.data, dict(stage='0', settings=dict(recipe=[], seed=42)), [])
        self.desktop.latest = manifest
        self.desktop.update_images()
        self.desktop.app.render_raster()
        self.desktop.update_images()
        return manifest

    def test_workspace_clicks_preserve_request_and_preview(self):
        manifest = self.preview()
        before = self.desktop.payload()
        for index, name in enumerate(WORKSPACES):
            self.click(self.desktop.workspaces, (index+.5)/len(WORKSPACES))
            self.assertEqual(self.desktop.workspaces.value, name)
            self.assertEqual(self.desktop.source_panel.visible, name == 'Curriculum')
            self.assertEqual(self.desktop.recipe_panel.visible, name in ('Curriculum', 'Scan Recipe'))
            self.assertEqual(self.desktop.manifest_view.visible, name == 'Manifest')
            self.assertEqual(self.desktop.payload(), before)
            self.assertIs(self.desktop.latest, manifest)

    def test_main_viewport_zoom_scroll_drag_linking_and_resize(self):
        self.preview()
        raster = self.desktop.app.render_raster()
        image = self.desktop.page_images[0]
        # RGBA pixels render immediately without the unsafe native async loader.
        import buipy
        self.assertEqual(buipy.image_stats()['pending'], 0)
        self.assertEqual(raster.pixel(image.x+image.w//2, image.y+image.h//2), (255, 255, 255))
        for node in self.desktop.page_images:
            self.assertGreater(node.h, 20)
            self.assertLessEqual(node.y + node.h, self.desktop.app.size[1]-35)
        self.desktop.zoom.value = '100%'
        self.assertEqual(image.scale, 1)
        x,y = image.x+image.w//2,image.y+image.h//2
        self.desktop.app.wheel(x,y,-1)
        self.assertGreater(self.desktop.view_centers[0][1], .5)
        self.assertEqual(self.desktop.view_centers[0],self.desktop.view_centers[1])
        self.desktop.app.wheel(x,y,-1,1)  # Shift scrolls horizontally.
        self.assertGreater(self.desktop.view_centers[0][0], .5)
        self.desktop.app.wheel(x,y,1,2)  # Ctrl zooms.
        self.assertEqual(self.desktop.zoom.value,'150%')
        self.desktop.link_views.value = False
        before = self.desktop.view_centers.copy()
        self.desktop.app.press(x,y)
        self.desktop.app.motion(x+50,y+20,8)
        self.desktop.app.release(x+50,y+20)
        self.assertLess(self.desktop.view_centers[0][0],before[0][0])
        self.assertEqual(self.desktop.view_centers[1],before[1])
        self.desktop.zoom.value='Fit page'
        self.desktop.app.render_raster(1060,760)
        self.assertLessEqual(image.scale*image.picture.width,image.w+.01)
        self.assertLessEqual(image.scale*image.picture.height,image.h+.01)
        before=self.desktop.view_centers.copy()
        self.desktop.app.wheel(image.x+image.w//2,image.y+image.h//2,-1)
        self.assertEqual(self.desktop.view_centers,before)

    def test_region_dividers_resize_bound_reset_and_survive_workspace_changes(self):
        self.preview()
        desktop, app = self.desktop, self.desktop.app
        request, manifest = desktop.payload(), desktop.latest

        def drag(divider, delta):
            app.render_raster()
            x,y=divider.x+divider.w//2,divider.y+divider.h//2
            app.motion(x,y)
            self.assertEqual(app.cursor,'ew')
            app.press(x,y)
            for part in (delta//3,delta*2//3,delta):
                app.motion(x+part,y,8)
                app.render_raster()
            app.release(x+delta,y)
            app.render_raster()

        def reset(divider):
            x,y=divider.x+divider.w//2,divider.y+divider.h//2
            for _ in range(2):
                app.press(x,y)
                app.release(x,y)
                app.render_raster()

        app.render_raster()
        left, center, right = desktop.main_split.panes
        old_left,old_center,old_right=left.w,center.w,right.w
        drag(desktop.main_split.dividers[0],60)
        self.assertAlmostEqual(left.w,old_left+60,delta=2)
        self.assertAlmostEqual(center.w,old_center-60,delta=2)
        self.assertAlmostEqual(right.w,old_right,delta=1)
        drag(desktop.main_split.dividers[1],-50)
        self.assertAlmostEqual(right.w,old_right+50,delta=2)
        widths=[pane.w for pane in desktop.image_split.panes]
        drag(desktop.image_split.dividers[0],70)
        self.assertAlmostEqual(desktop.image_split.panes[0].w,widths[0]+70,delta=2)
        self.assertNotEqual(desktop.page_images[0].w,desktop.page_images[1].w)
        self.assertAlmostEqual(desktop.page_images[0].scale,
            min(desktop.page_images[0].w/1400,desktop.page_images[0].h/1981),delta=.001)
        weights=[pane.weight for pane in desktop.main_split.panes]
        desktop.workspaces.value='Compare'
        self.assertFalse(any(divider.visible for divider in desktop.main_split.dividers))
        desktop.workspaces.value='Scan Recipe'
        self.assertEqual([divider.visible for divider in desktop.main_split.dividers],[False,True])
        desktop.workspaces.value='Curriculum'
        self.assertEqual([pane.weight for pane in desktop.main_split.panes],weights)
        app.render_raster()
        drag(desktop.main_split.dividers[0],-10000)
        self.assertGreaterEqual(left.w,179)
        reset(desktop.image_split.dividers[0])
        self.assertAlmostEqual(desktop.page_images[0].w,desktop.page_images[1].w,delta=1)
        reset(desktop.main_split.dividers[0])
        self.assertEqual([pane.weight for pane in desktop.main_split.panes],desktop.main_split.default_weights)
        self.assertEqual(desktop.payload(),request)
        self.assertIs(desktop.latest,manifest)

    def test_recipe_buttons_native_grip_order_and_roundtrip(self):
        app = self.desktop
        self.click(app.add_button)
        self.assertEqual(len(app.recipe), 1)
        for char in 'scan res':
            app.app.key(char, char)
        app.app.render_raster()
        rows = app.app.ctx.menu_rows(0)
        self.assertEqual(len(rows), 1)
        self.assertIn('Scan resolution (DPI)', rows[0][0])
        _, (x, y, w, h) = rows[0]
        app.app.press(x+w//2, y+h//2)
        app.app.release(x+w//2, y+h//2)
        self.assertEqual(app.recipe[-1]['type'], 'scan_dpi')
        ids = [item['id'] for item in app.recipe]
        # Drag the second Blender panel by its grip above the first.
        app.app.render_raster()
        first, second = app.effect_cards.children
        x, y = second.x+second.w-10, second.y+10
        app.app.press(x, y)
        app.app.motion(x, first.y+2)
        app.app.release(x, first.y+2)
        self.assertEqual([item['id'] for item in app.recipe], ids[::-1])
        expected = deepcopy(app.recipe_document())
        path = self.data / 'recipe.json'
        write_new(path, json.dumps(expected).encode())
        app.clear_recipe()
        app.load_recipe(path)
        self.assertEqual(app.recipe_document(), expected)
        app.move_effect(0, 1)
        self.assertEqual([item['id'] for item in app.recipe], ids)
        app.remove_effect(0)
        self.assertEqual(len(app.recipe), 1)
        path.write_text('{"schema_version":1,"seed":42,"recipe":[{"type":"unknown"}]}')
        before = deepcopy(app.recipe)
        with self.assertRaises(ValueError):
            app.load_recipe(path)
        self.assertEqual(app.recipe, before)

    def test_worker_failure_recovers_and_midflight_edits_are_stale(self):
        app = self.desktop
        failed = Future()
        failed.set_exception(RuntimeError('native worker exited'))
        with patch.object(app.executor, 'submit', return_value=failed):
            self.click(app.generate_button)
        app.poll()
        self.assertIsNone(app.future)
        self.assertTrue(app.generate_button.enabled)
        self.assertIn('native worker exited', app.status.text)
        manifest = self.preview()
        app.latest = None
        pending = Future()
        with patch.object(app.executor, 'submit', return_value=pending) as submit:
            app.generate()
            callback = submit.call_args.kwargs['progress']
            callback(dict(label='Effect 1/1: BadPhotoCopy', fraction=.3))
            app.poll()
            self.assertIn('BadPhotoCopy', app.progress_bar.text)
            self.assertAlmostEqual(app.progress_bar.value, .3)
            request = deepcopy(submit.call_args.args[2])
            app.recipe[0]['enabled'] = False
            app.dirty()
            self.assertEqual(submit.call_args.args[2], request)
        pending.set_result(manifest)
        app.poll()
        self.assertIn('earlier settings', app.status.text)
        self.assertTrue(app.export_button.enabled)
        self.assertEqual(app.progress_bar.value, 1)
        self.assertIn('Preview ready in', app.progress_bar.text)

    def test_export_is_displayed_preview_and_never_overwrites(self):
        manifest = self.preview()
        self.desktop.clear_recipe()
        self.desktop.augmentation_seed.value = 17
        path = self.data / 'preview.zip'
        self.desktop.export_to(path)
        original = path.read_bytes()
        with zipfile.ZipFile(path) as archive:
            saved = json.loads(archive.read('manifest.json'))
            self.assertEqual(saved, manifest)
            for name, digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)
        with self.assertRaises(FileExistsError):
            self.desktop.export_to(path)
        self.assertEqual(path.read_bytes(), original)

    def test_shared_collection_is_read_only_and_real_page_payload(self):
        self.assertEqual(read_documents(self.data), [])
        self.assertFalse((self.data/'annotations.sqlite3').exists())
        database = self.data / 'annotations.sqlite3'
        doc = dict(id='fixture', title='Development scan', pages=[dict(number=3)])
        with sqlite3.connect(database) as db:
            db.execute('CREATE TABLE documents (payload TEXT)')
            db.execute('INSERT INTO documents VALUES (?)', (json.dumps(doc),))
        before = database.read_bytes()
        self.desktop.refresh_documents()
        self.desktop.select_stage('Real scans')
        self.assertEqual(self.desktop.payload()['document_id'], 'fixture')
        self.assertEqual(self.desktop.payload()['page'], 3)
        self.assertEqual(database.read_bytes(), before)

    def test_async_file_dialog_cancel_snapshots_errors_and_owner_close(self):
        app = self.desktop
        with patch('desktop.FileDialog') as dialog_class:
            dialog_class.return_value.finished = False
            before = deepcopy(app.recipe_document())
            app.save_recipe_dialog()
            cancelled = dialog_class.call_args.kwargs['on_result']
            app.save_recipe_dialog()
            self.assertEqual(dialog_class.call_count, 1)
            dialog_class.return_value.focus.assert_called_once()
            cancelled(None)
            self.assertIsNone(app.file_dialog)

            self.assertEqual(app.recipe_document(), before)
            self.assertIn('cancelled', app.status.text)
            app.save_recipe_dialog()
            saved = dialog_class.call_args.kwargs['on_result']
            app.augmentation_seed.value = 19
            recipe = self.data/'recipe.json'
            saved(str(recipe))
            self.assertEqual(json.loads(recipe.read_text()), before)
            app.save_recipe_dialog()
            dialog_class.call_args.kwargs['on_result'](str(recipe))
            updated={**before,'seed':19}
            self.assertEqual(json.loads(recipe.read_text()), updated)
            self.assertEqual(json.loads(next((self.data/'.recipe-backups').iterdir()).read_text()),before)
            self.assertIn('backed up', app.status.text)
            app.open_recipe_dialog()
            dialog_class.call_args.kwargs['on_result'](str(recipe))
            self.assertEqual(app.recipe_document(), updated)
            manifest = self.preview()
            app.export_dialog()
            exported = dialog_class.call_args.kwargs['on_result']
            app.latest = {**manifest, 'id':'1'*32}
            archive = self.data/'displayed.zip'
            exported(str(archive))
            with zipfile.ZipFile(archive) as opened:
                self.assertEqual(json.loads(opened.read('manifest.json')),manifest)
            app.save_recipe_dialog()
            active = app.file_dialog
            app.close()
            active.close.assert_called_once()
            self.assertIsNone(app.file_dialog)

    def test_numeric_range_controls_roundtrip_and_new_sample(self):
        import recipes
        app=self.desktop
        app.recipe=[recipes.entry('rotation','rotate'),recipes.entry('black_white','binary')]
        app.render_recipe()
        angle=app.effect_cards.children[0].body.children[1].children[0]
        self.assertIsInstance(angle,NumericParameter)
        self.click(angle.toggle)
        self.assertEqual(app.recipe[0]['ranges']['angle'],[-3,3])
        self.assertTrue(angle.bounds.visible)
        self.assertTrue(angle.fixed.enabled)
        angle.high.value=-2
        angle.low.value=1
        self.assertEqual(app.recipe[0]['ranges']['angle'],[1,1])
        self.click(angle.toggle)
        self.assertNotIn('ranges',app.recipe[0])
        self.assertEqual(app.recipe_document()['schema_version'],1)
        self.click(angle.toggle)
        self.assertEqual(app.recipe[0]['ranges']['angle'],[1,1])
        angle.low.value=-3; angle.high.value=3
        threshold=app.effect_cards.children[1].body.children[1].children[1]
        self.click(threshold.toggle)
        threshold.low.value=140; threshold.high.value=180
        document=deepcopy(app.recipe_document())
        self.assertEqual(document['schema_version'],2)
        path=self.data/'ranged.json'
        write_new(path,json.dumps(document).encode())
        app.clear_recipe(); app.load_recipe(path)
        self.assertEqual(app.recipe_document(),document)
        seed=app.augmentation_seed.value
        with patch.object(app,'generate') as generate:
            app.resample_recipe()
        self.assertEqual(app.augmentation_seed.value,seed+1)
        generate.assert_called_once()

    def test_ranged_slider_shows_preview_and_keeps_manual_edits_until_new_sample(self):
        import recipes
        app=self.desktop
        step=recipes.entry('rotation','rotate'); step['ranges']={'angle':[-3,3]}
        app.recipe=[step];app.render_recipe()
        control=app.effect_cards.children[0].body.children[1].children[0]

        def result_for(request):
            source=Image.new('RGB',(200,300),'white')
            with patch.object(curriculum,'synthetic',return_value=(source,{'kind':'synthetic'},None)):
                return curriculum.preview(self.data,request,[])

        result=result_for(app.payload())
        pending=Future()
        with patch.object(app.executor,'submit',return_value=pending):
            app.generate()
        pending.set_result(result);app.poll()
        self.assertTrue(control.fixed.enabled)
        self.assertEqual(control.fixed.value,result['effects'][0]['sampled_parameters']['angle'])
        self.assertEqual(app.preview_values,{})
        control.fixed.value=1.5
        self.assertEqual(app.payload()['settings']['preview_values'],{'rotate':{'angle':1.5}})
        self.assertEqual(app.recipe[0]['ranges'],{'angle':[-3,3]})
        self.assertNotIn('preview_values',app.recipe_document())
        result=result_for(app.payload())
        pending=Future()
        with patch.object(app.executor,'submit',return_value=pending):
            app.generate()
        control.fixed.value=2.0  # User edits while the earlier request renders.
        pending.set_result(result);app.poll()
        self.assertEqual(control.fixed.value,2.0)
        self.assertIn('earlier settings',app.status.text)
        with patch.object(app,'generate'):
            app.resample_recipe()
        self.assertNotIn('preview_values',app.payload()['settings'])

    def test_existing_recipe_save_restores_range_selection_and_bounds(self):
        import recipes
        app=self.desktop
        path=self.data/'existing.json'
        original=app.recipe_document()
        original_bytes=json.dumps(original).encode()
        path.write_bytes(original_bytes)
        app.load_recipe(path)
        app.recipe=[recipes.entry('rotation','rotate'),recipes.entry('black_white','binary')]
        app.render_recipe()
        angle=app.effect_cards.children[0].body.children[1].children[0]
        threshold=app.effect_cards.children[1].body.children[1].children[1]
        self.click(angle.toggle)
        angle.low.value=-2.5;angle.high.value=2.5
        self.click(threshold.toggle)
        threshold.low.value=130;threshold.high.value=185
        expected=deepcopy(app.recipe_document())
        with patch('desktop.FileDialog') as dialogs:
            dialogs.return_value.finished=False
            app.save_recipe_dialog()
            options=dialogs.call_args.kwargs
            self.assertEqual(options['initialdir'],str(self.data.resolve()))
            self.assertEqual(options['initialfile'],'existing.json')
            options['on_result'](str(path))
        self.assertEqual(json.loads(path.read_text()),expected)
        backups=list((self.data/'.recipe-backups').glob('*.json'))
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_bytes(),original_bytes)
        app.clear_recipe()
        app.load_recipe(path)
        self.assertEqual(app.recipe_document(),expected)
        angle=app.effect_cards.children[0].body.children[1].children[0]
        threshold=app.effect_cards.children[1].body.children[1].children[1]
        self.assertTrue(angle.toggle.value)
        self.assertTrue(threshold.toggle.value)
        self.assertEqual([angle.low.value,angle.high.value],[-2.5,2.5])
        self.assertEqual([threshold.low.value,threshold.high.value],[130,185])
        before=path.read_bytes()
        with patch('desktop.os.replace',side_effect=OSError('simulated replacement failure')):
            with self.assertRaises(OSError):
                write_recipe(path,b'new recipe')
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(list(self.data.glob('.*.tmp')),[])

if __name__ == '__main__':
    unittest.main()
