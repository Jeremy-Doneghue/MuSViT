"""Finite one-note pitch diagnostic, with explicit absolute-pitch holdouts."""

import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops

from experiments.full_page_omr.datasets.clean_page_data import check_disjoint, digest
from experiments.full_page_omr.datasets.pilot_data import export_pilot, sha256
from experiments.full_page_omr.representation.codec_fixtures import add, note, score, xml
from experiments.full_page_omr.representation.score_semantics import inspect_score

RECIPE = 'one-note-pitch-v1'
CAP = 256
PITCHES = tuple(f'{step}{octave}' for octave in (4, 5) for step in 'CDEFGAB')
HELD_OUT = ('E4', 'A4', 'D5', 'G5')
LAYOUTS = tuple((dx, dy) for dy in (0, 32) for dx in (0, 8, 16, 24))
OPTIONS = dict(inputFrom='musicxml', breaks='encoded', pageWidth=2100,
               pageHeight=2100, scale=55, header='none', footer='none',
               justifyVertically=False)


def make_note(pitch):
    if pitch not in PITCHES:
        raise ValueError('pitch outside fixed pilot support')
    root, _, bar = score('', 'Horn')
    for tag in ('work', 'identification', 'credit'):
        root.remove(root.find(tag))
    bar.set('id', 'm1')
    # A complete, explicitly short measure, not an invalid underfilled 4/4 bar.
    bar.set('implicit', 'yes')
    note(bar, pitch[0], int(pitch[1]))
    add(add(bar, 'barline', location='right'), 'bar-style', 'light-heavy')
    return xml(root)


def export(output):
    output = Path(output)
    manifest = export_pilot(output, scores=[(p, make_note(p)) for p in PITCHES],
                            render_options=OPTIONS)
    records = []
    for base in manifest['records']:
        pitch = base['name']
        split = 'validation' if pitch in HELD_OUT else 'train'
        source = (output / base['source']).read_text()
        # Absolute pitch deliberately retained. The clean-page transposition-
        # invariant fingerprint would collapse every one-quarter-note source.
        fingerprint = digest(inspect_score(source))
        family = digest([RECIPE, pitch])
        if base['target_length'] > CAP:
            raise ValueError('target exceeds fixed cap')
        tree = ET.parse(output / pitch / 'page.svg')
        if sum('system' in n.get('class', '').split() for n in tree.iter()) != 1:
            raise ValueError('expected exactly one staff system')
        with Image.open(output / base['image']) as original:
            original = original.convert('RGB')
            if original.width != original.height:
                raise ValueError('expected square page; do not distort staff geometry')
            bounds = ImageChops.difference(original, Image.new('RGB', original.size, 'white')).getbbox()
            if bounds is None:
                raise ValueError('empty rendered page')
            for index, (dx, dy) in enumerate(LAYOUTS):
                if bounds[2] + dx > original.width or bounds[3] + dy > original.height:
                    raise ValueError('layout translation would clip notation')
                name = f'{split}_{pitch}_{index:02d}'
                folder = output / name
                folder.mkdir()
                image = Image.new('RGB', original.size, 'white')
                image.paste(original, (dx, dy))
                image.save(folder / 'page.png')
                records.append(dict(base, name=name, split=split, family_id=family,
                                    musical_fingerprint=fingerprint, pitch=pitch,
                                    kind='horn', variant=f'layout_{index:02d}',
                                    translation_pixels=[dx, dy], image=f'{name}/page.png',
                                    image_sha256=sha256(folder / 'page.png'), systems=1))
    check_disjoint(records)
    manifest.update(recipe=RECIPE, records=records, max_tokens=CAP,
                    purpose='finite symbol recognition diagnostic, not composition transfer',
                    split_policy='absolute pitch holdout; all layouts of each source stay together; no test export',
                    fingerprint_policy='absolute-pitch semantic fingerprint; transposition equivalence intentionally not grouped',
                    held_out_pitches=list(HELD_OUT), layouts_pixels=LAYOUTS,
                    family_counts={s: len({r['family_id'] for r in records if r['split'] == s})
                                   for s in ('train', 'validation')},
                    coverage={s: dict(Counter(r['pitch'] for r in records if r['split'] == s))
                              for s in ('train', 'validation')})
    manifest['source_hashes'][Path(__file__).name] = sha256(__file__)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    m = export(args.output)
    print(json.dumps(dict(families=m['family_counts'], coverage=m['coverage']), indent=2))
