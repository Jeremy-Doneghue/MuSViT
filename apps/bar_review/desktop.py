"""Curriculum Lab desktop: BUI Blender components over the shared lab backend.

Run with the repository environment: .venv/bin/python apps/bar_review/desktop.py
No web server or Blender installation is needed.

CurriculumDesktop owns session state, editor/view coordination and resource
lifetime. Layout, reusable widgets, preview jobs and project actions live in
the desktop_* modules; see README.md for the ownership and threading guide.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import argparse
import io
import json
import os
from pathlib import Path
from queue import Queue
import textwrap
import sqlite3
import time
import uuid

from PIL import Image as PILImage

import curriculum
import recipes
import lab_project
from curriculum_plan import default_stages
from preview_worker import PreviewWorker
from desktop_storage import read_documents

try:
    import blenderui as bui
    import buipy
    from desktop_dialog import FileDialog
    from desktop_curriculum import StageEditor
    from desktop_layout import WORKSPACES, build_layout
    from desktop_preview import PreviewJobs
    from desktop_projects import ProjectActions
    from desktop_widgets import NumericParameter, PageImage, RecipePanel, ResizableRow
    from blenderui import host
    from blenderui.components import (
        Button, Checkbox, Column, Dropdown, Label, Menu, MenuItem, Row,
    )
except ImportError as error:
    raise SystemExit('Install the desktop extra: uv sync --extra desktop') from error


APP = Path(__file__).resolve().parent
EFFECT_CATEGORIES = [
    ('Paper & framing', ['scanner_edge', 'page_border', 'framing', 'bindings']),
    ('Ink & printing', ['ink', 'low_ink_periodic', 'low_ink_random', 'lines_degradation']),
    ('Dirt & interference', ['badphotocopy', 'dirty_drum', 'dirty_rollers', 'dirty_screen', 'markup', 'subtle_noise']),
    ('Scan & geometry', ['rotation', 'scan_dpi', 'black_white']),
]


class CurriculumDesktop:
    """Own the live session; delegate jobs and persistence to collaborators.

    Action wrappers keep BUI callbacks and external callers on one stable API.
    Collaborators receive this host explicitly and never import the entry point.
    """
    def __init__(self, data=APP / 'outputs'):
        self.data = Path(data).expanduser().resolve()
        self.documents = read_documents(self.data)
        self.stage = '0'
        self.stages = default_stages()
        self.active_stage_id = self.stages[0]['id']
        self.recipe = deepcopy(recipes.PRESETS['light-copy'])
        self.latest = None
        self.revision = 0
        self.future = None
        self.progress_events = Queue()
        self.progress_state = dict(label='Ready', fraction=0)
        self.source_previews = {}
        self.view_cache = {}
        self.preview_values = {}
        self.displayed_values = {}
        self.closed = False
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='curriculum-desktop')
        self.worker = PreviewWorker()
        self.warmup_future = None
        self.file_dialog = None
        self.recipe_path = None
        self.project_path = None
        self.project_documents = []
        heavy=deepcopy(recipes.PRESETS['bound-copy'])
        next(item for item in heavy if item['type']=='badphotocopy')['parameters']['strength']=3
        self.levels=[lab_project.level('Clean',[]),lab_project.level('Mild',self.recipe),
                     lab_project.level('Moderate',recipes.PRESETS['library-scan']),lab_project.level('Heavy',heavy)]
        self.active_level_id=self.levels[1]['id']
        self.levels[1]['settings']['recipe']=self.recipe
        self.levels[1]['preset']='light-copy'
        self.levels[2]['preset']='library-scan'
        self.levels[3]['preset']='bound-copy'
        self.compare_centers={}
        self.compare_weights={}
        self.pending_batch=False
        self.projects = ProjectActions(self)
        self.previews = PreviewJobs(self)
        self.curriculum_editor = StageEditor(self)
        build_layout(self)
        self.rebuild_compare()
        self.refresh_documents()
        self.select_stage(curriculum.STAGES[0]['title'])
        self.render_recipe()
        self.update_manifest()
        self.set_workspace(self.workspaces.value)

    @staticmethod
    def clear(container):
        for child in list(container.children):
            container.remove(child)

    @staticmethod
    def lines(text, width=40):
        return [Label(line) for line in textwrap.wrap(text, width=width)]

    def active_level(self):
        return next(item for item in self.levels if item['id']==self.active_level_id)

    def stash_active(self):
        if getattr(self,'restoring',False):
            return
        item=self.active_level()
        settings=dict(seed=self.augmentation_seed.value,recipe=recipes.validate(self.recipe))
        overrides={step['id']:{key:value for key,value in self.preview_values.get(step['id'],{}).items()
                              if key in step.get('ranges',{})} for step in self.recipe}
        overrides={key:value for key,value in overrides.items() if value}
        if overrides:
            settings['preview_values']=overrides
        item.update(settings=settings,latest=self.latest,displayed_values=self.displayed_values,
                    preset=self.preset.value,collapsed={panel.recipe_item['id']:panel.collapsed
                        for panel in self.effect_cards.children if isinstance(panel,RecipePanel)})

    def activate_level(self,identity):
        self.active_level_id=identity
        item=self.active_level()
        self.recipe=item['settings']['recipe']
        self.latest=item.get('latest')
        self.preview_values=deepcopy(item['settings'].get('preview_values',{}))
        self.displayed_values=item.get('displayed_values',{})
        self.augmentation_seed.set_value(item['settings']['seed'],notify=False)
        self.preset.set_value(item.get('preset','clean'),notify=False)
        self.level_choice.items=[level['name'] for level in self.levels]
        self.level_choice.set_value(item['name'],notify=False)
        self.level_name.set_value(item['name'],notify=False)
        self.render_recipe()
        self.export_button.enabled=self.latest is not None
        self.preview_info.text=(f"{item['name']} · preview {self.latest['id'][:8]}" if self.latest
                                else f"{item['name']} · no preview generated")
        self.update_images()
        self.update_manifest()

    def select_level(self,name):
        self.stash_active()
        self.activate_level(next(item['id'] for item in self.levels if item['name']==name))
        self.status.text=f'Editing {name}'

    def rename_level(self,name):
        name=name.strip()
        if not name or len(name)>80 or any(item['name']==name and item['id']!=self.active_level_id for item in self.levels):
            self.level_name.set_value(self.active_level()['name'],notify=False)
            self.status.text='Choose a unique level name (1–80 characters).'
            return
        self.active_level()['name']=name
        self.level_choice.items=[item['name'] for item in self.levels]
        self.level_choice.set_value(name,notify=False)
        self.update_compare_labels()

    def unique_level_name(self,base):
        base=base[:80]
        name=base;index=2
        while any(item['name']==name for item in self.levels):
            suffix=f' {index}'
            name=base[:80-len(suffix)]+suffix;index+=1
        return name

    def add_level(self):
        self.insert_level(False)

    def duplicate_level(self):
        self.insert_level(True)

    def insert_level(self,duplicate):
        if self.future is not None or len(self.levels)>=lab_project.MAX_LEVELS:
            self.status.text='Wait for rendering, or remove a level before adding another (maximum 8).'
            return
        self.stash_active()
        if duplicate:
            item=deepcopy(self.active_level())
            item.update(id=uuid.uuid4().hex,name=self.unique_level_name(item['name']+' copy'))
        else:
            item=lab_project.level(self.unique_level_name('New level'),[])
        self.levels.append(item)
        self.activate_level(item['id'])
        self.rebuild_compare()

    def remove_level(self):
        if self.future is not None or len(self.levels)<=1:
            self.status.text='Keep at least one level, and wait for rendering before removing a level.'
            return
        index=next(i for i,item in enumerate(self.levels) if item['id']==self.active_level_id)
        self.levels.pop(index)
        self.activate_level(self.levels[min(index,len(self.levels)-1)]['id'])
        self.rebuild_compare()

    def move_level(self,delta):
        if self.future is not None:
            return
        self.stash_active()
        index=next(i for i,item in enumerate(self.levels) if item['id']==self.active_level_id)
        target=index+delta
        if 0<=target<len(self.levels):
            self.levels[index],self.levels[target]=self.levels[target],self.levels[index]
            self.level_choice.items=[item['name'] for item in self.levels]
            self.level_choice.set_value(self.active_level()['name'],notify=False)
            self.rebuild_compare()

    def source_settings(self):
        document=(self.documents[self.document.index]['id']
                  if self.documents and 0<=self.document.index<len(self.documents) else None)
        example=next((key for key,label in curriculum.EXAMPLES.items() if label==self.example.value),None)
        return dict(stage=self.stage,example=example,font=self.font.value,music_seed=self.music_seed.value,
                    document_id=document,page=int(self.page.value) if self.page.value else None)

    def source_request(self):
        source=self.source_settings()
        return ({key:source[key] for key in ['stage','document_id','page']} if self.stage=='4' else
                {key:source[key] for key in ['stage','example','font','music_seed']})

    def rebuild_compare(self):
        if self.compare_split is not None:
            self.compare_weights.update({key:pane.weight for key,pane in zip(self.compare_ids,self.compare_split.panes)})
            self.image_region.remove(self.compare_split)
        self.compare_ids=['source']+[item['id'] for item in self.levels]
        self.compare_images=[];self.compare_headers=[];panes=[]
        for identity in self.compare_ids:
            viewport=PageImage(lambda x,y,key=identity:self.pan_comparison(key,x,y),self.zoom_step)
            header=Label('Source' if identity=='source' else '',bold=True)
            pane=Column(header,viewport,fill=True,spacing=6,weight=self.compare_weights.get(identity,1))
            self.compare_images.append(viewport);self.compare_headers.append(header);panes.append(pane)
        self.compare_split=ResizableRow(*panes,minimums=[120]*len(panes),fill=True,
                                       visible=self.workspaces.value=='Compare')
        self.image_region.add(self.compare_split)
        self.update_images()

    def update_compare_labels(self):
        if not self.compare_headers:
            return
        self.stash_active()
        source=self.source_request()
        for item,header in zip(self.levels,self.compare_headers[1:]):
            preview=item.get('latest')
            stale=preview and (self.source_key(preview['request'])!=self.source_key(source)
                              or preview.get('settings')!=item['settings'])
            header.text=item['name']+(' · settings changed' if stale else ' · no preview' if not preview else '')

    def pan_comparison(self,identity,x,y):
        self.compare_centers[identity]=(x,y)
        if self.link_views.value:
            self.compare_centers={key:(x,y) for key in self.compare_ids}
            self.view_centers=[(x,y),(x,y)]
        self.redraw_panned_images()

    def current_viewport(self):
        return self.compare_images[0] if self.workspaces.value=='Compare' else self.page_images[0]

    def dirty(self):
        if getattr(self,'restoring',False):
            return
        self.revision += 1
        self.status.text = ('Settings changed · displaying the previous preview. Generate to apply.'
                            if self.latest else 'Settings ready · generate a preview.')
        if hasattr(self,'compare_headers'):
            self.update_compare_labels()

    def set_workspace(self, name):
        controls_parent = self.compare_controls if name == 'Compare' else self.reference_controls
        if controls_parent is not self.controls_parent:
            self.controls_parent.remove(self.image_controls)
            controls_parent.add(self.image_controls)
            self.controls_parent = controls_parent
        self.compare_controls.visible = name == 'Compare'
        self.source_panel.visible = name == 'Curriculum'
        self.recipe_panel.visible = name == 'Scan Recipe'
        self.main_split.sync_visibility()
        self.comparison.visible = name != 'Manifest'
        self.manifest_view.visible = name == 'Manifest'
        self.curriculum_split.visible=name!='Compare'
        self.kern_panel.visible=name=='Curriculum'
        self.curriculum_split.sync_visibility()
        self.image_split.visible=name!='Compare'
        self.image_split.panes[1].visible = name != 'Curriculum'
        self.image_split.sync_visibility()
        self.link_views.visible = name != 'Curriculum'
        if self.compare_split:
            self.compare_split.visible=name=='Compare'
        self.generate_all_button.visible=name=='Compare'
        self.generate_button.text='Generate selected level' if name=='Compare' else 'Generate preview'
        self.export_button.text='Export selected ZIP' if name=='Compare' else 'Export preview ZIP'
        self.update_images()
        if name == 'Manifest':
            self.update_manifest()

    def select_stage(self, title):
        return self.curriculum_editor.select(title)

    def refresh_documents(self):
        try:
            previous = self.document.value
            self.documents = read_documents(self.data)
            self.documents += [doc for doc in self.project_documents if not any(item['id']==doc['id'] for item in self.documents)]
            self.document.items = [f"{d['title']} [{d['id'][:8]}]" for d in self.documents]
            self.document.set_value(previous if previous in self.document.items else
                                    next(iter(self.document.items), ''), notify=False)
            self.select_document(self.document.value)
        except (OSError, sqlite3.Error, ValueError) as error:
            self.status.text = f'Cannot read imported scans: {error}'

    def select_document(self, _):
        index = self.document.index
        doc = self.documents[index] if 0 <= index < len(self.documents) else None
        self.page.items = [str(p['number']) for p in doc['pages']] if doc else []
        if self.page.items:
            self.page.set_value(self.page.items[0], notify=False)
        self.dirty()

    def load_preset(self):
        self.preview_values.clear()
        self.displayed_values.clear()
        self.recipe = deepcopy(recipes.PRESETS[self.preset.value])
        self.render_recipe()
        self.dirty()

    def clear_recipe(self):
        self.preview_values.clear()
        self.displayed_values.clear()
        self.recipe = []
        self.render_recipe()
        self.dirty()

    def show_add_effect_menu(self):
        if len(self.recipe) >= 12:
            return
        items = [MenuItem(category, submenu=[
            MenuItem(recipes.EFFECTS[kind]['label'], lambda kind=kind: self.add_effect(kind),
                     description=recipes.EFFECTS[kind].get('description', ''))
            for kind in kinds]) for category, kinds in EFFECT_CATEGORIES]
        Menu.show(self.app.ctx, self.add_button, items, title='Add Effect · type to search')

    def add_effect(self, kind):
        if len(self.recipe) >= 12:
            return
        self.recipe.append(recipes.entry(kind, uuid.uuid4().hex))
        self.render_recipe()
        self.dirty()

    def change_parameter(self, item, key, value):
        item['parameters'][key] = value
        self.dirty()

    def toggle_effect(self, item, enabled, fields):
        item['enabled'] = enabled
        fields.enabled = enabled
        self.dirty()

    def move_effect(self, index, delta):
        destination = index + delta
        if 0 <= destination < len(self.recipe):
            self.recipe[index], self.recipe[destination] = self.recipe[destination], self.recipe[index]
            self.render_recipe()
            self.dirty()

    def remove_effect(self, index):
        item=self.recipe.pop(index)
        self.preview_values.pop(item['id'],None)
        self.displayed_values.pop(item['id'],None)
        self.render_recipe()
        self.dirty()

    def render_recipe(self):
        self.clear(self.effect_cards)
        if not self.recipe:
            self.effect_cards.add(Label('Clean reference · no scan effects.'))
        for index, item in enumerate(self.recipe):
            definition = recipes.EFFECTS[item['type']]
            fields = Column(spacing=4, enabled=item['enabled'])
            for key, field in definition['fields'].items():
                changed = lambda value, item=item, key=key: self.change_parameter(item, key, value)
                if 'options' in field:
                    control = Dropdown(field['label'], field['options'], item['parameters'][key],
                                       on_change=changed)
                else:
                    control = NumericParameter(item,key,field,self.dirty,self.preview_values,self.displayed_values)
                fields.add(control)
            actions = Row(
                Checkbox('Enabled', item['enabled'], on_change=lambda value, item=item, fields=fields:
                         self.toggle_effect(item, value, fields)),
                Button('Up', lambda item=item: self.move_effect(self.recipe.index(item), -1), enabled=index > 0),
                Button('Down', lambda item=item: self.move_effect(self.recipe.index(item), 1), enabled=index < len(self.recipe)-1),
                Button('Remove', lambda item=item: self.remove_effect(self.recipe.index(item))), spacing=4)
            panel = RecipePanel(f"{index+1:02d}  {definition['label']}", actions, fields,
                recipe_item=item, on_order=self.sync_panel_order,
                description=definition.get('description', ''),
                collapsed=self.active_level().get('collapsed',{}).get(item['id'],False))
            panel.actions = actions
            self.effect_cards.add(panel)
        self.add_button.enabled = len(self.recipe) < 12

    def sync_panel_order(self):
        ordered = [panel.recipe_item for panel in self.effect_cards.children
                   if isinstance(panel, RecipePanel)]
        if [item['id'] for item in ordered] != [item['id'] for item in self.recipe]:
            self.recipe = ordered
            # Keep the grabbed native node alive through its release handler.
            for index, panel in enumerate(self.effect_cards.children):
                panel.set('text', f"{index+1:02d}  {recipes.EFFECTS[panel.recipe_item['type']]['label']}")
                panel.actions.children[1].enabled = index > 0
                panel.actions.children[2].enabled = index < len(ordered)-1
            self.dirty()

    def payload(self):
        request = dict(stage=self.stage, settings=dict(seed=self.augmentation_seed.value,
                                                       recipe=recipes.validate(self.recipe)))
        overrides={item['id']:{key:value for key,value in self.preview_values.get(item['id'],{}).items()
                              if key in item.get('ranges',{})} for item in self.recipe}
        overrides={identity:values for identity,values in overrides.items() if values}
        if overrides:
            request['settings']['preview_values']=overrides
        if self.stage == '4':
            if not self.documents or not self.page.value:
                raise ValueError('Choose an imported scan and page in the Curriculum workspace.')
            request.update(document_id=self.documents[self.document.index]['id'], page=int(self.page.value))
        else:
            example = next(k for k, value in curriculum.EXAMPLES.items() if value == self.example.value)
            request.update(example=example, font=self.font.value, music_seed=self.music_seed.value)
        return request

    def generate(self):
        return self.previews.generate()

    @staticmethod
    def source_key(request):
        return json.dumps({key: request.get(key) for key in
                           ['stage', 'example', 'music_seed', 'font','document_id','page']}, sort_keys=True)

    def generate_all(self):
        return self.previews.generate_all()

    def generate_level_batch(self, jobs, documents, sources):
        return self.previews.generate_level_batch(jobs, documents, sources)

    def accept_preview(self,manifest,identity):
        item=next((level for level in self.levels if level['id']==identity),None)
        if item is None:
            return
        item['latest']=manifest
        displayed={effect['id']:effect['sampled_parameters'] for effect in manifest['effects'] if 'sampled_parameters' in effect}
        item['displayed_values']=displayed
        if identity==self.active_level_id:
            self.latest=manifest
            self.displayed_values=displayed
            if self.pending_revision==self.revision:
                self.sync_preview_sliders()
        if manifest['source']['kind']=='synthetic':
            self.source_previews[self.source_key(manifest['request'])]=manifest['id']
            if len(self.source_previews)>64:
                del self.source_previews[next(iter(self.source_previews))]

    def resample_recipe(self):
        if self.future is not None:
            return
        self.preview_values.clear()
        self.augmentation_seed.value = (self.augmentation_seed.value+1) % (2**31)
        self.generate()

    def poll(self):
        return self.previews.poll()

    def sync_preview_sliders(self):
        for panel in self.effect_cards.children:
            if not isinstance(panel,RecipePanel):
                continue
            fields=panel.body.children[1]
            for control in fields.children:
                if isinstance(control,NumericParameter):
                    value=self.displayed_values.get(control.item['id'],{}).get(control.key)
                    if value is not None and control.key in control.item.get('ranges',{}):
                        control.fixed.set_value(value,notify=False)

    def pan_view(self, index, x, y):
        self.view_centers[index] = (x,y)
        if self.link_views.value:
            self.view_centers = [(x,y), (x,y)]
            self.compare_centers={key:(x,y) for key in self.compare_ids}
        self.redraw_panned_images()

    def redraw_panned_images(self):
        """Panning changes centers only; keep preview metadata and XML untouched."""
        if self.workspaces.value == 'Compare':
            views = zip(self.compare_images,
                        (self.compare_centers.get(key, (.5,.5)) for key in self.compare_ids))
        elif self.workspaces.value == 'Manifest':
            return
        else:
            count = 1 if self.workspaces.value == 'Curriculum' else 2
            views = zip(self.page_images[:count], self.view_centers[:count])
        for viewport, center in views:
            if viewport.picture is not None:
                viewport.show_page(viewport.picture, center, self.zoom.value)

    def zoom_step(self, delta):
        current = self.current_viewport().scale*100 if self.zoom.value == 'Fit page' else float(self.zoom.value[:-1])
        levels = [25,50,75,100,150,200,400]
        candidates = [level for level in levels if level > current+.01] if delta > 0 else [level for level in levels if level < current-.01]
        if candidates:
            self.zoom.value = f'{candidates[0] if delta > 0 else candidates[-1]}%'

    def update_kern(self):
        """Bind source text to the displayed preview, never pending controls."""
        identity = self.latest['id'] if self.latest else None
        if identity == self.kern_preview_id and identity is not None:
            return
        self.kern_preview_id = identity
        self.kern_info.text = 'Source of the displayed reference · read-only'
        if not self.latest:
            self.kern_text.show_source(message='Generate a synthetic preview to inspect its Humdrum.')
        elif 'source.krn' not in self.latest.get('files', {}):
            self.kern_text.show_source(message='This preview has no Humdrum source. Generate a new synthetic preview; imported scans have no score source.')
        else:
            try:
                source = curriculum.artifact(self.data, identity, 'source.krn').read_text(encoding='utf-8')
                self.kern_text.show_source(source)
                self.kern_info.text = f'{len(source.splitlines())} lines · displayed reference · read-only'
            except (OSError, UnicodeError, ValueError) as error:
                self.kern_text.show_source(message=f'Humdrum source unavailable: {error}')

    def update_images(self):
        self.update_kern()
        suffix = '-1024' if self.resolution.value == 'Model 1024' else ''
        def pictures(manifest):
            key=(manifest['id'],suffix)
            if key not in self.view_cache:
                images=[]
                for name in ['source','augmented']:
                    with PILImage.open(curriculum.artifact(self.data,manifest['id'],f'{name}{suffix}.png')) as opened:
                        images.append(opened.convert('RGB'))
                self.view_cache[key]=images
            return self.view_cache[key]
        for index, viewport in enumerate(self.page_images):
            if self.latest:
                viewport.show_page(pictures(self.latest)[index],self.view_centers[index],self.zoom.value)
            else:
                viewport.clear_page()
        if self.compare_images:
            self.update_compare_labels()
            previews=[item.get('latest') for item in self.levels]
            by_id={item['id']:item.get('latest') for item in self.levels}
            reference=next((preview for preview in previews if preview and self.source_key(preview['request'])==self.source_key(self.source_request())),None)
            reference=reference or next((preview for preview in previews if preview),None)
            self.compare_headers[0].text='Source'+(' · settings changed' if reference and
                self.source_key(reference['request'])!=self.source_key(self.source_request()) else '')
            if self.compare_split.visible:
                for index,(identity,viewport) in enumerate(zip(self.compare_ids,self.compare_images)):
                    manifest=reference if index==0 else by_id.get(identity)
                    if manifest:
                        viewport.show_page(pictures(manifest)[0 if index==0 else 1],
                            self.compare_centers.get(identity,(.5,.5)),self.zoom.value)
                    else:
                        viewport.clear_page()
            keep={preview['id'] for preview in previews if preview}
            if self.latest:
                keep.add(self.latest['id'])
            self.view_cache={key:images for key,images in self.view_cache.items() if key[0] in keep and key[1]==suffix}

    def update_manifest(self):
        self.clear(self.manifest_body)
        self.manifest_body.add(Label('DISPLAYED PREVIEW MANIFEST', bold=True),
            Label('The manifest records the rendered preview; control edits apply on Generate.'))
        if not self.latest:
            self.manifest_body.add(Label('Generate a preview to inspect provenance and executed effects.'))
            return
        self.manifest_body.add(*[Label(line) for line in json.dumps(self.latest, indent=2).splitlines()])

    def export_to(self, path):
        return self.projects.export_to(path)

    def export_dialog(self):
        return self.projects.export_dialog()

    def recipe_document(self):
        return self.projects.recipe_document()

    def project_document(self):
        return self.projects.project_document()

    def save_project_dialog(self):
        return self.projects.save_project_dialog()

    def save_project(self):
        return self.projects.save_project()

    def open_project_dialog(self):
        return self.projects.open_project_dialog()

    def load_project(self, path):
        return self.projects.load_project(path)

    def choose_file(self, kind, callback, **options):
        if self.file_dialog is not None and not self.file_dialog.finished:
            self.file_dialog.focus()
            return

        def completed(path):
            self.file_dialog = None
            if self.closed:
                return
            if not path:
                self.status.text = f"{options['title']} cancelled."
                return
            try:
                callback(path)
            except Exception as error:
                self.status.text = f"{options['title']} failed (existing files are preserved): {error}"

        self.file_dialog = FileDialog(self.app.window, kind, on_result=completed, **options)

    def save_recipe_dialog(self):
        return self.projects.save_recipe_dialog()

    def load_recipe(self, path):
        return self.projects.load_recipe(path)

    def open_recipe_dialog(self):
        return self.projects.open_recipe_dialog()

    def screenshot(self, path):
        size = self.app.window.size if self.app.window and self.app.window.is_open else self.app.size
        self.app.render_raster(*size,full=True)
        for _ in range(100):
            if not buipy.image_stats()['pending']:
                break
            time.sleep(.01)
        buipy.image_poll()
        raster = self.app.render_raster(*size,full=True)
        PILImage.open(io.BytesIO(raster.ppm(0, 0, *size))).save(path)

    def close(self):
        self.closed = True
        if self.file_dialog is not None:
            self.file_dialog.close()
            self.file_dialog = None
        self.worker.close()
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.view_cache.clear()
        return True

    def run(self):
        window = self.app.open()
        window.on_close = self.close
        window.wm('minsize', 1060, 760)
        self.warmup_started_at = time.perf_counter()
        self.progress_bar.visible = True
        self.warmup_future = self.executor.submit(self.worker.start, progress=self.progress_events.put)
        window.after(80, self.poll_warmup)
        try:
            host.run()
        finally:
            if not self.closed:
                self.close()

    def poll_warmup(self):
        return self.previews.poll_warmup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=APP / 'outputs',
                        help='Share imported scans and immutable previews with Bar Review')
    parser.add_argument('--screenshot', type=Path, help='Render a headless PNG and exit')
    parser.add_argument('--workspace', choices=WORKSPACES, default='Curriculum')
    parser.add_argument('--theme', choices=['dark', 'light'], default='dark')
    args = parser.parse_args()
    # Match the documented Homebrew rendering setup when no activation script
    # was used. The Verovio worker inherits this environment.
    if os.name == 'posix' and Path('/opt/homebrew/lib/libcairo.2.dylib').is_file():
        os.environ.setdefault('DYLD_FALLBACK_LIBRARY_PATH', '/opt/homebrew/lib')
    bui.set_theme(args.theme)
    desktop = CurriculumDesktop(args.data_dir)
    desktop.workspaces.set_value(args.workspace)
    if args.screenshot:
        try:
            desktop.screenshot(args.screenshot)
        finally:
            desktop.close()
    else:
        desktop.run()


if __name__ == '__main__':
    main()
