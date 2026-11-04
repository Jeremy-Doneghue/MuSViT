"""Immutable short-staff transfer dataset; no test-set access."""

from experiments.full_page_omr.paths import PACKAGE_ROOT
import argparse
from collections import Counter
import json
from pathlib import Path
import random
import xml.etree.ElementTree as ET

from experiments.full_page_omr.datasets.clean_page_data import check_disjoint, digest, musical_fingerprint, timed_note
from experiments.full_page_omr.representation.codec_fixtures import add, score, xml
from experiments.full_page_omr.datasets.pilot_data import export_pilot, sha256
from experiments.full_page_omr.representation.score_semantics import inspect_score

RECIPE = 'short-staff-v1'
OPTIONS = dict(inputFrom='musicxml', breaks='encoded', pageWidth=2100,
               pageHeight=2100, scale=55, header='none', footer='none',
               justifyVertically=False)
CAP = 1536


def make_passage(seed, variant='base'):
    """Two bars, four notes/bar; rhythm permutations keep bar fill constant.

    Edits change one pitch or exchange two unequal durations in one bar.
    All variants share a source family, including when used as validation probes.
    """
    if variant not in ('base', 'pitch', 'rhythm'):
        raise ValueError('unknown variant')
    rng = random.Random(seed)
    pitches = [rng.randrange(14) for _ in range(8)]
    rhythms = []
    for _ in range(2):
        rhythm = [.5, .5, 1, 2]
        rng.shuffle(rhythm)
        rhythms.append(rhythm)
    edit = rng.randrange(8)
    if variant == 'pitch':
        pitches[edit] += 1 if pitches[edit] < 13 else -1
    elif variant == 'rhythm':
        rhythm = rhythms[edit // 4]
        i = edit % 4
        j = next(j for j in range(4) if rhythm[j] != rhythm[i])
        rhythm[i], rhythm[j] = rhythm[j], rhythm[i]
    root, part, first = score('', 'Horn')
    for tag in ('work', 'identification', 'credit'):
        root.remove(root.find(tag))
    for b in range(2):
        bar = first if b == 0 else add(part, 'measure', number=2)
        bar.set('id', f'm{b+1}')
        for p, duration in zip(pitches[b*4:b*4+4], rhythms[b]):
            timed_note(bar, 'CDEFGAB'[p % 7], 4+p//7, duration)
    add(add(bar, 'barline', location='right'), 'bar-style', 'light-heavy')
    return xml(root)


def export(output, seed=113, train_count=96, validation_count=16):
    if min(train_count, validation_count) < 2:
        raise ValueError('need at least two families per split for swaps')
    output = Path(output)
    specs, scores = {}, []
    for split, count in (('train', train_count), ('validation', validation_count)):
        for i in range(count):
            family = digest([RECIPE, seed, split, i])
            family_seed = int(family[:15], 16)
            for variant in (('base',) if split == 'train' else ('base', 'pitch', 'rhythm')):
                name = f'{split}_{i:03d}_{variant}'
                source = make_passage(family_seed, variant)
                specs[name] = dict(split=split, seed=family_seed, family_id=family,
                                   variant=variant, kind='horn', musical_fingerprint=musical_fingerprint(source))
                scores.append((name, source))
    manifest = export_pilot(output, scores=scores, render_options=OPTIONS)
    coverage = {s: {'pitch': Counter(), 'duration': Counter()} for s in ('train', 'validation')}
    for r in manifest['records']:
        r.update(specs[r['name']])
        if r['target_length'] > CAP:
            raise ValueError('target exceeds fixed cap')
        tree = ET.parse(output / r['name'] / 'page.svg')
        r['systems'] = sum('system' in n.get('class', '').split() for n in tree.iter())
        if r['systems'] != 1:
            raise ValueError('expected exactly one system')
        for b in inspect_score((output/r['source']).read_text())['parts'][0]['measures']:
            for e in b['events']:
                coverage[r['split']]['pitch'][str(e['pitch'])] += 1
                coverage[r['split']]['duration'][e['duration']] += 1
    check_disjoint(manifest['records'])
    manifest.update(recipe=RECIPE, seed=seed, max_tokens=CAP,
                    purpose='source-disjoint short-staff visual transfer diagnostic',
                    split_policy='independent family seed domains; validation edits stay with parent; no test export',
                    family_counts=dict(train=train_count, validation=validation_count), coverage=coverage)
    manifest['source_hashes'][Path(__file__).name] = sha256(__file__)
    manifest['source_hashes']['clean_page_data.py'] = sha256(PACKAGE_ROOT / 'datasets/clean_page_data.py')
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seed', type=int, default=113)
    parser.add_argument('--train-count', type=int, default=96)
    parser.add_argument('--validation-count', type=int, default=16)
    args = parser.parse_args()
    m = export(**vars(args))
    print(json.dumps(dict(families=m['family_counts'], coverage=m['coverage']), indent=2))
