"""Construct the workbench's initial layout and bind application callbacks.

This module owns presentation and initial widget values, not project persistence
or worker execution. The coordinator initializes session state before calling it.
"""
from typing import TYPE_CHECKING
import sys

import blenderui as bui
from blenderui.components import (
    App, Button, Checkbox, Column, Dropdown, EnumRow, Label, MenuBar, MenuItem, NumberField, Panel,
    ProgressBar, Row, ScrollView, Separator, TextField,
)

import curriculum
import recipes
from desktop_widgets import PageImage, ResizableRow, SourceText

if TYPE_CHECKING:
    from desktop import CurriculumDesktop


WORKSPACES = ['Curriculum', 'Scan Recipe', 'Compare', 'Manifest']


def file_menu(desktop: "CurriculumDesktop") -> MenuBar:
    """Use the same actions for menus, toolbar buttons and window shortcuts."""
    modifier = 'Cmd' if sys.platform == 'darwin' else 'Ctrl'
    return MenuBar(('File', [
        MenuItem('Open project…', desktop.open_project_dialog, shortcut=f'{modifier} O', icon='FILE_FOLDER'),
        MenuItem('Save project', desktop.save_project, shortcut=f'{modifier} S', icon='FILE_TICK'),
        MenuItem('Save project as…', desktop.save_project_dialog, shortcut=f'{modifier} Shift S'),
        '-',
        MenuItem('Import recipe…', desktop.open_recipe_dialog),
        MenuItem('Export recipe…', desktop.save_recipe_dialog),
        MenuItem('Export preview ZIP…', desktop.export_dialog, shortcut=f'{modifier} Shift E', icon='EXPORT'),
    ]))


def build_layout(desktop: "CurriculumDesktop") -> None:
    """Attach the initial BUI tree to the CurriculumDesktop coordinator."""
    desktop.status = Label('Choose a stage and generate a preview.', icon='INFO', weight=.7)
    desktop.progress_bar = ProgressBar(0, text='Ready', visible=False, weight=.3)
    desktop.preview_info = Label('No preview generated')
    desktop.stage_info = Column()
    desktop.stage_choice = Dropdown('Stage', [s['title'] for s in desktop.stages],
                                 on_change=desktop.select_stage)
    desktop.example = Dropdown('Example', [], on_change=lambda _: desktop.dirty())
    desktop.font = Dropdown('Font', ['Leipzig', 'Bravura', 'Petaluma'],
                         on_change=lambda _: desktop.dirty())
    desktop.music_seed = NumberField('Music seed', 7, min=0, max=2**31-1,
                                  on_change=lambda _: desktop.dirty())
    desktop.augmentation_seed = NumberField('Recipe seed', 42, min=0, max=2**31-1,
                                         on_change=lambda _: desktop.dirty())
    desktop.resample_button = Button('New sample',desktop.resample_recipe,weight=.55,
        description='Advance the recipe seed and generate another reproducible sample')
    desktop.document = Dropdown('Document', [], on_change=desktop.select_document)
    desktop.page = Dropdown('Page', [], on_change=lambda _: desktop.dirty())
    desktop.synthetic_controls = Column(desktop.example, desktop.font, desktop.music_seed, spacing=5)
    desktop.scan_controls = Column(desktop.document, desktop.page,
        Button('Refresh imported scans', desktop.refresh_documents, icon='FILE_REFRESH'),
        Label('Import scans in Bar Review to use them here.'), spacing=5, visible=False)
    desktop.source_panel = ScrollView(Column(
        Panel('Curriculum stages', desktop.stage_choice, desktop.stage_info),
        Panel('Source', desktop.synthetic_controls, desktop.scan_controls),
        Panel('Provenance', Label('Proposed stages; exploration only.'),
              Label('Source scans and labels stay unchanged.'),
              Label('Previews have no dataset split.')), spacing=12), fill=True, weight=0.24)

    desktop.preset = Dropdown('Starter', list(recipes.PRESETS), 'light-copy')
    desktop.level_choice=Dropdown('Level',[item['name'] for item in desktop.levels],'Mild',on_change=desktop.select_level)
    desktop.level_name=TextField('Name','Mild',on_change=desktop.rename_level)
    desktop.level_buttons=[Button('Add',desktop.add_level),Button('Duplicate',desktop.duplicate_level),Button('Remove',desktop.remove_level)]
    desktop.effect_cards = Column(spacing=8)
    desktop.add_button = Button('Add Effect', desktop.show_add_effect_menu, icon='ADD',
        description='Choose a category, or type to search all effects')
    desktop.recipe_panel = ScrollView(Column(
        Panel('Degradation levels',desktop.level_choice,desktop.level_name,Row(*desktop.level_buttons,spacing=4),
              Row(Button('Move left',lambda:desktop.move_level(-1)),Button('Move right',lambda:desktop.move_level(1)),spacing=4)),
        Panel('Scan recipe', Row(desktop.augmentation_seed,desktop.resample_button,spacing=4), desktop.preset,
              Row(Button('Load starter', desktop.load_preset), Button('Clear', desktop.clear_recipe)),
              desktop.add_button),
        Label('Applied top to bottom · up to 12 steps'), desktop.effect_cards,
        spacing=10), fill=True, weight=0.29)

    desktop.resolution = EnumRow('', ['Native', 'Model 1024'], 'Native',
                              on_change=lambda _: desktop.update_images())
    desktop.view_centers = [(.5,.5), (.5,.5)]
    desktop.zoom = Dropdown('Zoom', ['Fit page', '25%', '50%', '75%', '100%', '150%', '200%', '400%'], 'Fit page',
                         on_change=lambda _: desktop.update_images())
    desktop.link_views = Checkbox('Link views', True)
    desktop.page_images = [PageImage(lambda x,y,i=i: desktop.pan_view(i,x,y), desktop.zoom_step) for i in range(2)]
    desktop.image_controls = Column(
        desktop.resolution,
        Row(Button('−', lambda: desktop.zoom_step(-1), weight=.15), desktop.zoom,
            Button('+', lambda: desktop.zoom_step(1), weight=.15),
            Button('Fit', lambda: desktop.zoom.set_value('Fit page'), weight=.3), spacing=4),
        desktop.link_views, spacing=4)
    desktop.reference_controls = Column(desktop.image_controls)
    desktop.compare_controls = Column(visible=False)
    desktop.controls_parent = desktop.reference_controls
    desktop.image_split = ResizableRow(
        Column(Label('SOURCE / REFERENCE', bold=True), desktop.reference_controls,
            desktop.page_images[0], Label('Scroll / drag to pan · Ctrl+scroll to zoom'), fill=True, spacing=6),
        Column(Label('AUGMENTED', bold=True), desktop.page_images[1], fill=True, spacing=6),
        minimums=[120,120], fill=True)
    desktop.kern_text = SourceText()
    desktop.kern_info = Label('Source of the displayed reference · read-only')
    desktop.kern_preview_id = None
    desktop.kern_panel = Column(
        Row(Label('**kern / HUMDRUM', bold=True), Button('Top', desktop.kern_text.top, weight=.2)),
        desktop.kern_info, desktop.kern_text,
        Label('Scroll for lines · Shift+scroll sideways'), fill=True, spacing=6)
    desktop.curriculum_split = ResizableRow(desktop.image_split, desktop.kern_panel,
        minimums=[180,240], fill=True)
    desktop.image_region=Column(desktop.curriculum_split,fill=True)
    desktop.compare_split=None
    desktop.compare_images=[]
    desktop.compare_headers=[]
    desktop.comparison = Column(desktop.compare_controls, desktop.image_region,
        fill=True, spacing=8)
    desktop.manifest_body = Column()
    desktop.manifest_view = ScrollView(desktop.manifest_body, fill=True, visible=False)
    desktop.viewer = Column(desktop.preview_info, desktop.comparison, desktop.manifest_view,
                         fill=True, spacing=10, weight=.60)
    desktop.main_split = ResizableRow(desktop.source_panel, desktop.viewer, desktop.recipe_panel,
                                  minimums=[180,320,220], fill=True)
    desktop.generate_button = Button('Generate preview', desktop.generate, icon='RENDER_STILL')
    desktop.generate_all_button=Button('Generate all levels',desktop.generate_all,icon='RENDER_STILL',visible=False)
    desktop.export_button = Button('Export preview ZIP', desktop.export_dialog, icon='EXPORT', enabled=False)
    desktop.workspaces = EnumRow('', WORKSPACES, 'Curriculum', on_change=desktop.set_workspace)
    desktop.theme_choice=Dropdown('', ['Dark', 'Light'], bui.theme_name().title(), weight=.14,
                              on_change=lambda value: bui.set_theme(value.lower()))
    desktop.menu_bar = file_menu(desktop)
    desktop.app = App('MuSViT · Curriculum Lab', (1520, 960),
        Row(Label('MuSViT', icon='SEQ_LUMA_WAVEFORM', bold=True, weight=0),
            desktop.workspaces,
            desktop.theme_choice, spacing=18),
        Separator(.25, line=True),
        Row(desktop.generate_button,desktop.generate_all_button,desktop.export_button,
            Button('Save project', desktop.save_project, icon='FILE_TICK'),
            Button('Open project', desktop.open_project_dialog, icon='FILE_FOLDER'), spacing=8),
        desktop.main_split,
        Separator(.25, line=True), Row(desktop.status, desktop.progress_bar, spacing=12),
        padding=12, spacing=8, header=desktop.menu_bar)
    # BUI's Cocoa host maps both Command and Control to its CTRL modifier.
    desktop.app.bind('ctrl+enter', desktop.generate)
    desktop.app.bind('ctrl+s', desktop.save_project)
    desktop.app.bind('ctrl+shift+s', desktop.save_project_dialog)
    desktop.app.bind('ctrl+o', desktop.open_project_dialog)
    desktop.app.bind('ctrl+shift+e', desktop.export_dialog)
    desktop.app.bind('left', lambda: desktop.current_viewport().pan(80, 0))
    desktop.app.bind('right', lambda: desktop.current_viewport().pan(-80, 0))
    desktop.app.bind('up', lambda: desktop.current_viewport().pan(0, 80))
    desktop.app.bind('down', lambda: desktop.current_viewport().pan(0, -80))
