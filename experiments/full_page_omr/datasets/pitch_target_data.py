"""All-pitches-taught appearance diagnostic with paired score/pitch targets.

Source labels deliberately repeat across splits. This dataset is NOT accepted
by the composition-disjoint adapters and is not a repertoire benchmark.
"""

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops
import torch

from experiments.full_page_omr.datasets.one_note_data import CAP, OPTIONS, PITCHES, make_note
from experiments.full_page_omr.datasets.pilot_data import export_pilot, sha256
from experiments.full_page_omr.representation.score_codec import VOCABULARY_SHA256, W2I, decode, encode
from experiments.full_page_omr.representation.score_semantics import inspect_score

RECIPE = 'all-notes-paired-targets'
LAYOUTS = {'train': ((0, 0), (24, 0), (0, 32), (24, 32)),
           'validation': ((8, 8), (16, 8), (8, 24), (16, 24))}


def pitch_tokens(pitch):
    if pitch not in PITCHES:
        raise ValueError('pitch outside fixed diagnostic support')
    return [W2I['<bos>'], W2I['V:' + pitch[0]], W2I['V:' + pitch[1]], W2I['<eos>']]


def pitch_from_tokens(tokens):
    for pitch in PITCHES:
        if tokens == pitch_tokens(pitch):
            return pitch
    raise ValueError('expected exactly BOS, natural pitch step, octave 4/5, EOS')


def pitch_to_musicxml(tokens):
    """Fixed quarter duration/clef/meter/part context is supplied, not inferred."""
    return make_note(pitch_from_tokens(tokens))


PLACEMENT_LAYOUTS = {'train': tuple((x, y) for x in (0, 8, 16, 24) for y in (0, 8, 24, 32)),
                     'validation': ((4, 4), (20, 4), (4, 28), (20, 28))}
PLACEMENT_RECIPE = 'all-notes-placement-comparison'


def check_records(records, layouts=None):
    layouts = LAYOUTS if layouts is None else layouts
    if len({r['name'] for r in records}) != len(records):
        raise ValueError('duplicate record name')
    images, positions = {}, {}
    for r in records:
        if r['split'] not in layouts or r['pitch'] not in PITCHES:
            raise ValueError('unexpected split/pitch')
        position = tuple(r['translation_pixels'])
        if position not in layouts[r['split']]:
            raise ValueError('placement outside fixed split recipe')
        if r['image_sha256'] in images:
            raise ValueError('duplicate raster')
        images[r['image_sha256']] = r['split']
        key = (r['pitch'], position)
        if key in positions:
            raise ValueError('duplicate pitch/placement')
        positions[key] = r['split']
    for split in layouts:
        counts = Counter(r['pitch'] for r in records if r['split'] == split)
        if counts != Counter({p: len(layouts[split]) for p in PITCHES}):
            raise ValueError('expected balanced complete pitch support')


def export(output, placement_comparison=False):
    layouts = PLACEMENT_LAYOUTS if placement_comparison else LAYOUTS
    output = Path(output)
    manifest = export_pilot(output, scores=[(p, make_note(p)) for p in PITCHES], render_options=OPTIONS)
    records = []
    for base in manifest['records']:
        pitch = base['name']
        if inspect_score(pitch_to_musicxml(pitch_tokens(pitch))) != inspect_score((output / base['source']).read_text()):
            raise ValueError('compact target does not preserve fixed-task score')
        with Image.open(output / base['image']) as original:
            original = original.convert('RGB')
            if original.size != (1400, 1400):
                raise ValueError('expected square source page at fixed scale')
            bounds = ImageChops.difference(original, Image.new('RGB', original.size, 'white')).getbbox()
            if bounds is None:
                raise ValueError('empty rendered page')
            for split, positions in layouts.items():
                for index, (dx, dy) in enumerate(positions):
                    if bounds[2] + dx > original.width or bounds[3] + dy > original.height:
                        raise ValueError('translation would clip notation')
                    name = f'{split}_{pitch}_{index:02d}'
                    folder = output / name
                    folder.mkdir()
                    image = Image.new('RGB', original.size, 'white')
                    image.paste(original, (dx, dy))
                    image.save(folder / 'page.png')
                    records.append(dict(base, name=name, split=split, pitch=pitch,
                        variant=f'placement_{index}', translation_pixels=[dx, dy],
                        image=f'{name}/page.png', image_sha256=sha256(folder / 'page.png'),
                        compact_tokens=pitch_tokens(pitch)))
    check_records(records, layouts)
    manifest.update(recipe=PLACEMENT_RECIPE if placement_comparison else RECIPE, records=records, max_tokens=CAP,
        purpose='paired target comparison; known pitches, unseen placements; not composition-disjoint',
        split_policy='all 14 pitch sources shared; fixed disjoint raster translations; no test export',
        supplied_context='treble clef, C major, 4/4, one implicit quarter-note measure, voice/staff 1, Horn',
        target_formats={'score': 'musvit-score-v1', 'pitch': 'BOS V:step V:octave EOS'},
        layouts_pixels=layouts, independent_pitch_targets=len(PITCHES))
    manifest['source_hashes'][Path(__file__).name] = sha256(__file__)
    manifest['source_hashes']['one_note_data.py'] = sha256(Path(__file__).with_name('one_note_data.py'))
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


def load(directory):
    """Verify paired labels without relaxing the existing source-disjoint adapter."""
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    if manifest.get('recipe') not in (RECIPE, PLACEMENT_RECIPE) or manifest['vocabulary_sha256'] != VOCABULARY_SHA256:
        raise ValueError('unexpected recipe/vocabulary')
    layouts = PLACEMENT_LAYOUTS if manifest['recipe'] == PLACEMENT_RECIPE else LAYOUTS
    if manifest.get('layouts_pixels') != {k: [list(p) for p in v] for k,v in layouts.items()}:
        raise ValueError('manifest layouts differ from fixed recipe')
    check_records(manifest['records'], layouts)
    samples = {s: [] for s in LAYOUTS}
    for record in manifest['records']:
        for key in ('image', 'source', 'target'):
            if sha256(directory / record[key]) != record[key + '_sha256']:
                raise ValueError('dataset artifact hash mismatch')
        score_target = json.loads((directory / record['target']).read_text())
        source = (directory / record['source']).read_text()
        if score_target['vocabulary_sha256'] != VOCABULARY_SHA256 or score_target['tokens'] != encode(source):
            raise ValueError('score label mismatch')
        if record['compact_tokens'] != pitch_tokens(record['pitch']):
            raise ValueError('compact label mismatch')
        if inspect_score(decode(score_target['tokens'])) != inspect_score(pitch_to_musicxml(record['compact_tokens'])):
            raise ValueError('paired target semantics differ')
        if len(score_target['tokens']) > CAP:
            raise ValueError('target exceeds fixed cap')
        samples[record['split']].append(dict(record=record, score=score_target['tokens'], pitch=record['compact_tokens']))
    return manifest, samples


def image_tensor(directory, record, resolution):
    with Image.open(Path(directory) / record['image']) as image:
        image = image.convert('RGB').resize((resolution, resolution), Image.Resampling.BILINEAR)
        return torch.from_numpy(np.asarray(image, dtype=np.float32) / 255).permute(2, 0, 1).unsqueeze(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    manifest = export(args.output)
    print(json.dumps(dict(records=len(manifest['records']), pitch_targets=len(PITCHES), layouts=LAYOUTS), indent=2))
