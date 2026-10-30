"""Deterministic notation coverage sheets for comparing music and text fonts.

Run: python -m experiments.full_page_omr.font_coverage --help
"""

import argparse
from dataclasses import dataclass, replace
import hashlib
import html
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from .generate_parts import ChordSymbol, Event, Measure, Part, Simile, Slur, render_musicxml, validate
from .musicxml_score import to_musicxml
from .scenarios import FEATURES, observe_features
from .font_resources import (
    SVG, audit_glyphs, compact_svg, font_info, outline_text, resource_fingerprint,
)


@dataclass
class CoverageCase:
    name: str
    title: str
    expected: tuple[str, ...]
    part: Part

    def source(self):
        root = ET.fromstring(to_musicxml(self.part))
        root.find('part-list/score-part/part-name').text = 'Sax'
        root.find('work/work-title').text = 'Title — étude' if self.name == 'text' else ''
        return ET.tostring(root, encoding='unicode', xml_declaration=True)


def coverage_cases():
    cases = []

    def new(name, title, count, expected=()):
        bars = [Measure(f'm{i + 1}', i + 1, 0, (4, 4),
                        [Event(f'm{i + 1}-e{j + 1}', 4, 'cdef'[j]) for j in range(4)]) for i in range(count)]
        part = Part(2, 0, 'Tenor saxophone', 'plain', bars, [], {},
                    [m.id for m in bars], [], [], [],
                    [m.id for i, m in enumerate(bars) if i and i % 2 == 0], [])
        case = CoverageCase(name, title, tuple(expected), part)
        cases.append(case)
        return part

    part = new('rhythm', 'Notes, rests and beam hooks', 4,
               ['semiquavers', 'semibreves', 'duration_rests', 'beams'])
    durations = [1, 1, 2, 2, 1, 1, 3, 1, 1, 3]
    part.measures[0].events = [Event(f'm1-e{i + 1}', d, 'cdefgab'[i % 7]) for i, d in enumerate(durations)]
    part.measures[1].events = [Event(f'm2-e{i + 1}', d, None) for i, d in enumerate([1, 1, 2, 4, 8])]
    part.measures[2].events = [Event('m3-e1', 16, 'c')]
    part.measures[3].events = [Event('m4-e1', 16, None)]
    part = new('keys', 'Key signatures: C, G, D, F, B-flat, E-flat', 6, ['key_changes'])
    for measure, key in zip(part.measures, (0, 1, 2, -1, -2, -3), strict=True):
        measure.key = key
    part = new('meters', 'Meters and simple / compound beaming', 4, ['meter_changes', 'beams'])
    for measure, meter in zip(part.measures, ((4, 4), (3, 4), (6, 8), (5, 4)), strict=True):
        measure.meter = meter
        measure.events = [Event(f'{measure.id}-e{i + 1}', 2, 'cdefgab'[i % 7])
                          for i in range(meter[0] * 8 // meter[1])]
    part = new('articulations', 'Accent, staccato, tenuto, marcato', 4,
               ['accent', 'staccato', 'tenuto', 'marcato'])
    for measure, code in zip(part.measures, ('acc', 'stacc', 'ten', 'marc'), strict=True):
        for event in measure.events:
            event.articulation = code
    part = new('slurs', 'Slurs within a bar and across a system break', 4, ['slurs'])
    part.slurs = [Slur('slur1', 'm1-e1', 'm1-e3'), Slur('slur2', 'm2-e4', 'm3-e2')]
    part = new('measure-rests', 'Full-bar rests in 4/4, 3/4, 6/8, 5/4', 4, ['measure_rests'])
    for measure, meter in zip(part.measures, ((4, 4), (3, 4), (6, 8), (5, 4)), strict=True):
        measure.meter = meter
        measure.events = [Event(f'{measure.id}-e1', meter[0] * 16 // meter[1], None, measure_rest=True)]
    part = new('multibar-rest', 'Three-bar rest with written bars retained', 5, ['multibar_rests'])
    part.system_breaks = ['m5']
    part.multirests = [['m2', 'm3', 'm4']]
    for measure in part.measures[1:4]:
        measure.events = [Event(f'{measure.id}-e1', 16, None, measure_rest=True)]
    for name, size, count in (('simile-one', 1, 4), ('simile-two', 2, 6)):
        part = new(name, f'{size}-bar repeat simile', count,
                   ['one_bar_simile' if size == 1 else 'two_bar_simile'])
        part.system_breaks = ['m5'] if size == 2 else ['m3']
        part.similes = [Simile([m.id for m in part.measures[size:2 * size]],
                               [m.id for m in part.measures[:size]])]
        for source, target in zip(part.measures[:size], part.measures[size:2 * size], strict=True):
            target.events = [replace(e, id=f'{target.id}-e{i + 1}') for i, e in enumerate(source.events)]
    part = new('repeat', 'Repeat barlines and final barline', 6, ['repeat'])
    part.scenario = 'repeat'
    part.navigation = dict(start='m2', end='m5', times=2)
    part.playback = ['m1', 'm2', 'm3', 'm4', 'm5', 'm2', 'm3', 'm4', 'm5', 'm6']
    part = new('endings', 'First and second endings', 8, ['endings'])
    part.scenario = 'endings'
    part.navigation = dict(start='m1', first_ending=['m3', 'm4'], second_ending=['m5', 'm6'], times=2)
    part.playback = ['m1', 'm2', 'm3', 'm4', 'm1', 'm2', 'm5', 'm6', 'm7', 'm8']
    part = new('navigation', 'Segno, To Coda, D.S. al Coda and coda', 8, ['ds_coda'])
    part.scenario = 'ds_coda'
    part.navigation = dict(segno='m2', to_coda='m3', ds='m5', coda='m7')
    part.playback = ['m1', 'm2', 'm3', 'm4', 'm5', 'm2', 'm3', 'm7', 'm8']
    part = new('improvisation', 'Slashes and chord roots / accidentals / qualities', 4,
               ['improvisation_slashes', 'chord_symbols'])
    for measure in part.measures:
        measure.events = [Event(f'{measure.id}-e{i + 1}', 4, None, slash=True) for i in range(4)]
    part.measures[0].chords = [ChordSymbol('h1', 0, 'D', 0, 'minor-seventh'), ChordSymbol('h2', 8, 'G', 0, 'dominant')]
    part.measures[1].chords = [ChordSymbol('h3', 0, 'C', 0, 'major-seventh')]
    part.measures[2].chords = [ChordSymbol('h4', 0, 'B', -1, 'dominant')]
    part.measures[3].chords = [ChordSymbol('h5', 0, 'F', 1, 'minor-seventh')]
    part.directions = [dict(measure='m1', kind='dir', text='Solo — improvise')]
    part = new('text', 'Title, directions, rehearsal marks and dynamics', 4)
    part.directions = [dict(measure='m1', kind='dir', text='Swing — étude; straight eighths'),
                       dict(measure='m1', kind='reh', text='A'), dict(measure='m3', kind='reh', text='B')]
    for measure, dynamic in zip(part.measures, ('p', 'mf', 'f', 'ff'), strict=True):
        part.directions.append(dict(measure=measure.id, kind='dynam', text=dynamic))
    for case in cases:
        validate(case.part)
        missing = set(case.expected) - observe_features(case.source()).keys()
        if missing:
            raise ValueError(f'{case.name} is missing coverage: {sorted(missing)}')
    promised = {f for case in cases for f in case.expected}
    if promised != FEATURES:
        raise ValueError(f'Coverage catalog mismatch: {sorted(FEATURES - promised)}')
    return cases


def _embed(sheet, svg, y, prefix, height):
    score = ET.fromstring(svg)
    ids = {node.get('id'): prefix + '-' + node.get('id') for node in score.iter() if node.get('id')}
    for node in score.iter():
        if node.get('id'):
            node.set('id', ids[node.get('id')])
        for key, value in list(node.attrib.items()):
            if value.startswith('#') and value[1:] in ids:
                node.set(key, '#' + ids[value[1:]])
            elif 'url(#' in value:
                for old, new in ids.items():
                    value = value.replace(f'url(#{old})', f'url(#{new})')
                node.set(key, value)
    score.set('x', '20')
    score.set('y', str(y))
    score.set('width', '1100')
    score.set('height', str(height))
    sheet.append(score)


def generate_coverage(output_dir, fonts=('Leipzig', 'Petaluma'), png=False,
                      text_font_file=None, fallback='Bravura'):
    import verovio
    from importlib.util import find_spec

    if fallback not in ('Bravura', 'Leipzig'):
        raise ValueError('fallback must be Bravura or Leipzig')
    if not fonts:
        raise ValueError('select at least one bundled font')
    if len(set(fonts)) != len(fonts) or any(not name.isalnum() for name in fonts):
        raise ValueError('bundled font names must be unique alphanumeric names')
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f'refusing to overwrite {output}')
    resource_path = Path(verovio.toolkit().getResourcePath())
    for name in fonts:
        if not (resource_path / f'{name}.xml').exists() or not (resource_path / name).is_dir():
            raise ValueError(f'font is not bundled with Verovio: {name}')
    if not shutil.which('hb-shape'):
        raise RuntimeError('Coverage sheets require hb-shape (HarfBuzz CLI) for portable text outlines')
    # Use the packaged face directly; avoid scanning/installing system fonts.
    base_text = Path(find_spec('matplotlib').origin).parent / 'mpl-data/fonts/ttf/DejaVuSerif.ttf'
    if not base_text.is_file():
        raise FileNotFoundError(base_text)
    text_path = Path(text_font_file) if text_font_file else base_text
    font_info(text_path)  # Validate a requested face before creating any output.
    output.mkdir(parents=True)
    configurations = []
    for name in fonts:
        configurations.append(dict(name=name, glyph_dir=str(resource_path / name),
            metadata=str(resource_path / f'{name}.xml'),
            resource_sha256=resource_fingerprint(resource_path / f'{name}.xml', resource_path / name),
            provenance='Verovio bundled resources', source='https://github.com/rism-digital/verovio/tree/version-5.0.0/data',
            font_version=None, text_file=str(text_path)))
    cases = coverage_cases()
    source_hashes = {case.name: hashlib.sha256(case.source().encode()).hexdigest() for case in cases}
    manifest = dict(renderer=verovio.toolkit().getVersion(), font_fallback=fallback,
                    sources=source_hashes, fonts=[],
                    limitations=['Outline comparisons cannot distinguish identical glyph designs.',
                                 'Collisions and overall engraving quality require visual review.',
                                 'Text uses regular font files shaped with HarfBuzz; no synthetic bold/italic.'])
    html_rows = []
    for config in configurations:
        name = config['name']
        folder = output / name
        folder.mkdir()
        sheet = ET.Element(f'{{{SVG}}}svg', width='1140', version='1.1')
        ET.SubElement(sheet, f'{{{SVG}}}rect', width='100%', height='100%', fill='white')
        ET.SubElement(sheet, f'{{{SVG}}}text', x='20', y='40', **{'font-family': 'sans-serif', 'font-size': '26'}).text = f'{name} — notation coverage'
        ET.SubElement(sheet, f'{{{SVG}}}text', x='20', y='68', **{'font-family': 'sans-serif', 'font-size': '15'}).text = f'Text: {font_info(config["text_file"])["family"]}; fallback: {fallback}; same MusicXML for every font'
        y = 100
        reports = []
        for index, case in enumerate(cases):
            options = dict(font=name, fontFallback=fallback, svgBoundingBoxes=True)
            if config.get('archive') and not config.get('resource_path'):
                options['fontAddCustom'] = [config['archive']]
            case_folder = folder / case.name
            layout = render_musicxml(case.source(), case_folder, engraving_options=options,
                                     resource_path=config.get('resource_path'))
            if len(layout['pages']) != 1:
                raise ValueError(f'Coverage case {case.name} unexpectedly rendered multiple pages')
            svg = (case_folder / 'page_01.svg').read_text(encoding='utf-8')
            music_audit = audit_glyphs(svg, config['glyph_dir'], resource_path / fallback)
            compact, height = compact_svg(svg)
            compact, text_audit = outline_text(compact, config['text_file'], base_text,
                                             output / 'embedded_text_fonts', name)
            (case_folder / 'preview.svg').write_text(compact, encoding='utf-8')
            ET.SubElement(sheet, f'{{{SVG}}}text', x='20', y=str(y + 22),
                **{'font-family': 'sans-serif', 'font-size': '19', 'font-weight': 'bold'}).text = f'{index + 1:02d}. {case.title}'
            y += 38
            _embed(sheet, compact, y, case.name, height)
            y += height + 12
            reports.append(dict(case=case.name, expected=list(case.expected),
                                actual=observe_features(case.source()), music=music_audit, text=text_audit))
        sheet.set('height', f'{y + 20:g}')
        sheet.set('viewBox', f'0 0 1140 {y + 20:g}')
        ET.register_namespace('', SVG)
        sheet_svg = ET.tostring(sheet, encoding='unicode', xml_declaration=True)
        (folder / 'coverage.svg').write_text(sheet_svg, encoding='utf-8')
        if png:
            import cairosvg
            cairosvg.svg2png(bytestring=sheet_svg.encode(), write_to=str(folder / 'coverage.png'), background_color='white')
        summary = dict(music_fallbacks=sorted({g for r in reports for g in r['music']['fallback_glyphs']} |
                                             {g for r in reports for g in r['text']['music_text_fallbacks']}),
                       ambiguous=sorted({g for r in reports for g in r['music']['ambiguous_glyphs']}),
                       unattributed=sorted({g for r in reports for g in r['music']['unattributed_glyphs']}),
                       missing_references=sorted({g for r in reports for g in r['music']['missing_references']}),
                       text_fallbacks=sorted({c['codepoint'] for r in reports for c in r['text']['fallback_characters']}))
        report = dict(font=config, summary=summary, cases=reports)
        (folder / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        manifest['fonts'].append(dict(name=name, sheet=f'{name}/coverage.svg', report=f'{name}/report.json', summary=summary))
        html_rows.append(f'<section><h2>{html.escape(name)}</h2><p>Music fallback glyphs: {len(summary["music_fallbacks"])}; '
                         f'ambiguous outline matches: {len(summary["ambiguous"])}; '
                         f'text fallback characters: {len(summary["text_fallbacks"])}. '
                         f'<a href="{name}/report.json">Audit report</a></p>'
                         f'<img src="{name}/coverage.svg" alt="{html.escape(name)} notation coverage"></section>')
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    (output / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Music font coverage</title>'
        '<style>body{font:16px system-ui;margin:24px;background:#eee;color:#222}section{background:white;padding:20px;margin-bottom:24px}'
        'img{width:100%;max-width:1140px;height:auto}p{max-width:85ch}</style><h1>Music font coverage</h1>'
        '<p>Compare the same notation in each font. Review missing glyphs, fallback, spacing, collisions and chord readability. '
        'Reports identify resource-outline matches; visual quality is not automatically certified.</p>' + ''.join(html_rows), encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path,
                        default=Path(__file__).resolve().parent / 'outputs/font_coverage')
    parser.add_argument('--fonts', default='Leipzig,Petaluma', help='comma-separated bundled Verovio font names')
    parser.add_argument('--text-font-file', type=Path, help='regular OTF/TTF face for normal text (default: packaged DejaVu Serif)')
    parser.add_argument('--fallback', choices=['Bravura', 'Leipzig'], default='Bravura')
    parser.add_argument('--png', action='store_true', help='also rasterize each compact sheet (requires Cairo)')
    args = parser.parse_args()
    result = generate_coverage(args.output_dir, [f.strip() for f in args.fonts.split(',') if f.strip()],
                               png=args.png, text_font_file=args.text_font_file, fallback=args.fallback)
    for font in result['fonts']:
        print(font['name'], json.dumps(font['summary']))
    print(args.output_dir / 'index.html')


if __name__ == '__main__':
    main()
