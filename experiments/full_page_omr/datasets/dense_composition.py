"""Five training pages and seven untrained compositions of four local note edits."""
import argparse
from itertools import combinations
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

from experiments.full_page_omr.datasets.pilot_data import export_pilot, sha256
from experiments.full_page_omr.representation.score_codec import encode


def export(dataset,output):
    dataset,output = Path(dataset),Path(output)
    parent = json.loads((dataset/'manifest.json').read_text())
    record = next(r for r in parent['records'] if r['name']=='train_000_horn')
    if record['split']!='train' or sha256(dataset/record['source'])!=record['source_sha256']:
        raise ValueError('parent identity mismatch')
    source=(dataset/record['source']).read_text()
    base_tokens=encode(source)
    # Zero-based measure/note indices; one unadorned pitch in each system.
    edits=[(0,1,'C','D'),(4,1,'D','E'),(8,1,'F','E'),(12,1,'F','E')]
    variants=[('horn_base',())]+[(f'horn_edit_{i+1}',(i,)) for i in range(4)]
    variants += [(f'horn_pair_{i+1}_{j+1}',(i,j)) for i,j in combinations(range(4),2)]
    variants += [('horn_all_four',tuple(range(4)))]
    scores,metadata=[],{}
    for name,active in variants:
        root=ET.fromstring(source)
        for i in active:
            measure,note,expected,replacement=edits[i]
            target=root.findall('part/measure')[measure].findall('note')[note]
            if target.findtext('pitch/step')!=expected or target.find('notations') is not None:
                raise ValueError('unexpected edit location')
            target.find('pitch/step').text=replacement
        xml=source if not active else ET.tostring(root,encoding='unicode')
        tokens=encode(xml)
        changed=[i for i,(a,b) in enumerate(zip(base_tokens,tokens)) if a!=b]
        if len(tokens)!=len(base_tokens) or len(changed)!=len(active):
            raise ValueError('each edit must change exactly one pitch token')
        scores.append((name,xml))
        metadata[name]=dict(active_edits=list(active),target_difference_positions=changed,
                            diagnostic_role='train' if len(active)<=1 else 'untrained_probe')
    manifest=export_pilot(output,scores=scores,render_options=parent['render_options'])
    with Image.open(output/'horn_base/page.png') as image:
        base=np.asarray(image.convert('RGB'))
    with Image.open(dataset/record['image']) as image:
        if not np.array_equal(base,np.asarray(image.convert('RGB'))):
            raise ValueError('base pixels changed')
    masks={}
    for name,active in variants:
        with Image.open(output/name/'page.png') as image:
            pixels=np.asarray(image.convert('RGB'))
        if pixels.shape!=base.shape:
            raise ValueError('page dimensions changed')
        mask=np.any(pixels!=base,axis=2)
        masks[name]=mask
        metadata[name]['changed_pixels']=int(mask.sum())
        if len(active)>1:
            expected=np.logical_or.reduce([masks[f'horn_edit_{i+1}'] for i in active])
            if not np.array_equal(mask,expected):
                raise ValueError('combined raster changes are not the union of individual edits')
            metadata[name]['raster_mask_equals_union_of_single_edits']=True
    for r in manifest['records']:
        r.update(kind='horn',family_id=record['family_id'],**metadata[r['name']])
    manifest['composition_probe']=dict(parent_manifest_sha256=sha256(dataset/'manifest.json'),
        exporter_sha256=sha256(__file__),edits=edits,training_indices=list(range(5)),
        untrained_indices=list(range(5,12)),
        limitation='Same training composition; tests combinations of learned edits, not source-disjoint reading.')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(dict(records=metadata,recipe=manifest['composition_probe']),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',required=True)
    parser.add_argument('--output',required=True)
    export(**vars(parser.parse_args()))
