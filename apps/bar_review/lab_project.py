"""Portable Curriculum Lab projects: settings and exact immutable preview assets."""
from copy import deepcopy
import hashlib
import io
import json
import math
from pathlib import Path
import re
import uuid
import zipfile

import curriculum
import recipes
from curriculum_plan import default_stages, validate_stages

KIND = 'musvit-curriculum-project'
VERSION = 2
MAX_LEVELS = 8
MAX_BYTES = 512 * 1024 * 1024
IMAGE_FILES = {'source.png','augmented.png','source-1024.png','augmented-1024.png'}
FILES = IMAGE_FILES | {'source.krn','source.svg','source.mei','source.musicxml'}


def level(name, recipe, seed=42):
    return dict(id=uuid.uuid4().hex,name=name,settings=dict(seed=seed,recipe=deepcopy(recipe)),
                preview_id=None,preset='clean',collapsed={})


def validate(value):
    if not isinstance(value,dict) or value.get('kind')!=KIND or value.get('schema_version') not in (1, VERSION):
        raise ValueError('Expected a version 1 or 2 Curriculum Lab project')
    if value['schema_version'] == VERSION and not {'curriculum_stages', 'active_curriculum_stage'} <= value.keys():
        raise ValueError('Version 2 projects require a curriculum plan and selected stage')
    result=deepcopy(value)
    result['curriculum_stages'] = validate_stages(result.get('curriculum_stages', default_stages()))
    source=result.get('source',{})
    if not isinstance(source,dict) or str(source.get('stage')) not in {s['id'] for s in curriculum.STAGES}:
        raise ValueError('Unknown project curriculum stage')
    source['stage']=str(source['stage'])
    result.setdefault('active_curriculum_stage', source['stage'])
    active_stage = next((stage for stage in result['curriculum_stages'] if stage['id'] == result['active_curriculum_stage']), None)
    if active_stage is None or active_stage['template'] != source['stage']:
        raise ValueError('Invalid selected curriculum stage or source type')
    if source.get('font') not in ('Leipzig','Bravura','Petaluma'):
        raise ValueError('Unknown project engraving font')
    source['music_seed']=curriculum.integer(source.get('music_seed'),0,2**31-1,'Music seed')
    if source['stage']!='4' and source.get('example') not in curriculum.STAGES[int(source['stage'])]['examples']:
        raise ValueError('Project example does not belong to its stage')
    if source.get('document_id') is not None and (not isinstance(source['document_id'],str) or
            not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',source['document_id'])):
        raise ValueError('Invalid source document ID')
    if source.get('page') is not None:
        source['page']=curriculum.integer(source['page'],1,100000,'Scan page')
    levels=result.get('levels')
    if not isinstance(levels,list) or not 1<=len(levels)<=MAX_LEVELS:
        raise ValueError(f'A project needs 1–{MAX_LEVELS} degradation levels')
    identities,names=set(),set()
    for item in levels:
        if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not re.fullmatch(r'[a-f0-9]{32}',item['id']):
            raise ValueError('Invalid degradation level ID')
        name=item.get('name')
        if not isinstance(name,str) or not name.strip() or len(name)>80 or name in names or item['id'] in identities:
            raise ValueError('Level names and IDs must be nonempty and unique')
        identities.add(item['id']);names.add(name)
        item['settings']=curriculum.settings(item.get('settings',{}))
        if 'recipe' not in item['settings']:
            raise ValueError('Project levels require ordered recipes')
        item['preset']=item.get('preset','clean')
        if item['preset'] not in recipes.PRESETS:
            raise ValueError('Unknown starting recipe')
        collapsed=item.get('collapsed',{})
        if not isinstance(collapsed,dict) or any(not isinstance(v,bool) for v in collapsed.values()):
            raise ValueError('Invalid panel state')
    if result.get('active_level') not in identities:
        raise ValueError('Unknown selected degradation level')
    previews=result.get('previews',{})
    if not isinstance(previews,dict) or len(previews)>MAX_LEVELS:
        raise ValueError('Invalid project previews')
    for identity,manifest in previews.items():
        if not re.fullmatch(r'[a-f0-9]{32}',identity) or not isinstance(manifest,dict) or manifest.get('id')!=identity:
            raise ValueError('Invalid project preview ID')
        files=manifest.get('files',{})
        if not isinstance(files,dict) or not IMAGE_FILES<=set(files) or set(files)-FILES:
            raise ValueError('Invalid project preview files')
        if any(not re.fullmatch(r'[a-f0-9]{64}',str(digest)) for digest in files.values()):
            raise ValueError('Invalid preview checksum')
        if not isinstance(manifest.get('request'),dict) or not isinstance(manifest.get('effects'),list):
            raise ValueError('Invalid preview settings')
        if any(not isinstance(effect,dict) or ('sampled_parameters' in effect and
                (not isinstance(effect['sampled_parameters'],dict) or not isinstance(effect.get('id'),str)))
               for effect in manifest['effects']):
            raise ValueError('Invalid preview effect records')
        for key in ('source_dimensions','augmented_dimensions'):
            dimensions=manifest.get(key)
            if not isinstance(dimensions,list) or len(dimensions)!=2 or any(
                    isinstance(v,bool) or not isinstance(v,int) or v<=0 for v in dimensions) or dimensions[0]*dimensions[1]>16_000_000:
                raise ValueError('Invalid preview image dimensions')
        if not isinstance(manifest.get('source'),dict) or manifest['source'].get('kind') not in ('synthetic','real-scan'):
            raise ValueError('Invalid preview provenance')
    for item in levels:
        if item.get('preview_id') is not None and item['preview_id'] not in previews:
            raise ValueError('Missing level preview')
    view=result.get('view',{})
    if not isinstance(view,dict):
        raise ValueError('Invalid project view settings')
    if view.get('workspace') not in ('Curriculum','Scan Recipe','Compare','Manifest') or view.get('resolution') not in ('Native','Model 1024'):
        raise ValueError('Unknown saved workspace or resolution')
    if view.get('zoom') not in ('Fit page','25%','50%','75%','100%','150%','200%','400%') or view.get('theme') not in ('dark','light'):
        raise ValueError('Unknown zoom or theme')
    if not isinstance(view.get('link_views'),bool):
        raise ValueError('Invalid linked view setting')
    for key,count in [('sidebar_weights',3),('image_weights',2)]:
        weights=view.get(key)
        if not isinstance(weights,list) or len(weights)!=count or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in weights):
            raise ValueError('Invalid region widths')
    centers=view.get('centers')
    if not isinstance(centers,list) or len(centers)!=2:
        raise ValueError('Invalid image centers')
    compare_centers=view.get('compare_centers',{})
    if not isinstance(compare_centers,dict):
        raise ValueError('Invalid comparison centers')
    for pair in centers+list(compare_centers.values()):
        if not isinstance(pair,(list,tuple)) or len(pair)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in pair):
            raise ValueError('Invalid image center')
    weights=view.get('compare_weights',{})
    if not isinstance(weights,dict) or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<=0 for v in weights.values()):
        raise ValueError('Invalid comparison widths')
    panels=view.get('panels',{})
    if not isinstance(panels,dict) or any(not isinstance(value,bool) for value in panels.values()):
        raise ValueError('Invalid sidebar panel state')
    return result


def bundle(document,data,documents):
    document=validate(document)
    assets={}
    for identity,manifest in document['previews'].items():
        for name,digest in manifest['files'].items():
            content=curriculum.artifact(data,identity,name).read_bytes()
            if hashlib.sha256(content).hexdigest()!=digest:
                raise ValueError(f'Preview asset changed: {identity}/{name}')
            assets[f'previews/{identity}/{name}']=content
    source=document['source']
    if source['stage']=='4' and source.get('document_id') and source.get('page'):
        doc=next((d for d in documents if d['id']==source['document_id']),None)
        if doc is None:
            raise ValueError('The selected source scan is unavailable')
        content=(Path(data)/doc['id']/f"page-{source['page']}.png").read_bytes()
        page=next(p for p in doc['pages'] if p['number']==source['page'])
        document['selected_scan']=dict(id=doc['id'],title=doc['title'],sha256=doc['sha256'],
            pages=[dict(number=page['number'],width=page['width'],height=page['height'])],
            image_sha256=hashlib.sha256(content).hexdigest())
        assets['selected-scan.png']=content
    assets['project.json']=json.dumps(document,indent=2).encode()
    if sum(map(len,assets.values()))>MAX_BYTES:
        raise ValueError('Project is too large (512 MiB limit)')
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,content in assets.items():
            archive.writestr(name,content,compress_type=zipfile.ZIP_STORED if name.endswith('.png') else zipfile.ZIP_DEFLATED)
    return buffer.getvalue()


def unbundle(path,data):
    """Validate all bytes before restoring assets; never replace existing previews."""
    with zipfile.ZipFile(path) as archive:
        info=archive.infolist()
        if len(info)>100 or sum(item.file_size for item in info)>MAX_BYTES or len({item.filename for item in info})!=len(info):
            raise ValueError('Invalid or oversized project archive')
        if archive.getinfo('project.json').file_size>8*1024*1024:
            raise ValueError('Project metadata is too large')
        document=validate(json.loads(archive.read('project.json')))
        expected={'project.json'}
        assets={}
        for identity,manifest in document['previews'].items():
            for name,digest in manifest['files'].items():
                entry=f'previews/{identity}/{name}';expected.add(entry)
                content=archive.read(entry)
                if hashlib.sha256(content).hexdigest()!=digest:
                    raise ValueError(f'Corrupt project preview: {entry}')
                assets[entry]=content
        scan=document.get('selected_scan')
        if scan:
            expected.add('selected-scan.png')
            content=archive.read('selected-scan.png')
            if hashlib.sha256(content).hexdigest()!=scan.get('image_sha256'):
                raise ValueError('Corrupt source scan')
            # Source selection has already validated the only on-disk identifiers.
            if scan.get('id')!=document['source'].get('document_id') or not isinstance(scan.get('title'),str):
                raise ValueError('Invalid embedded source scan')
            if not isinstance(scan.get('pages'),list) or len(scan['pages'])!=1 or scan['pages'][0].get('number')!=document['source']['page']:
                raise ValueError('Invalid embedded scan page')
            scan['pages'][0]['number']=document['source']['page']
            assets['selected-scan.png']=content
        if {item.filename for item in info}!=expected:
            raise ValueError('Unexpected files in project archive')
    from PIL import Image
    for name,content in assets.items():
        if name.endswith('.png'):
            with Image.open(io.BytesIO(content)) as image:
                if image.width*image.height>16_000_000:
                    raise ValueError('Project image is too large')
                image.verify()
    data=Path(data)
    restored={}
    mapping={}
    for identity,manifest in document['previews'].items():
        target=data/'curriculum'/identity
        intact=False
        if target.is_dir():
            try:
                intact=json.loads((target/'manifest.json').read_text())==manifest and all(
                    hashlib.sha256((target/name).read_bytes()).hexdigest()==digest for name,digest in manifest['files'].items())
            except (OSError,ValueError):
                pass
        new_id=identity if not target.exists() or intact else uuid.uuid4().hex
        mapping[identity]=new_id
        copy=deepcopy(manifest);copy['id']=new_id
        if new_id!=identity:
            copy['restored_from_preview_id']=identity
        if not intact:
            folder=data/'curriculum'/new_id
            folder.mkdir(parents=True,exist_ok=False)
            for name in copy['files']:
                (folder/name).write_bytes(assets[f'previews/{identity}/{name}'])
            (folder/'manifest.json').write_text(json.dumps(copy,indent=2))
        restored[new_id]=copy
    document['previews']=restored
    for item in document['levels']:
        if item.get('preview_id'):
            item['preview_id']=mapping[item['preview_id']]
    embedded=None
    if scan:
        content=assets['selected-scan.png'];page=document['source']['page']
        identity=scan['id'];target=data/identity/f'page-{page}.png'
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=scan['image_sha256']:
            identity='projectscan_'+scan['image_sha256'][:24]
            target=data/identity/f'page-{page}.png'
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream:
                stream.write(content)
        elif hashlib.sha256(target.read_bytes()).hexdigest()!=scan['image_sha256']:
            raise ValueError('Embedded source destination conflicts with an existing file')
        embedded={k:v for k,v in scan.items() if k!='image_sha256'}
        embedded['id']=identity
        document['source']['document_id']=identity
    return document,embedded
