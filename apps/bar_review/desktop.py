"""Curriculum Lab desktop: BUI Blender components over the shared lab backend.

Run with the repository environment: .venv/bin/python apps/bar_review/desktop.py
No web server or Blender installation is needed.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import argparse
import io
import json
import os
from pathlib import Path
from queue import Empty, Queue
import sqlite3
import tempfile
import textwrap
import time
import uuid

from PIL import Image as PILImage

import curriculum
import recipes
import lab_project
from preview_worker import PreviewWorker

try:
    import blenderui as bui
    import buipy
    from desktop_dialog import FileDialog
    from blenderui import host
    from blenderui.components import (
        App, Button, Checkbox, Column, Component, Dropdown, EnumRow, Image,
        Label, Menu, MenuItem, NumberField, NumberSlider, Panel, ProgressBar, Row, ScrollView, Separator, TextField,
    )
except ImportError as error:
    raise SystemExit('Install the desktop extra: uv sync --extra desktop') from error


APP = Path(__file__).resolve().parent
WORKSPACES = ['Curriculum', 'Scan Recipe', 'Compare', 'Manifest']
EFFECT_CATEGORIES = [
    ('Paper & framing', ['scanner_edge', 'page_border', 'framing', 'bindings']),
    ('Ink & printing', ['ink', 'low_ink_periodic', 'low_ink_random', 'lines_degradation']),
    ('Dirt & interference', ['badphotocopy', 'dirty_drum', 'dirty_rollers', 'dirty_screen', 'markup', 'subtle_noise']),
    ('Scan & geometry', ['rotation', 'scan_dpi', 'black_white']),
]


def read_documents(data):
    """Read the existing collection without initializing or changing its DB."""
    database = Path(data) / 'annotations.sqlite3'
    if not database.is_file():
        return []
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
        return [json.loads(row[0]) for row in db.execute('SELECT payload FROM documents ORDER BY rowid')]


def write_new(path, content):
    """Exports never replace a prior export, even when a dialog selects one."""
    with Path(path).expanduser().open('xb') as stream:
        stream.write(content)


def write_recipe(path, content, backup_folder='.recipe-backups'):
    """Update a chosen lab file atomically, preserving its exact previous bytes."""
    path=Path(path).expanduser().absolute()
    backup=None
    if path.exists():
        previous=path.read_bytes()
        if previous == content:
            return None
        folder=path.parent/backup_folder
        folder.mkdir(exist_ok=True)
        backup=folder/f'{path.stem}-{time.time_ns()}-{uuid.uuid4().hex[:8]}{path.suffix}'
        write_new(backup,previous)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix=f'.{path.name}.',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return backup


class RasterImage(Image):
    """Supply decoded pixels to BUI, avoiding 0.4.1's macOS async callback.

    The wheel's image-poll wake can invoke a Python Tk redraw without holding
    the GIL. Pillow decoding on the UI thread avoids that native callback;
    BUI still owns layout, fitting and drawing. Unchanged pages are reused.
    """
    @Image.src.setter
    def src(self, path):
        path = str(path or '')
        if path and path == self._src:
            return
        self._src = path
        self.set_image_source(None, self.FITS[self._fit])
        if path:
            with PILImage.open(path) as opened:
                image = opened.convert('RGBA')
                self.set_image(image.width, image.height, image.tobytes())

    def show_pixels(self, image):
        """Visible pixels already exist in memory; no PNG write/read round trip."""
        rgba = image.convert('RGBA')
        self.set_image(rgba.width, rgba.height, rgba.tobytes())


class PageImage(RasterImage):
    """A clipped image viewport; only visible pixels are supplied to BUI."""
    def __init__(self, on_pan, on_zoom):
        super().__init__('', fit='fill', fill=True)
        self.geom(0, reqwidth=1, reqheight=1)
        self.on_pan, self.on_zoom = on_pan, on_zoom
        self.picture = None
        self.center = (.5, .5)
        self.zoom = 'Fit page'
        self.scale = 1
        self.offset = (0, 0)
        self.drag = None
        self.set('events', True)

    def show_page(self, picture, center, zoom):
        self.picture, self.center, self.zoom = picture, center, zoom
        self.draw_view()

    def clear_page(self):
        self.picture=None
        self.set_image()

    def draw_view(self):
        if self.picture is None or self.w < 2 or self.h < 2:
            return
        image = self.picture
        self.scale = (min(self.w/image.width, self.h/image.height) if self.zoom == 'Fit page'
                      else float(self.zoom.removesuffix('%'))/100)
        width, height = self.w/self.scale, self.h/self.scale
        left = (max(0, min(image.width-width, self.center[0]*image.width-width/2))
                if width < image.width else (image.width-width)/2)
        top = (max(0, min(image.height-height, self.center[1]*image.height-height/2))
               if height < image.height else (image.height-height)/2)
        self.offset = left, top
        view = image.transform((self.w, self.h), PILImage.Transform.AFFINE,
            (1/self.scale, 0, left, 0, 1/self.scale, top),
            resample=PILImage.Resampling.NEAREST if self.scale >= 1 else PILImage.Resampling.BICUBIC,
            fillcolor=(48,48,48))
        self.show_pixels(view)

    def pan(self, dx, dy):
        if self.picture is None:
            return
        image = self.picture
        width, height = self.w/self.scale, self.h/self.scale
        if width >= image.width and height >= image.height:
            return
        left = max(0, min(max(0, image.width-width), self.offset[0]-dx/self.scale))
        top = max(0, min(max(0, image.height-height), self.offset[1]-dy/self.scale))
        x = (left+width/2)/image.width if width < image.width else .5
        y = (top+height/2)/image.height if height < image.height else .5
        self.on_pan(x, y)

    def _on_event(self, kind, ref, a, b):
        if kind == 19:  # Resize/workspace change; redraw at the actual viewport size.
            self.draw_view()
        elif kind == 8:
            self.drag = (a, b)
        elif kind == 9:
            self.drag = None
        elif kind == 11 and self.drag is not None:
            previous, self.drag = self.drag, (a,b)
            self.pan(a-previous[0], b-previous[1])
        elif kind == 15:  # Raw wheel ref carries modifier bits; a is delta.
            mods = int(ref.split()[0])
            if mods & 2:
                self.on_zoom(1 if a > 0 else -1)
            elif mods & 1:
                self.pan(a*48, 0)
            else:
                self.pan(0, a*48)


class NumericParameter(Column):
    """Fixed value or seeded uniform range, with bounded numeric endpoints."""
    def __init__(self, item, key, field, on_edit, preview_values=None, displayed_values=None):
        self.item, self.key, self.field, self.on_edit = item, key, field, on_edit
        self.preview_values = preview_values if preview_values is not None else {}
        options = dict(min=field['min'],max=field['max'],step=field['step'],
                       integer=field['step']==1,precision=2)
        value = item['parameters'][key]
        ranged = key in item.get('ranges',{})
        self.saved_bounds = list(item['ranges'][key]) if ranged else None
        low,high = item.get('ranges',{}).get(key,[value,value])
        if ranged:
            value=self.preview_values.get(item['id'],{}).get(key,
                (displayed_values or {}).get(item['id'],{}).get(key,value))
            value=max(low,min(high,value))
            options.update(min=low,max=high)
        self.fixed = NumberSlider(field['label'],value,on_change=self.change_fixed,
            description='Current preview value; edit and Generate to try a specific value',**options)
        bounds_options={**options,'min':field['min'],'max':field['max']}
        self.low = NumberField('Min',low,on_change=lambda value:self.change_bound(0,value),**bounds_options)
        self.high = NumberField('Max',high,on_change=lambda value:self.change_bound(1,value),**bounds_options)
        self.bounds = Row(self.low,self.high,visible=ranged,spacing=4)
        self.toggle = Checkbox('Range',ranged,on_change=self.toggle_range,weight=.3,
                               description='Sample a value between Min and Max using the recipe seed')
        super().__init__(Row(self.fixed,self.toggle,spacing=4),self.bounds,spacing=4)

    def change_fixed(self,value):
        self.item['parameters'][self.key]=value
        if self.key in self.item.get('ranges',{}):
            self.preview_values.setdefault(self.item['id'],{})[self.key]=value
        self.on_edit()

    def toggle_range(self,enabled):
        if enabled:
            bounds = (list(self.saved_bounds) if self.saved_bounds is not None else
                      [self.field['min'],self.field['max']] if self.item['type']=='rotation'
                      else [self.fixed.value,self.fixed.value])
            self.item.setdefault('ranges',{})[self.key]=bounds
            self.low.set_value(bounds[0],notify=False)
            self.high.set_value(bounds[1],notify=False)
        else:
            self.saved_bounds = list(self.item['ranges'][self.key])
            self.item['parameters'][self.key]=self.fixed.value
            self.item.get('ranges',{}).pop(self.key,None)
            if not self.item.get('ranges'):
                self.item.pop('ranges',None)
            self.preview_values.get(self.item['id'],{}).pop(self.key,None)
        self.update_limits()
        self.bounds.visible = enabled
        self.on_edit()

    def change_bound(self,index,value):
        bounds=self.item['ranges'][self.key]
        bounds[index]=value
        if bounds[0]>bounds[1]:
            bounds[1-index]=value
            (self.high if index==0 else self.low).set_value(value,notify=False)
        self.update_limits()
        self.on_edit()

    def update_limits(self):
        low,high=self.item.get('ranges',{}).get(self.key,[self.field['min'],self.field['max']])
        self.fixed.set('min',low)
        self.fixed.set('max',high)
        value=max(low,min(high,self.fixed.value))
        self.fixed.set_value(value,notify=False)
        overrides=self.preview_values.get(self.item['id'],{})
        if self.key in overrides:
            overrides[self.key]=value


class ResizeDivider(Component):
    """Blender-style region edge, driven by the kit's captured pointer events."""
    TYPE = 'frame'

    def __init__(self, row, index):
        super().__init__(weight=0, description='Drag to resize · double-click to reset widths')
        self.row, self.index, self.drag = row, index, None
        self.geom(0, reqwidth=7, reqheight=1)
        self.set('events', True)
        self.set('cursor', 1)  # Horizontal resize cursor.
        self.set('bg', (.14,.14,.14,1))

    def _on_event(self, kind, ref, a, b):
        if kind == 8:
            left, right = self.row.panes[self.index:self.index+2]
            self.drag = (self.x+a, left.w, left.w+right.w, left.weight+right.weight)
        elif kind == 11 and self.drag:
            x, width, total, weight = self.drag
            low, high = self.row.minimums[self.index:self.index+2]
            # If a window is smaller than both minima, retain usable proportions.
            factor = min(1, total/(low+high))
            size = max(low*factor, min(total-high*factor, width+self.x+a-x))
            left, right = self.row.panes[self.index:self.index+2]
            left.weight, right.weight = weight*size/total, weight*(total-size)/total
        elif kind == 9:
            self.drag = None
        elif kind == 10:
            self.drag = None
            self.row.reset_sizes()
        elif kind == 12:
            self.set('bg', (.30,.40,.55,1))
        elif kind == 13:
            self.set('bg', (.14,.14,.14,1))


class ResizableRow(Row):
    def __init__(self, *panes, minimums, **kwargs):
        self.panes, self.minimums = list(panes), list(minimums)
        self.default_weights = [pane.weight for pane in panes]
        self.dividers = [ResizeDivider(self, i) for i in range(len(panes)-1)]
        children = []
        for index, pane in enumerate(panes):
            if index:
                children.append(self.dividers[index-1])
            children.append(pane)
        super().__init__(*children, spacing=0, **kwargs)

    def sync_visibility(self):
        for index, divider in enumerate(self.dividers):
            divider.visible = self.panes[index].visible and self.panes[index+1].visible

    def reset_sizes(self):
        for pane, weight in zip(self.panes, self.default_weights):
            pane.weight = weight


class RecipePanel(Panel):
    """Keep Blender's native panel-grip reordering in the executable recipe."""
    def __init__(self, *args, recipe_item, on_order, **kwargs):
        super().__init__(*args, **kwargs)
        self.recipe_item = recipe_item
        self.on_order = on_order
        self.set('events', True)

    def _on_event(self, kind, ref, a, b):
        super()._on_event(kind, ref, a, b)
        if kind == 9:  # BK_EV_RELEASE; motion has already reordered siblings.
            self.on_order()


class CurriculumDesktop:
    def __init__(self, data=APP / 'outputs'):
        self.data = Path(data).expanduser().resolve()
        self.documents = read_documents(self.data)
        self.stage = '0'
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
        self.status = Label('Choose a stage and generate a preview.', icon='INFO')
        self.progress_bar = ProgressBar(0, text='Ready', visible=False)
        self.preview_info = Label('No preview generated')
        self.stage_info = Column()
        self.stage_choice = Dropdown('Stage', [s['title'] for s in curriculum.STAGES],
                                     on_change=self.select_stage)
        self.example = Dropdown('Example', [], on_change=lambda _: self.dirty())
        self.font = Dropdown('Font', ['Leipzig', 'Bravura', 'Petaluma'],
                             on_change=lambda _: self.dirty())
        self.music_seed = NumberField('Music seed', 7, min=0, max=2**31-1,
                                      on_change=lambda _: self.dirty())
        self.augmentation_seed = NumberField('Recipe seed', 42, min=0, max=2**31-1,
                                             on_change=lambda _: self.dirty())
        self.resample_button = Button('New sample',self.resample_recipe,weight=.55,
            description='Advance the recipe seed and generate another reproducible sample')
        self.document = Dropdown('Document', [], on_change=self.select_document)
        self.page = Dropdown('Page', [], on_change=lambda _: self.dirty())
        self.synthetic_controls = Column(self.example, self.font, self.music_seed, spacing=5)
        self.scan_controls = Column(self.document, self.page,
            Button('Refresh imported scans', self.refresh_documents, icon='FILE_REFRESH'),
            Label('Import scans in Bar Review to use them here.'), spacing=5, visible=False)
        self.source_panel = ScrollView(Column(
            Panel('Curriculum stages', self.stage_choice, self.stage_info),
            Panel('Source', self.synthetic_controls, self.scan_controls),
            Panel('Provenance', Label('Proposed stages; exploration only.'),
                  Label('Source scans and labels stay unchanged.'),
                  Label('Previews have no dataset split.')), spacing=12), fill=True, weight=0.24)

        self.preset = Dropdown('Starter', list(recipes.PRESETS), 'light-copy')
        self.level_choice=Dropdown('Level',[item['name'] for item in self.levels],'Mild',on_change=self.select_level)
        self.level_name=TextField('Name','Mild',on_change=self.rename_level)
        self.level_buttons=[Button('Add',self.add_level),Button('Duplicate',self.duplicate_level),Button('Remove',self.remove_level)]
        self.effect_cards = Column(spacing=8)
        self.add_button = Button('Add Effect', self.show_add_effect_menu, icon='ADD',
            description='Choose a category, or type to search all effects')
        self.recipe_panel = ScrollView(Column(
            Panel('Degradation levels',self.level_choice,self.level_name,Row(*self.level_buttons,spacing=4),
                  Row(Button('Move left',lambda:self.move_level(-1)),Button('Move right',lambda:self.move_level(1)),spacing=4)),
            Panel('Scan recipe', Row(self.augmentation_seed,self.resample_button,spacing=4), self.preset,
                  Row(Button('Load starter', self.load_preset), Button('Clear', self.clear_recipe)),
                  self.add_button),
            Label('Applied top to bottom · up to 12 steps'), self.effect_cards,
            spacing=10), fill=True, weight=0.29)

        self.resolution = EnumRow('', ['Native', 'Model 1024'], 'Native',
                                  on_change=lambda _: self.update_images())
        self.view_centers = [(.5,.5), (.5,.5)]
        self.zoom = Dropdown('Zoom', ['Fit page', '25%', '50%', '75%', '100%', '150%', '200%', '400%'], 'Fit page',
                             on_change=lambda _: self.update_images())
        self.link_views = Checkbox('Link views', True)
        self.page_images = [PageImage(lambda x,y,i=i: self.pan_view(i,x,y), self.zoom_step) for i in range(2)]
        self.image_split = ResizableRow(*[
            Column(Label(title, bold=True), image, fill=True, spacing=6)
            for title, image in zip(['SOURCE / REFERENCE', 'AUGMENTED'], self.page_images)],
            minimums=[120,120], fill=True)
        self.image_region=Column(self.image_split,fill=True)
        self.compare_split=None
        self.compare_images=[]
        self.compare_headers=[]
        self.comparison = Column(
            Row(self.resolution, Button('−', lambda: self.zoom_step(-1), weight=.15), self.zoom,
                Button('+', lambda: self.zoom_step(1), weight=.15),
                Button('Fit', lambda: self.zoom.set_value('Fit page'), weight=.3),
                self.link_views, spacing=6),
            self.image_region,
            Label('Scroll to pan · Shift+scroll sideways · Ctrl+scroll to zoom · drag to move'),
            fill=True, spacing=8)
        self.manifest_body = Column()
        self.manifest_view = ScrollView(self.manifest_body, fill=True, visible=False)
        self.viewer = Column(self.preview_info, self.comparison, self.manifest_view,
                             fill=True, spacing=10, weight=.60)
        self.main_split = ResizableRow(self.source_panel, self.viewer, self.recipe_panel,
                                      minimums=[180,320,220], fill=True)
        self.generate_button = Button('Generate preview', self.generate, icon='RENDER_STILL')
        self.generate_all_button=Button('Generate all levels',self.generate_all,icon='RENDER_STILL',visible=False)
        self.export_button = Button('Export preview ZIP', self.export_dialog, icon='EXPORT', enabled=False)
        self.workspaces = EnumRow('', WORKSPACES, 'Curriculum', on_change=self.set_workspace)
        self.theme_choice=Dropdown('', ['Dark', 'Light'], bui.theme_name().title(), weight=.14,
                                  on_change=lambda value: bui.set_theme(value.lower()))
        self.app = App('MuSViT · Curriculum Lab', (1520, 960),
            Row(Label('MuSViT', icon='SEQ_LUMA_WAVEFORM', bold=True, weight=0),
                self.workspaces,
                self.theme_choice, spacing=18),
            Separator(.25, line=True),
            Row(self.generate_button,self.generate_all_button,self.export_button,
                Button('Save project', self.save_project_dialog, icon='FILE_TICK'),
                Button('Open project', self.open_project_dialog, icon='FILE_FOLDER'), spacing=8),
            self.main_split,
            Separator(.25, line=True), self.progress_bar, self.status,
            padding=12, spacing=8)
        self.app.bind('ctrl+enter', self.generate)
        self.app.bind('ctrl+s', self.save_project_dialog)
        self.app.bind('left', lambda: self.current_viewport().pan(80, 0))
        self.app.bind('right', lambda: self.current_viewport().pan(-80, 0))
        self.app.bind('up', lambda: self.current_viewport().pan(0, 80))
        self.app.bind('down', lambda: self.current_viewport().pan(0, -80))
        self.rebuild_compare()
        self.refresh_documents()
        self.select_stage(curriculum.STAGES[0]['title'])
        self.render_recipe()
        self.update_manifest()

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
        self.update_images()

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
        self.source_panel.visible = name == 'Curriculum'
        self.recipe_panel.visible = name in ('Curriculum', 'Scan Recipe')
        self.main_split.sync_visibility()
        self.comparison.visible = name != 'Manifest'
        self.manifest_view.visible = name == 'Manifest'
        self.image_split.visible=name!='Compare'
        if self.compare_split:
            self.compare_split.visible=name=='Compare'
        self.generate_all_button.visible=name=='Compare'
        self.generate_button.text='Generate selected level' if name=='Compare' else 'Generate preview'
        self.export_button.text='Export selected ZIP' if name=='Compare' else 'Export preview ZIP'
        self.update_images()
        if name == 'Manifest':
            self.update_manifest()

    def select_stage(self, title):
        item = next(s for s in curriculum.STAGES if s['title'] == title)
        self.stage = item['id']
        self.clear(self.stage_info)
        self.stage_info.add(*self.lines(item['description']), Separator(.3),
                            *self.lines('Focus: ' + item['focus']), Separator(.3),
                            *self.lines('Proposed mix: ' + item['mix']))
        self.synthetic_controls.visible = self.stage != '4'
        self.scan_controls.visible = self.stage == '4'
        self.example.items = [curriculum.EXAMPLES[key] for key in item['examples']]
        if self.example.items:
            self.example.set_value(self.example.items[0], notify=False)
        self.dirty()

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
        if self.future is not None:
            return
        try:
            request = self.payload()
            self.stash_active()
            self.pending_level_id=self.active_level_id
            self.pending_batch=False
            self.pending_revision = self.revision
            self.started_at = time.perf_counter()
            while not self.progress_events.empty():
                self.progress_events.get_nowait()
            self.progress_state = dict(label='Submitting preview job', fraction=.02)
            self.progress_bar.visible = True
            self.progress_bar.set_value(.02)
            self.progress_bar.text = 'Submitting preview job · 0.0s'
            self.generate_button.enabled = False
            self.generate_all_button.enabled = False
            self.resample_button.enabled = False
            self.status.text = 'Rendering preview…'
            self.future = self.executor.submit(self.worker.preview, self.data,
                deepcopy(request), deepcopy(self.documents), progress=self.progress_events.put,
                source_preview=self.source_previews.get(self.source_key(request)))
            if self.app.window:
                self.app.window.after(80, self.poll)
        except Exception as error:
            self.status.text = f'Preview failed: {error}'
            self.generate_button.enabled = True
            self.generate_all_button.enabled = True
            self.resample_button.enabled = True
            self.progress_bar.text = 'Preview failed'

    @staticmethod
    def source_key(request):
        return json.dumps({key: request.get(key) for key in
                           ['stage', 'example', 'music_seed', 'font','document_id','page']}, sort_keys=True)

    def generate_all(self):
        if self.future is not None:
            return
        try:
            source={key:value for key,value in self.payload().items() if key!='settings'}
            self.stash_active()
            jobs=[dict(level_id=item['id'],name=item['name'],payload={**source,'settings':deepcopy(item['settings'])})
                  for item in self.levels]
            self.pending_batch=True
            self.pending_revision=self.revision
            self.started_at=time.perf_counter()
            while not self.progress_events.empty():
                self.progress_events.get_nowait()
            self.progress_state=dict(label='Generating degradation levels',fraction=.02)
            self.progress_bar.visible=True
            self.generate_button.enabled=self.generate_all_button.enabled=self.resample_button.enabled=False
            self.status.text='Generating all levels from the selected source…'
            self.future=self.executor.submit(self.generate_level_batch,jobs,deepcopy(self.documents),dict(self.source_previews))
            if self.app.window:
                self.app.window.after(80,self.poll)
        except Exception as error:
            self.generate_button.enabled=self.generate_all_button.enabled=self.resample_button.enabled=True
            self.status.text=f'Cannot generate levels: {error}'

    def generate_level_batch(self,jobs,documents,sources):
        results=[]
        for index,job in enumerate(jobs):
            if self.closed:
                break
            def progress(value,index=index,name=job['name']):
                self.progress_events.put(dict(label=f'{index+1}/{len(jobs)} {name}: {value["label"]}',
                    fraction=(index+min(.99,value['fraction']))/len(jobs)))
            try:
                key=self.source_key(job['payload'])
                manifest=self.worker.preview(self.data,job['payload'],documents,progress=progress,
                    source_preview=sources.get(key))
                if manifest['source']['kind']=='synthetic':
                    sources[key]=manifest['id']
                results.append(dict(level_id=job['level_id'],manifest=manifest))
            except Exception as error:
                results.append(dict(level_id=job['level_id'],error=str(error)))
        return results

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
        """Only the window thread touches BUI nodes; worker returns plain data."""
        if self.closed or self.future is None:
            return
        try:
            while True:
                self.progress_state = self.progress_events.get_nowait()
        except Empty:
            pass
        elapsed = time.perf_counter()-self.started_at
        self.progress_bar.set_value(self.progress_state['fraction'])
        self.progress_bar.text = f"{self.progress_state['label']} · {elapsed:.1f}s"
        if not self.future.done():
            if self.app.window:
                self.app.window.after(80, self.poll)
            return
        future, self.future = self.future, None
        self.generate_button.enabled = True
        self.generate_all_button.enabled = True
        self.resample_button.enabled = True
        try:
            result=future.result()
            self.stash_active()
            errors=[]
            if self.pending_batch:
                for entry in result:
                    if 'manifest' in entry:
                        self.accept_preview(entry['manifest'],entry['level_id'])
                    else:
                        errors.append(entry['error'])
            else:
                self.accept_preview(result,self.pending_level_id)
            self.export_button.enabled = self.latest is not None
            self.preview_info.text = ((f"{self.active_level()['name']} · preview {self.latest['id'][:8]} · "
                f"{self.latest['source_dimensions']} → {self.latest['augmented_dimensions']} · "
                f"{len(self.latest['effects'])} active effects") if self.latest else 'No preview for the selected level')
            self.update_images()
            self.update_manifest()
            elapsed = time.perf_counter()-self.started_at
            reused = ' · reused source engraving' if self.latest and self.latest.get('source_reused') else ''
            self.progress_bar.set_value(1)
            self.progress_bar.text = f'{"Levels" if self.pending_batch else "Preview"} ready in {elapsed:.2f}s{reused}'
            self.status.text = ('Preview ready · exploration only · export saves this exact preview.'
                if self.pending_revision == self.revision else
                'Preview ready for earlier settings · generate again to apply current edits.')
            if errors:
                self.status.text=f'{len(errors)} level(s) failed: {errors[0][:220]}'
        except Exception as error:
            self.progress_bar.text = f'Preview failed after {elapsed:.1f}s'
            self.status.text = f'Preview failed: {str(error)[:350]}'
            print(f'Preview failed: {error}', flush=True)

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
        self.update_images()

    def zoom_step(self, delta):
        current = self.current_viewport().scale*100 if self.zoom.value == 'Fit page' else float(self.zoom.value[:-1])
        levels = [25,50,75,100,150,200,400]
        candidates = [level for level in levels if level > current+.01] if delta > 0 else [level for level in levels if level < current-.01]
        if candidates:
            self.zoom.value = f'{candidates[0] if delta > 0 else candidates[-1]}%'

    def update_images(self):
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
        if not self.latest:
            raise ValueError('Generate a preview first.')
        write_new(path, curriculum.export_preview(self.data, self.latest['id']))

    def export_dialog(self):
        if not self.latest:
            self.status.text = 'Generate a preview before exporting.'
            return
        try:
            # Bind to the displayed preview at dialog-open time, even if a
            # background job completes while the browser window is open.
            preview_id = self.latest['id']
            def exported(path):
                write_new(path, curriculum.export_preview(self.data, preview_id))
                self.status.text = f'Exported displayed preview to {path}'
            self.choose_file('save', exported, title='Export displayed preview',
                initialfile=f"curriculum-{preview_id[:8]}.zip", defaultextension='.zip')
        except Exception as error:
            self.status.text = f'Export failed (existing files are preserved): {error}'

    def recipe_document(self):
        recipe=recipes.validate(self.recipe)
        return dict(schema_version=2 if any(item.get('ranges') for item in recipe) else 1,
                    seed=self.augmentation_seed.value, recipe=recipe)

    def project_document(self):
        self.stash_active()
        previews={item['latest']['id']:deepcopy(item['latest']) for item in self.levels if item.get('latest')}
        levels=[dict(id=item['id'],name=item['name'],settings=deepcopy(item['settings']),
                     preset=item.get('preset','clean'),collapsed=deepcopy(item.get('collapsed',{})),
                     preview_id=item['latest']['id'] if item.get('latest') else None) for item in self.levels]
        compare_weights={key:pane.weight for key,pane in zip(self.compare_ids,self.compare_split.panes)}
        document=lab_project.validate(dict(kind=lab_project.KIND,schema_version=1,source=self.source_settings(),
            levels=levels,active_level=self.active_level_id,previews=previews,
            view=dict(workspace=self.workspaces.value,resolution=self.resolution.value,zoom=self.zoom.value,
                link_views=self.link_views.value,centers=[list(pair) for pair in self.view_centers],
                compare_centers={key:list(pair) for key,pair in self.compare_centers.items()},
                sidebar_weights=[pane.weight for pane in self.main_split.panes],
                image_weights=[pane.weight for pane in self.image_split.panes],
                compare_weights=compare_weights,theme=bui.theme_name(),
                panels={f'{region}:{panel.title}':panel.collapsed for region,container in
                    [('source',self.source_panel),('recipe',self.recipe_panel)]
                    for panel in container.children[0].children if isinstance(panel,Panel)})))
        return json.loads(json.dumps(document))

    def save_project_dialog(self):
        try:
            content=lab_project.bundle(self.project_document(),self.data,self.documents)
            def saved(path):
                backup=write_recipe(path,content,backup_folder='.project-backups')
                self.project_path=Path(path).expanduser().resolve()
                self.status.text=f'Saved project to {self.project_path}'+(' · previous version backed up' if backup else '')
            self.choose_file('save',saved,title='Save Curriculum Lab project',
                initialfile=self.project_path.name if self.project_path else 'curriculum-lab.musvitlab',
                initialdir=str(self.project_path.parent) if self.project_path else None,
                defaultextension='.musvitlab',filetypes=[('Curriculum Lab projects','*.musvitlab')])
        except Exception as error:
            self.status.text=f'Project save failed: {error}'

    def open_project_dialog(self):
        if self.future is not None:
            self.status.text='Wait for preview generation before opening another project.'
            return
        self.choose_file('open',self.load_project,title='Open Curriculum Lab project',
            initialdir=str(self.project_path.parent) if self.project_path else None,
            filetypes=[('Curriculum Lab projects','*.musvitlab'),('Legacy recipes','*.json')])

    def load_project(self,path):
        import zipfile
        if self.future is not None:
            raise ValueError('Wait for preview generation before opening another project.')
        if not zipfile.is_zipfile(path):
            self.load_recipe(path)
            self.stash_active()
            self.status.text=f'Imported legacy recipe into {self.active_level()["name"]}; use Save project to retain the whole lab.'
            return
        document,embedded=lab_project.unbundle(path,self.data)
        self.restoring=True
        try:
            self.levels=document['levels']
            for item in self.levels:
                item['latest']=document['previews'].get(item.get('preview_id'))
                item['displayed_values']={effect['id']:effect['sampled_parameters'] for effect in
                    (item['latest']['effects'] if item['latest'] else []) if 'sampled_parameters' in effect}
            self.project_documents=[embedded] if embedded else []
            self.refresh_documents()
            source=document['source']
            self.font.set_value(source['font'],notify=False)
            self.music_seed.set_value(source['music_seed'],notify=False)
            stage=next(item for item in curriculum.STAGES if item['id']==source['stage'])
            self.stage_choice.set_value(stage['title'],notify=False)
            self.select_stage(stage['title'])
            if source.get('example'):
                self.example.set_value(curriculum.EXAMPLES[source['example']],notify=False)
            index=next((i for i,doc in enumerate(self.documents) if doc['id']==source.get('document_id')),None)
            if index is not None:
                self.document.set_value(self.document.items[index],notify=False)
                self.select_document(self.document.value)
                self.page.set_value(str(source['page']),notify=False)
            self.view_cache.clear()
            self.source_previews={self.source_key(manifest['request']):manifest['id']
                for manifest in document['previews'].values() if manifest['source']['kind']=='synthetic'}
            self.active_level_id=document['active_level']
            self.compare_centers={key:tuple(pair) for key,pair in document['view'].get('compare_centers',{}).items()}
            self.compare_weights={}
            self.rebuild_compare()
            view=document['view']
            self.view_centers=[tuple(pair) for pair in view['centers']]
            self.resolution.set_value(view['resolution'],notify=False)
            self.zoom.set_value(view['zoom'],notify=False)
            self.link_views.set_value(view['link_views'],notify=False)
            for row,weights in [(self.main_split,view['sidebar_weights']),(self.image_split,view['image_weights'])]:
                for pane,weight in zip(row.panes,weights):
                    pane.weight=weight
            for identity,pane in zip(self.compare_ids,self.compare_split.panes):
                pane.weight=view.get('compare_weights',{}).get(identity,1)
            bui.set_theme(view['theme']);self.theme_choice.set_value(view['theme'].title(),notify=False)
            self.activate_level(self.active_level_id)
            for region,container in [('source',self.source_panel),('recipe',self.recipe_panel)]:
                for panel in container.children[0].children:
                    if isinstance(panel,Panel):
                        panel.collapsed=view.get('panels',{}).get(f'{region}:{panel.title}',False)
            self.workspaces.set_value(view['workspace'],notify=False)
            self.set_workspace(view['workspace'])
            self.update_images()
            self.update_manifest()
            self.project_path=Path(path).expanduser().resolve()
            self.revision+=1
            self.status.text=f'Opened project {self.project_path.name} · {len(self.levels)} levels · saved previews restored'
        finally:
            self.restoring=False

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
        try:
            content = json.dumps(self.recipe_document(), indent=2).encode()
            def saved(path):
                backup=write_recipe(path, content)
                self.recipe_path=Path(path).expanduser().resolve()
                self.status.text = f'Saved recipe to {path}'+(' · previous version backed up' if backup else '')
                self.status.description = f'Previous version: {backup}' if backup else str(self.recipe_path)
            self.choose_file('save', saved, title='Save scan recipe',
                initialfile=self.recipe_path.name if self.recipe_path else 'scan-recipe.json',
                initialdir=str(self.recipe_path.parent) if self.recipe_path else None,
                defaultextension='.json')
        except Exception as error:
            self.status.text = f'Recipe save failed (existing files are preserved): {error}'

    def load_recipe(self, path):
        value = json.loads(Path(path).read_text())
        if not isinstance(value, dict) or value.get('schema_version') not in (1,2) or 'recipe' not in value:
            raise ValueError('Expected a version 1 or 2 desktop recipe with seed and recipe fields.')
        config = curriculum.settings(value)
        self.recipe = config['recipe']
        self.preview_values.clear()
        self.displayed_values.clear()
        self.augmentation_seed.set_value(config['seed'], notify=False)
        self.render_recipe()
        self.dirty()
        self.recipe_path=Path(path).expanduser().resolve()
        self.status.text=f'Loaded recipe from {self.recipe_path}. Generate a preview to apply it.'

    def open_recipe_dialog(self):
        try:
            self.choose_file('open', self.load_recipe, title='Open scan recipe',
                initialdir=str(self.recipe_path.parent) if self.recipe_path else None,
                filetypes=[('Recipes', '*.json')])
        except Exception as error:
            self.status.text = f'Recipe load failed: {error}'

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
        if self.closed or self.warmup_future is None:
            return
        # A queued preview owns progress/status as soon as Generate is pressed.
        if self.future is None and self.latest is None:
            try:
                while True:
                    self.progress_state = self.progress_events.get_nowait()
            except Empty:
                pass
            self.progress_bar.set_value(self.progress_state['fraction'])
            elapsed = time.perf_counter()-self.warmup_started_at
            self.progress_bar.text = f"{self.progress_state['label']} · {elapsed:.1f}s"
        if not self.warmup_future.done():
            self.app.window.after(80, self.poll_warmup)
            return
        warmup, self.warmup_future = self.warmup_future, None
        try:
            warmup.result()
            if self.future is None and self.latest is None:
                self.progress_bar.set_value(1)
                self.progress_bar.text = 'Preview worker ready'
        except Exception as error:
            if self.future is None:
                self.progress_bar.text = 'Worker warmup failed; Generate will retry'
                self.status.text = str(error)[:350]


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
