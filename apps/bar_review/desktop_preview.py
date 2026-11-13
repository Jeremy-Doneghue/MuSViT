"""Submit preview jobs and apply queued progress/results on the UI thread.

The coordinator owns worker/executor lifetime and session state. Only the batch
runner executes on the executor thread; it uses submission snapshots and posts
plain progress/results. All BUI mutations happen in submit/poll callbacks.
"""
from typing import TYPE_CHECKING

from copy import deepcopy
from queue import Empty
import time

if TYPE_CHECKING:
    from desktop import CurriculumDesktop



class PreviewJobs:
    def __init__(self, desktop: "CurriculumDesktop"):
        self.desktop = desktop

    def generate(self):
        desktop = self.desktop
        if desktop.future is not None:
            return
        try:
            request = desktop.payload()
            desktop.stash_active()
            desktop.pending_level_id=desktop.active_level_id
            desktop.pending_batch=False
            desktop.pending_revision = desktop.revision
            desktop.started_at = time.perf_counter()
            while not desktop.progress_events.empty():
                desktop.progress_events.get_nowait()
            desktop.progress_state = dict(label='Submitting preview job', fraction=.02)
            desktop.progress_bar.visible = True
            desktop.progress_bar.set_value(.02)
            desktop.progress_bar.text = 'Submitting preview job · 0.0s'
            desktop.generate_button.enabled = False
            desktop.generate_all_button.enabled = False
            desktop.resample_button.enabled = False
            desktop.status.text = 'Rendering preview…'
            desktop.future = desktop.executor.submit(desktop.worker.preview, desktop.data,
                deepcopy(request), deepcopy(desktop.documents), progress=desktop.progress_events.put,
                source_preview=desktop.source_previews.get(desktop.source_key(request)))
            if desktop.app.window:
                desktop.app.window.after(80, desktop.poll)
        except Exception as error:
            desktop.status.text = f'Preview failed: {error}'
            desktop.generate_button.enabled = True
            desktop.generate_all_button.enabled = True
            desktop.resample_button.enabled = True
            desktop.progress_bar.text = 'Preview failed'

    def generate_all(self):
        desktop = self.desktop
        if desktop.future is not None:
            return
        try:
            source={key:value for key,value in desktop.payload().items() if key!='settings'}
            desktop.stash_active()
            jobs=[dict(level_id=item['id'],name=item['name'],payload={**source,'settings':deepcopy(item['settings'])})
                  for item in desktop.levels]
            desktop.pending_batch=True
            desktop.pending_revision=desktop.revision
            desktop.started_at=time.perf_counter()
            while not desktop.progress_events.empty():
                desktop.progress_events.get_nowait()
            desktop.progress_state=dict(label='Generating degradation levels',fraction=.02)
            desktop.progress_bar.visible=True
            desktop.generate_button.enabled=desktop.generate_all_button.enabled=desktop.resample_button.enabled=False
            desktop.status.text='Generating all levels from the selected source…'
            desktop.future=desktop.executor.submit(desktop.generate_level_batch,jobs,deepcopy(desktop.documents),dict(desktop.source_previews))
            if desktop.app.window:
                desktop.app.window.after(80,desktop.poll)
        except Exception as error:
            desktop.generate_button.enabled=desktop.generate_all_button.enabled=desktop.resample_button.enabled=True
            desktop.status.text=f'Cannot generate levels: {error}'

    def generate_level_batch(self,jobs,documents,sources):
        desktop = self.desktop
        results=[]
        for index,job in enumerate(jobs):
            if desktop.closed:
                break
            def progress(value,index=index,name=job['name']):
                desktop.progress_events.put(dict(label=f'{index+1}/{len(jobs)} {name}: {value["label"]}',
                    fraction=(index+min(.99,value['fraction']))/len(jobs)))
            try:
                key=desktop.source_key(job['payload'])
                manifest=desktop.worker.preview(desktop.data,job['payload'],documents,progress=progress,
                    source_preview=sources.get(key))
                if manifest['source']['kind']=='synthetic':
                    sources[key]=manifest['id']
                results.append(dict(level_id=job['level_id'],manifest=manifest))
            except Exception as error:
                results.append(dict(level_id=job['level_id'],error=str(error)))
        return results

    def poll(self):
        """Only the window thread touches BUI nodes; worker returns plain data."""
        desktop = self.desktop
        if desktop.closed or desktop.future is None:
            return
        try:
            while True:
                desktop.progress_state = desktop.progress_events.get_nowait()
        except Empty:
            pass
        elapsed = time.perf_counter()-desktop.started_at
        desktop.progress_bar.set_value(desktop.progress_state['fraction'])
        desktop.progress_bar.text = f"{desktop.progress_state['label']} · {elapsed:.1f}s"
        if not desktop.future.done():
            if desktop.app.window:
                desktop.app.window.after(80, desktop.poll)
            return
        future, desktop.future = desktop.future, None
        desktop.generate_button.enabled = True
        desktop.generate_all_button.enabled = True
        desktop.resample_button.enabled = True
        try:
            result=future.result()
            desktop.stash_active()
            errors=[]
            if desktop.pending_batch:
                for entry in result:
                    if 'manifest' in entry:
                        desktop.accept_preview(entry['manifest'],entry['level_id'])
                    else:
                        errors.append(entry['error'])
            else:
                desktop.accept_preview(result,desktop.pending_level_id)
            desktop.export_button.enabled = desktop.latest is not None
            desktop.preview_info.text = ((f"{desktop.active_level()['name']} · preview {desktop.latest['id'][:8]} · "
                f"{desktop.latest['source_dimensions']} → {desktop.latest['augmented_dimensions']} · "
                f"{len(desktop.latest['effects'])} active effects") if desktop.latest else 'No preview for the selected level')
            desktop.update_images()
            desktop.update_manifest()
            elapsed = time.perf_counter()-desktop.started_at
            reused = ' · reused source engraving' if desktop.latest and desktop.latest.get('source_reused') else ''
            desktop.progress_bar.set_value(1)
            desktop.progress_bar.text = f'{"Levels" if desktop.pending_batch else "Preview"} ready in {elapsed:.2f}s{reused}'
            desktop.status.text = ('Preview ready · exploration only · export saves this exact preview.'
                if desktop.pending_revision == desktop.revision else
                'Preview ready for earlier settings · generate again to apply current edits.')
            if errors:
                desktop.status.text=f'{len(errors)} level(s) failed: {errors[0][:220]}'
        except Exception as error:
            desktop.progress_bar.text = f'Preview failed after {elapsed:.1f}s'
            desktop.status.text = f'Preview failed: {str(error)[:350]}'
            print(f'Preview failed: {error}', flush=True)

    def poll_warmup(self):
        desktop = self.desktop
        if desktop.closed or desktop.warmup_future is None:
            return
        # A queued preview owns progress/status as soon as Generate is pressed.
        if desktop.future is None and desktop.latest is None:
            try:
                while True:
                    desktop.progress_state = desktop.progress_events.get_nowait()
            except Empty:
                pass
            desktop.progress_bar.set_value(desktop.progress_state['fraction'])
            elapsed = time.perf_counter()-desktop.warmup_started_at
            desktop.progress_bar.text = f"{desktop.progress_state['label']} · {elapsed:.1f}s"
        if not desktop.warmup_future.done():
            desktop.app.window.after(80, desktop.poll_warmup)
            return
        warmup, desktop.warmup_future = desktop.warmup_future, None
        try:
            warmup.result()
            if desktop.future is None and desktop.latest is None:
                desktop.progress_bar.set_value(1)
                desktop.progress_bar.text = 'Preview worker ready'
        except Exception as error:
            if desktop.future is None:
                desktop.progress_bar.text = 'Worker warmup failed; Generate will retry'
                desktop.status.text = str(error)[:350]
