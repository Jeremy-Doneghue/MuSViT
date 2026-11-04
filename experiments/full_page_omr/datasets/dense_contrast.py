"""Export a controlled one-note contrast from one existing dense training page."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageChops

from experiments.full_page_omr.datasets.pilot_data import export_pilot, sha256
from experiments.full_page_omr.representation.score_codec import VOCABULARY, encode


def export_contrast(dataset, output, transfer_probes=False):
    dataset, output = Path(dataset), Path(output)
    manifest = json.loads((dataset/'manifest.json').read_text())
    record = next(r for r in manifest['records'] if r['name']=='train_000_horn')
    if record['split'] != 'train' or sha256(dataset/record['source']) != record['source_sha256']:
        raise ValueError('unexpected parent source/split')
    source = (dataset/record['source']).read_text()
    root = ET.fromstring(source)
    note = root.findall('part/measure')[0].findall('note')[1]
    if note.findtext('pitch/step') != 'C' or note.findtext('pitch/octave') != '5' or note.find('notations') is not None:
        raise ValueError('contrast expects the unadorned second note, C5, in measure 1')
    note.find('pitch/step').text = 'D'
    changed = ET.tostring(root,encoding='unicode')
    left, right = encode(source), encode(changed)
    positions = [i for i,(a,b) in enumerate(zip(left,right)) if a != b]
    if len(left) != len(right) or len(positions) != 1:
        raise ValueError('contrast must change exactly one target token')
    scores = [('horn_base',source),('horn_one_note',changed)]
    if transfer_probes:
        for name, index, expected, replacement in [('horn_unseen_pitch',1,'C','E'),
                                                   ('horn_unseen_position',2,'A','B')]:
            probe = ET.fromstring(source)
            pitch = probe.findall('part/measure')[0].findall('note')[index].find('pitch/step')
            if pitch.text != expected:
                raise ValueError('unexpected probe note')
            pitch.text = replacement
            xml = ET.tostring(probe,encoding='unicode')
            tokens = encode(xml)
            if len(tokens) != len(left) or sum(a!=b for a,b in zip(left,tokens)) != 1:
                raise ValueError('each transfer probe must differ by one target token')
            scores.append((name,xml))
    exported = export_pilot(output,scores=scores,
                            render_options=manifest['render_options'])
    with Image.open(output/'horn_base/page.png') as a, Image.open(output/'horn_one_note/page.png') as b:
        a,b = a.convert('RGB'),b.convert('RGB')
        if a.size != b.size:
            raise ValueError('contrast changed page dimensions')
        difference = ImageChops.difference(a,b)
        bbox = difference.getbbox()
        changed_pixels = int(np.any(np.asarray(difference)!=0,axis=2).sum())
        with Image.open(dataset/record['image']) as original:
            base_equal = original.size==a.size and ImageChops.difference(original.convert('RGB'),a).getbbox() is None
    if not base_equal or bbox is None:
        raise ValueError('base must match parent pixels and variant must visibly differ')
    for item in exported['records']:
        item.update(kind='horn',family_id=record['family_id'],parent_composition_id=record['composition_id'])
    exported['contrast'] = dict(parent_manifest_sha256=sha256(dataset/'manifest.json'),
                                exporter_sha256=sha256(__file__), parent_name=record['name'],
                                change='measure 1, second note: written C5 to D5; all other score content retained',
                                target_difference_positions=positions,
                                target_values=[VOCABULARY[left[positions[0]]],VOCABULARY[right[positions[0]]]],
                                raster_difference_bbox=bbox, changed_pixels=changed_pixels,
                                base_pixels_equal_parent=base_equal)
    if transfer_probes:
        probes = {}
        for name,xml in scores[2:]:
            with Image.open(output/'horn_base/page.png') as a, Image.open(output/name/'page.png') as b:
                diff = ImageChops.difference(a.convert('RGB'),b.convert('RGB'))
                probes[name] = dict(raster_difference_bbox=diff.getbbox(),
                                    changed_pixels=int(np.any(np.asarray(diff)!=0,axis=2).sum()),
                                    target_difference_positions=[i for i,(x,y) in enumerate(zip(left,encode(xml))) if x!=y])
        exported['contrast']['untrained_transfer_probes'] = probes
    (output/'manifest.json').write_text(json.dumps(exported,indent=2))
    print(json.dumps(exported['contrast'],indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--transfer-probes',action='store_true')
    args=parser.parse_args()
    export_contrast(args.dataset,args.output,args.transfer_probes)
