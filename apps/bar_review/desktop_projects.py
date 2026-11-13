"""Project/legacy-recipe snapshots, restoration and export actions.

The coordinator owns live session state and UI callbacks; this collaborator
reads or restores that state on the UI thread. Dialog callbacks capture bytes
or preview IDs at open time. Storage and archive formats remain separate.
"""
from typing import TYPE_CHECKING

from copy import deepcopy
import json
from pathlib import Path

import blenderui as bui
from blenderui.components import Panel

import curriculum
import lab_project
import recipes
from desktop_storage import write_new, write_recipe

if TYPE_CHECKING:
    from desktop import CurriculumDesktop



class ProjectActions:
    def __init__(self, desktop: "CurriculumDesktop"):
        self.desktop = desktop

    def export_to(self, path):
        desktop = self.desktop
        if not desktop.latest:
            raise ValueError('Generate a preview first.')
        write_new(path, curriculum.export_preview(desktop.data, desktop.latest['id']))

    def export_dialog(self):
        desktop = self.desktop
        if not desktop.latest:
            desktop.status.text = 'Generate a preview before exporting.'
            return
        try:
            # Bind to the displayed preview at dialog-open time, even if a
            # background job completes while the browser window is open.
            preview_id = desktop.latest['id']
            def exported(path):
                write_new(path, curriculum.export_preview(desktop.data, preview_id))
                desktop.status.text = f'Exported displayed preview to {path}'
            desktop.choose_file('save', exported, title='Export displayed preview',
                initialfile=f"curriculum-{preview_id[:8]}.zip", defaultextension='.zip')
        except Exception as error:
            desktop.status.text = f'Export failed (existing files are preserved): {error}'

    def recipe_document(self):
        desktop = self.desktop
        recipe=recipes.validate(desktop.recipe)
        return dict(schema_version=2 if any(item.get('ranges') for item in recipe) else 1,
                    seed=desktop.augmentation_seed.value, recipe=recipe)

    def project_document(self):
        desktop = self.desktop
        desktop.stash_active()
        previews={item['latest']['id']:deepcopy(item['latest']) for item in desktop.levels if item.get('latest')}
        levels=[dict(id=item['id'],name=item['name'],settings=deepcopy(item['settings']),
                     preset=item.get('preset','clean'),collapsed=deepcopy(item.get('collapsed',{})),
                     preview_id=item['latest']['id'] if item.get('latest') else None) for item in desktop.levels]
        compare_weights={key:pane.weight for key,pane in zip(desktop.compare_ids,desktop.compare_split.panes)}
        document=lab_project.validate(dict(kind=lab_project.KIND,schema_version=lab_project.VERSION,source=desktop.source_settings(),
            curriculum_stages=deepcopy(desktop.stages),
            active_curriculum_stage=desktop.active_stage_id,
            levels=levels,active_level=desktop.active_level_id,previews=previews,
            view=dict(workspace=desktop.workspaces.value,resolution=desktop.resolution.value,zoom=desktop.zoom.value,
                link_views=desktop.link_views.value,centers=[list(pair) for pair in desktop.view_centers],
                compare_centers={key:list(pair) for key,pair in desktop.compare_centers.items()},
                sidebar_weights=[pane.weight for pane in desktop.main_split.panes],
                image_weights=[pane.weight for pane in desktop.image_split.panes],
                compare_weights=compare_weights,theme=bui.theme_name(),
                panels={f'{region}:{panel.title}':panel.collapsed for region,container in
                    [('source',desktop.source_panel),('recipe',desktop.recipe_panel)]
                    for panel in container.children[0].children if isinstance(panel,Panel)})))
        return json.loads(json.dumps(document))

    def write_project(self, path, content):
        """Persist one captured snapshot and remember the path only on success."""
        desktop = self.desktop
        backup = write_recipe(path, content, backup_folder='.project-backups')
        desktop.project_path = Path(path).expanduser().resolve()
        desktop.status.text = f'Saved project to {desktop.project_path}' + (
            ' · previous version backed up' if backup else '')

    def save_project(self):
        """Save in place; untitled projects use the Save As browser."""
        desktop = self.desktop
        if desktop.project_path is None:
            desktop.save_project_dialog()
            return
        try:
            content = lab_project.bundle(desktop.project_document(), desktop.data, desktop.documents)
            self.write_project(desktop.project_path, content)
        except Exception as error:
            desktop.status.text = f'Project save failed: {error}'

    def save_project_dialog(self):
        desktop = self.desktop
        try:
            content=lab_project.bundle(desktop.project_document(),desktop.data,desktop.documents)
            def saved(path):
                self.write_project(path, content)
            desktop.choose_file('save',saved,title='Save Curriculum Lab project',
                initialfile=desktop.project_path.name if desktop.project_path else 'curriculum-lab.musvitlab',
                initialdir=str(desktop.project_path.parent) if desktop.project_path else None,
                defaultextension='.musvitlab',filetypes=[('Curriculum Lab projects','*.musvitlab')])
        except Exception as error:
            desktop.status.text=f'Project save failed: {error}'

    def open_project_dialog(self):
        desktop = self.desktop
        if desktop.future is not None:
            desktop.status.text='Wait for preview generation before opening another project.'
            return
        desktop.choose_file('open',desktop.load_project,title='Open Curriculum Lab project',
            initialdir=str(desktop.project_path.parent) if desktop.project_path else None,
            filetypes=[('Curriculum Lab projects','*.musvitlab'),('Legacy recipes','*.json')])

    def load_project(self,path):
        desktop = self.desktop
        import zipfile
        if desktop.future is not None:
            raise ValueError('Wait for preview generation before opening another project.')
        if not zipfile.is_zipfile(path):
            desktop.load_recipe(path)
            desktop.stash_active()
            desktop.status.text=f'Imported legacy recipe into {desktop.active_level()["name"]}; use Save project to retain the whole lab.'
            return
        document,embedded=lab_project.unbundle(path,desktop.data)
        desktop.restoring=True
        try:
            desktop.stages = document['curriculum_stages']
            desktop.active_stage_id = document['active_curriculum_stage']
            desktop.stage_choice.items = [stage['title'] for stage in desktop.stages]
            desktop.levels=document['levels']
            for item in desktop.levels:
                item['latest']=document['previews'].get(item.get('preview_id'))
                item['displayed_values']={effect['id']:effect['sampled_parameters'] for effect in
                    (item['latest']['effects'] if item['latest'] else []) if 'sampled_parameters' in effect}
            desktop.project_documents=[embedded] if embedded else []
            desktop.refresh_documents()
            source=document['source']
            desktop.font.set_value(source['font'],notify=False)
            desktop.music_seed.set_value(source['music_seed'],notify=False)
            stage=next(item for item in desktop.stages if item['id']==desktop.active_stage_id)
            desktop.stage_choice.set_value(stage['title'],notify=False)
            desktop.select_stage(stage['title'])
            if source.get('example'):
                desktop.example.set_value(curriculum.EXAMPLES[source['example']],notify=False)
            index=next((i for i,doc in enumerate(desktop.documents) if doc['id']==source.get('document_id')),None)
            if index is not None:
                desktop.document.set_value(desktop.document.items[index],notify=False)
                desktop.select_document(desktop.document.value)
                desktop.page.set_value(str(source['page']),notify=False)
            desktop.view_cache.clear()
            desktop.source_previews={desktop.source_key(manifest['request']):manifest['id']
                for manifest in document['previews'].values() if manifest['source']['kind']=='synthetic'}
            desktop.active_level_id=document['active_level']
            desktop.compare_centers={key:tuple(pair) for key,pair in document['view'].get('compare_centers',{}).items()}
            desktop.compare_weights={}
            desktop.rebuild_compare()
            view=document['view']
            desktop.view_centers=[tuple(pair) for pair in view['centers']]
            desktop.resolution.set_value(view['resolution'],notify=False)
            desktop.zoom.set_value(view['zoom'],notify=False)
            desktop.link_views.set_value(view['link_views'],notify=False)
            for row,weights in [(desktop.main_split,view['sidebar_weights']),(desktop.image_split,view['image_weights'])]:
                for pane,weight in zip(row.panes,weights):
                    pane.weight=weight
            for identity,pane in zip(desktop.compare_ids,desktop.compare_split.panes):
                pane.weight=view.get('compare_weights',{}).get(identity,1)
            bui.set_theme(view['theme']);desktop.theme_choice.set_value(view['theme'].title(),notify=False)
            desktop.activate_level(desktop.active_level_id)
            for region,container in [('source',desktop.source_panel),('recipe',desktop.recipe_panel)]:
                for panel in container.children[0].children:
                    if isinstance(panel,Panel):
                        panel.collapsed=view.get('panels',{}).get(f'{region}:{panel.title}',False)
            desktop.workspaces.set_value(view['workspace'],notify=False)
            desktop.set_workspace(view['workspace'])
            desktop.update_images()
            desktop.update_manifest()
            desktop.project_path=Path(path).expanduser().resolve()
            desktop.revision+=1
            desktop.status.text=f'Opened project {desktop.project_path.name} · {len(desktop.levels)} levels · saved previews restored'
        finally:
            desktop.restoring=False

    def save_recipe_dialog(self):
        desktop = self.desktop
        try:
            content = json.dumps(desktop.recipe_document(), indent=2).encode()
            def saved(path):
                backup=write_recipe(path, content)
                desktop.recipe_path=Path(path).expanduser().resolve()
                desktop.status.text = f'Saved recipe to {path}'+(' · previous version backed up' if backup else '')
                desktop.status.description = f'Previous version: {backup}' if backup else str(desktop.recipe_path)
            desktop.choose_file('save', saved, title='Save scan recipe',
                initialfile=desktop.recipe_path.name if desktop.recipe_path else 'scan-recipe.json',
                initialdir=str(desktop.recipe_path.parent) if desktop.recipe_path else None,
                defaultextension='.json')
        except Exception as error:
            desktop.status.text = f'Recipe save failed (existing files are preserved): {error}'

    def load_recipe(self, path):
        desktop = self.desktop
        value = json.loads(Path(path).read_text())
        if not isinstance(value, dict) or value.get('schema_version') not in (1,2) or 'recipe' not in value:
            raise ValueError('Expected a version 1 or 2 desktop recipe with seed and recipe fields.')
        config = curriculum.settings(value)
        desktop.recipe = config['recipe']
        desktop.preview_values.clear()
        desktop.displayed_values.clear()
        desktop.augmentation_seed.set_value(config['seed'], notify=False)
        desktop.render_recipe()
        desktop.dirty()
        desktop.recipe_path=Path(path).expanduser().resolve()
        desktop.status.text=f'Loaded recipe from {desktop.recipe_path}. Generate a preview to apply it.'

    def open_recipe_dialog(self):
        desktop = self.desktop
        try:
            desktop.choose_file('open', desktop.load_recipe, title='Open scan recipe',
                initialdir=str(desktop.recipe_path.parent) if desktop.recipe_path else None,
                filetypes=[('Recipes', '*.json')])
        except Exception as error:
            desktop.status.text = f'Recipe load failed: {error}'
