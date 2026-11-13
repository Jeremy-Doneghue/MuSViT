"""Direct, seeded Humdrum sources for Curriculum Lab; no MusicXML or ML imports.

Generated sources follow one fixed spelling/order. This is a small generation
profile, not a normalizer or validator for arbitrary imported Humdrum.
"""
from dataclasses import dataclass
import hashlib
from importlib.util import find_spec
import io
from pathlib import Path
import random
import re
import xml.etree.ElementTree as ET

PROFILE = 'musvit-humdrum-preview-v1'
EXAMPLES = ('note', 'passage', 'horn_page', 'piano_page', 'drums_page',
            'piano', 'cross_staff', 'drums')
PITCHES = tuple(['c','d','e','f','g','a','b','cc','dd','ee','ff','gg','aa','bb'])


@dataclass(frozen=True)
class Score:
    source: str
    notes: int
    rests: int
    measures: int
    staves: int
    instructions: tuple[str, ...] = ()
    pedals: int = 0
    cross_staff: bool = False


def make_score(example, seed=7):
    if example not in EXAMPLES:
        raise ValueError('Unknown Humdrum example')
    if type(seed) is not int or not 0 <= seed <= 2**31-1:
        raise ValueError('Music seed must be an integer from 0 to 2**31-1')
    rng = random.Random(seed)
    if example == 'note':
        return Score('\n'.join(['**kern', '*staff1', '*I"Horn', '*clefG2', '*M4/4',
                                '4'+PITCHES[seed % len(PITCHES)], '==', '*-', '']), 1, 0, 1, 1)
    if example == 'cross_staff':
        # One beamed voice begins on the lower staff and crosses above. The
        # upper staff has a separate whole-rest voice; no fake duplicate notes.
        rows = [
            '!!!RDF**kern: > = above',
            '**kern\t**kern', '*part1\t*part1', '*staff2\t*staff1',
            '*I"Piano\t*I"Piano', '*clefF4\t*clefG2', '*M4/4\t*M4/4', '=1\t=1',
            '8cL\t1r', '8d\t.', '8e>\t.', '8f>J\t.', '2g\t.', '==\t==', '*-\t*-', '']
        return Score('\n'.join(rows), 5, 1, 1, 2, cross_staff=True)
    if example.startswith('piano'):
        return _piano(24 if example.endswith('_page') else 2, rng)
    if example.startswith('drums'):
        return _drums(24 if example.endswith('_page') else 2, rng)
    bars = 24 if example == 'horn_page' else 2
    rows = ['**kern\t**dynam', '*staff1\t*staff1', '*I"Horn\t*',
            '*clefG2\t*', '*k[]\t*', '*M4/4\t*', '*MM120\t*']
    notes = rests = 0
    instructions = ('Light swing',)
    for bar in range(bars):
        rows.append(f'={bar+1}\t={bar+1}')
        if bar == 0:
            rows.append('!LO:TX:a:t=Light swing\t!')
        # Whole bars built from quarters or eighths; no duration rounding.
        duration, count = rng.choice(((4,4),(8,8)))
        for index in range(count):
            is_rest = index == count-1 and bar % 3 == 1
            pitch = 'r' if is_rest else rng.choice(PITCHES[:10])
            token = str(duration)+pitch
            if duration == 8 and not is_rest:
                token += 'L' if index == 0 else 'J' if index == count-1 else ''
            # Avoid an unterminated beam when the final event is a rest.
            if duration == 8 and is_rest:
                token += 'J'
            notes += not is_rest
            rests += is_rest
            rows.append(token+'\t'+('mf' if index == 0 and bar % 4 == 0 else '.'))
    rows += ['==\t==', '*-\t*-', '']
    return Score('\n'.join(rows), notes, rests, bars, 1, instructions)


def _piano(bars, rng):
    rows = ['**kern\t**kern\t**dynam', '*part1\t*part1\t*part1',
            '*staff2\t*staff1\t*staff1', '*I"Piano\t*I"Piano\t*',
            '*clefF4\t*clefG2\t*', '*M4/4\t*M4/4\t*']
    for bar in range(bars):
        rows += [f'={bar+1}\t={bar+1}\t={bar+1}']
        rows += ['*ped\t*\t*', '*\t*^\t*']
        if bar == 0:
            rows += ['!\t!LO:TX:a:t=Legato\t!\t!']
        # Upper staff splits into two independent voices, then merges at the
        # bar end. Chord tones have fixed ascending pitch order.
        high = rng.choice(('cc ee', 'dd ff', 'ee gg'))
        rows += ['1C\t'+ ' '.join('2'+p for p in high.split())+'\t1g\t'+('p' if bar % 4 == 0 else '.'),
                 '.\t2dd\t.\t.', '*\t*v\t*v\t*', '*Xped\t*\t*']
    rows += ['==\t==\t==', '*-\t*-\t*-', '']
    return Score('\n'.join(rows), bars*5, 0, bars, 2, ('Legato',), bars*2)


def _drums(bars, rng):
    rows = ['**kern\t**dynam', '*staff1\t*staff1', '*I"Drums\t*',
            '*clefX\t*', '*M4/4\t*', '*^\t*']
    instructions = ('BRUSHES — light swing', 'RIDE CYM. / B.D. on 1; fill →')
    for bar in range(bars):
        rows += [f'={bar+1}\t={bar+1}\t={bar+1}']
        if bar < 2:
            rows += [f'!LO:TX:a:t={instructions[bar]}\t!\t!']
        bass_beats = rng.choice(((0,2),(0,3),(1,3)))
        for beat in range(4):
            rows += ['!LO:N:head=x\t!\t!']
            rows += ['4gR\t'+('4cR' if beat in bass_beats else '4r')+'\t'+('mf' if bar == beat == 0 else '.')]
    rows += ['*v\t*v\t*', '==\t==', '*-\t*-', '']
    return Score('\n'.join(rows), bars*6, bars*2, bars, 1, instructions)



def _stable_ids(text):
    """Normalize renderer-generated XML IDs and their local references."""
    root = ET.fromstring(text)
    # Verovio emits glyph definitions from an unordered map. Their suffixes
    # are random, but the SMuFL glyph prefix is stable.
    for node in root.iter():
        if node.tag.rsplit('}',1)[-1] == 'defs':
            node[:] = sorted(node, key=lambda child: child.get('id','').split('-',1)[0])
    identities = {}
    for node in root.iter():
        for key,value in node.attrib.items():
            if key in ('id', '{http://www.w3.org/XML/1998/namespace}id'):
                if value in identities:
                    raise ValueError('Duplicate generated XML ID')
                identities[value] = f'id{len(identities)+1}'
    def references(value):
        return re.sub(r'#([A-Za-z0-9_.:-]+)',
                      lambda match: '#'+identities.get(match[1],match[1]), value)
    for node in root.iter():
        if node.tail and not node.tail.strip():
            node.tail = None
        if len(node) and node.text and not node.text.strip():
            node.text = None
        for key,value in list(node.attrib.items()):
            if key in ('id','{http://www.w3.org/XML/1998/namespace}id'):
                node.set(key, identities[value])
            elif key == 'class':
                node.set(key, ' '.join(identities.get(token, token) for token in value.split()))
            else:
                node.set(key, references(value))
        if node.tag.rsplit('}',1)[-1] == 'style' and node.text:
            node.text = references(node.text)
        if node.tag.rsplit('}',1)[-1] == 'application':
            node.attrib.pop('isodate', None)
    return ET.tostring(root, encoding='unicode')


def render(score, folder, font='Leipzig'):
    """Render the exact canonical source to one page, with derived SVG and MEI."""
    import verovio
    from cairosvg import svg2png
    from PIL import Image
    from experiments.full_page_omr.generation.font_resources import outline_text
    if font not in ('Leipzig','Bravura','Petaluma'):
        raise ValueError('Unknown engraving font')
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    options = dict(inputFrom='humdrum', breaks='auto', pageWidth=2100, pageHeight=2970,
                   scale=40, header='none', footer='none', justifyVertically=False, font=font)
    toolkit = verovio.toolkit()
    toolkit.setOptions(options)
    toolkit.resetXmlIdSeed(0)
    if not toolkit.loadData(score.source) or toolkit.getPageCount() != 1:
        raise ValueError('Humdrum preview requires a complete single-page render')
    mei = _stable_ids(toolkit.getMEI())
    root = ET.fromstring(mei)
    for node in root.iter():
        node.tag = node.tag.rsplit('}',1)[-1]
    expected = {'note':score.notes,'rest':score.rests,'measure':score.measures,
                'staffDef':score.staves,'pedal':score.pedals}
    for tag, count in expected.items():
        actual = len(root.findall('.//'+tag)) + (len(root.findall('.//mRest')) if tag == 'rest' else 0)
        if actual != count:
            raise ValueError(f'Humdrum render changed {tag} count; expected {count}')
    if any(text not in ''.join(root.itertext()) for text in score.instructions):
        raise ValueError('Humdrum render omitted a performance instruction')
    if score.cross_staff and not root.findall('.//note[@staff]'):
        raise ValueError('Humdrum render omitted cross-staff assignment')
    svg = toolkit.renderToSVG(1).replace('overflow="inherit"', 'overflow="visible"')
    text_font = Path(find_spec('matplotlib').origin).parent/'mpl-data/fonts/ttf/DejaVuSerif.ttf'
    svg, _ = outline_text(svg, text_font, text_font, folder/'text_fonts', 'Leipzig')
    svg = _stable_ids(svg)
    outputs = {'source.krn':score.source,'source.mei':mei,'source.svg':svg}
    for name, text in outputs.items():
        (folder/name).write_text(text, encoding='utf-8')
    pixels = svg2png(bytestring=svg.encode('utf-8'), output_width=1400, background_color='white')
    with Image.open(io.BytesIO(pixels)) as opened:
        image = opened.convert('RGB')
    provenance = dict(profile=PROFILE, source_format='humdrum', renderer=toolkit.getVersion(),
        render_options=options, source_sha256=hashlib.sha256(score.source.encode()).hexdigest(),
        source_bytes=len(score.source.encode()), source_lines=len(score.source.splitlines()),
        generated_coverage=dict(notes=score.notes,rests=score.rests,measures=score.measures,
                                staves=score.staves,pedal_markers=score.pedals,
                                performance_instructions=len(score.instructions),cross_staff=score.cross_staff),
        derived_sha256={name:hashlib.sha256(text.encode()).hexdigest() for name,text in outputs.items()
                        if name != 'source.krn'},
        omissions=[], normalization='fixed generated syntax; imported Humdrum normalization unimplemented')
    return image, provenance
