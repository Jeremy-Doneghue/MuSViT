"""Stage management for the reference-focused Curriculum workspace."""
from copy import deepcopy
from typing import TYPE_CHECKING
import uuid

from blenderui.components import Button, Dropdown, Label, Row, TextField

import curriculum
from curriculum_plan import FIELDS, MAX_STAGES, validate_stages

if TYPE_CHECKING:
    from desktop import CurriculumDesktop


class StageEditor:
    def __init__(self, desktop: 'CurriculumDesktop'):
        self.desktop = desktop

    def active(self):
        return next(stage for stage in self.desktop.stages if stage['id'] == self.desktop.active_stage_id)

    def select(self, title):
        desktop = self.desktop
        stage = next(item for item in desktop.stages if item['title'] == title)
        desktop.active_stage_id = stage['id']
        desktop.stage = stage['template']
        desktop.clear(desktop.stage_info)
        index = desktop.stages.index(stage)
        desktop.stage_fields = {
            key: TextField(label, stage[key], on_change=lambda value, key=key: self.edit(key, value))
            for key, (label, _) in FIELDS.items()
        }
        desktop.stage_template = Dropdown('Source type', [item['title'] for item in curriculum.STAGES],
            next(item['title'] for item in curriculum.STAGES if item['id'] == stage['template']), on_change=self.change_template)
        desktop.stage_info.add(
            Row(Button('Add', self.add, enabled=len(desktop.stages)<MAX_STAGES),
                Button('Duplicate', self.duplicate, enabled=len(desktop.stages)<MAX_STAGES),
                Button('Remove', self.remove, enabled=len(desktop.stages)>1), spacing=4),
            Row(Button('Move up', lambda: self.move(-1), enabled=index>0),
                Button('Move down', lambda: self.move(1), enabled=index<len(desktop.stages)-1), spacing=4),
            desktop.stage_template, *desktop.stage_fields.values(),
            Button('Reset stage details', self.reset),
            Label('Mix notes describe the plan; they do not schedule training.'))
        desktop.synthetic_controls.visible = desktop.stage != '4'
        desktop.scan_controls.visible = desktop.stage == '4'
        previous = desktop.example.value
        desktop.example.items = [curriculum.EXAMPLES[key] for key in stage['examples']]
        if desktop.example.items:
            desktop.example.set_value(previous if previous in desktop.example.items else desktop.example.items[0], notify=False)
        desktop.dirty()

    def refresh(self, stage):
        desktop = self.desktop
        desktop.stage_choice.items = [item['title'] for item in desktop.stages]
        desktop.stage_choice.set_value(stage['title'], notify=False)
        self.select(stage['title'])

    def unique_name(self, base, exclude=None):
        names = {stage['title'] for stage in self.desktop.stages if stage['id'] != exclude}
        name, number = base[:70], 2
        while name in names:
            name = f'{base[:70]} {number}'
            number += 1
        return name

    def edit(self, key, value):
        desktop = self.desktop
        proposed = deepcopy(desktop.stages)
        next(stage for stage in proposed if stage['id'] == desktop.active_stage_id)[key] = value
        try:
            desktop.stages = validate_stages(proposed)
        except ValueError as error:
            desktop.status.text = str(error)
            return
        if key == 'title':
            desktop.stage_choice.items = [stage['title'] for stage in desktop.stages]
            desktop.stage_choice.set_value(value, notify=False)
        desktop.status.text = 'Stage details changed · Save project to retain the curriculum plan.'

    def change_template(self, title):
        template = next(stage for stage in curriculum.STAGES if stage['title'] == title)
        stage = self.active()
        stage.update(template=template['id'], examples=deepcopy(template['examples']))
        self.refresh(stage)

    def add(self):
        self.insert('New stage')

    def duplicate(self):
        self.insert(self.active()['title'] + ' copy')

    def insert(self, name):
        desktop = self.desktop
        if len(desktop.stages) >= MAX_STAGES:
            return
        stage = deepcopy(self.active())
        stage.update(id=uuid.uuid4().hex, title=self.unique_name(name))
        desktop.stages.insert(desktop.stages.index(self.active())+1, stage)
        self.refresh(stage)

    def remove(self):
        desktop = self.desktop
        if len(desktop.stages) <= 1:
            return
        index = desktop.stages.index(self.active())
        desktop.stages.pop(index)
        self.refresh(desktop.stages[min(index, len(desktop.stages)-1)])

    def move(self, delta):
        desktop = self.desktop
        stage = self.active()
        index = desktop.stages.index(stage)
        target = index+delta
        if 0 <= target < len(desktop.stages):
            desktop.stages[index], desktop.stages[target] = desktop.stages[target], stage
            self.refresh(stage)

    def reset(self):
        stage = self.active()
        template = next(item for item in curriculum.STAGES if item['id'] == stage['template'])
        for key in FIELDS:
            stage[key] = deepcopy(template[key])
        stage['title'] = self.unique_name(stage['title'], exclude=stage['id'])
        self.refresh(stage)
