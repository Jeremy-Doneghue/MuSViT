"""Collection reads and safe file writes, independent of BUI.

Exports are exclusive-create; editable recipes/projects retain atomic backups.
Project bundle validation and asset restoration live in lab_project.py.
"""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid


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
