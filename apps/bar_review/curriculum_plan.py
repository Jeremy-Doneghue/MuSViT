"""Project-local curriculum stages mapped to supported source generators."""
from copy import deepcopy
import re

import curriculum

MAX_STAGES = 32
FIELDS = {'title': ('Name', 80), 'description': ('Description', 2000),
          'focus': ('Learning focus', 500), 'mix': ('Mix notes', 500)}


def default_stages():
    return [{**deepcopy(stage), 'template': stage['id']} for stage in curriculum.STAGES]


def validate_stages(value):
    """Validate editable stages while keeping backend generator IDs stable."""
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_STAGES:
        raise ValueError(f'A curriculum needs 1–{MAX_STAGES} stages')
    result = deepcopy(value)
    names, identities = set(), set()
    templates = {stage['id']: stage for stage in curriculum.STAGES}
    for stage in result:
        if not isinstance(stage, dict) or not isinstance(stage.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', stage['id']):
            raise ValueError('Invalid curriculum stage ID')
        template = stage.setdefault('template', stage['id'])
        if not isinstance(template, str) or template not in templates or stage.get('examples') != templates[template]['examples']:
            raise ValueError('Unknown curriculum source type or unsupported example types')
        for key, (label, limit) in FIELDS.items():
            text = stage.get(key)
            if not isinstance(text, str) or len(text) > limit or (key == 'title' and not text.strip()):
                raise ValueError(f'{label} must be text of at most {limit} characters (stage names cannot be blank)')
        if stage['title'] in names or stage['id'] in identities:
            raise ValueError('Curriculum stage names and IDs must be unique')
        names.add(stage['title']); identities.add(stage['id'])
    return result
