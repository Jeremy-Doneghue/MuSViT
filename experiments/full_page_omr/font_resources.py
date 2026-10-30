"""Bundled font outline audits and portable text for coverage sheets."""

import base64
from functools import lru_cache
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def font_info(path):
    from fontTools.ttLib import TTFont

    with TTFont(path) as font:
        names = font['name']
        return dict(file=Path(path).name, sha256=sha256(path),
                    family=names.getDebugName(1), version=names.getDebugName(5))


def resource_fingerprint(metadata, glyph_dir):
    digest = hashlib.sha256()
    for path in [Path(metadata), *sorted(Path(glyph_dir).glob('*.xml'))]:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _shape_key(symbol):
    return tuple((n.tag.split('}')[-1], tuple(sorted((k, re.sub(r'\s+', ' ', v).strip())
                  for k, v in n.attrib.items() if k not in ('id', 'viewBox', 'overflow'))))
                 for n in symbol.iter() if n is not symbol)


@lru_cache(maxsize=4096)
def _resource_shape(directory, code):
    path = Path(directory) / f'{code}.xml'
    return _shape_key(ET.parse(path).getroot()) if path.exists() else None


def audit_glyphs(svg, requested_dir, fallback_dir):
    root = ET.fromstring(svg)
    ids = {n.get('id'): n for n in root.iter() if n.get('id')}
    rows = {}
    missing_refs = []
    for use in root.iter(f'{{{SVG}}}use'):
        ref = use.get(f'{{{XLINK}}}href') or use.get('href', '')
        if not ref.startswith('#'):
            continue
        identity = ref[1:]
        if identity not in ids:
            missing_refs.append(identity)
            continue
        code = identity.split('-')[0]
        if not re.fullmatch(r'[0-9A-F]{4,6}', code):
            continue
        shape = _shape_key(ids[identity])
        selected = _resource_shape(str(requested_dir), code)
        fallback = _resource_shape(str(fallback_dir), code)
        selected_match = selected is not None and shape == selected
        fallback_match = fallback is not None and shape == fallback
        status = ('ambiguous' if selected_match and fallback_match and Path(requested_dir) != Path(fallback_dir)
                  else 'requested' if selected_match else 'fallback' if fallback_match else 'unattributed')
        rows[code] = dict(codepoint=f'U+{code}', source=status,
                          missing_in_requested=selected is None)
    return dict(glyphs=list(rows.values()), missing_references=sorted(set(missing_refs)),
                fallback_glyphs=sorted(code for code, row in rows.items() if row['source'] == 'fallback'),
                ambiguous_glyphs=sorted(code for code, row in rows.items() if row['source'] == 'ambiguous'),
                unattributed_glyphs=sorted(code for code, row in rows.items() if row['source'] == 'unattributed'),
                method='Compare emitted SVG outlines with selected and fallback Verovio resources; identical outlines are ambiguous.')


@lru_cache(maxsize=16)
def _open_font(path):
    from fontTools.ttLib import TTFont
    return TTFont(path)


@lru_cache(maxsize=4096)
def _shape_text(path, text):
    if not shutil.which('hb-shape'):
        raise RuntimeError('Text-outline previews require hb-shape (HarfBuzz CLI)')
    result = subprocess.run(['hb-shape', str(path), text, '--output-format=json', '--no-glyph-names'],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def outline_text(svg, font_path, fallback_path, font_cache, music_font_name=None):
    """Shape and outline actual font files, avoiding browser/system substitution.

    The chosen files are regular styles; bold/italic CSS is not synthesized.
    Missing characters use an explicitly recorded fallback font, never .notdef.
    """
    from fontTools.pens.svgPathPen import SVGPathPen

    root = ET.fromstring(svg)
    # Verovio puts chord accidentals and some dynamics into embedded SMuFL text
    # faces. Preserve those exact faces instead of treating PUA glyphs as prose.
    from fontTools.ttLib import TTFont
    embedded = {}
    font_cache = Path(font_cache)
    for style in root.iter(f'{{{SVG}}}style'):
        for block in re.findall(r'@font-face\s*\{([^}]+)\}', style.text or ''):
            family = re.search(r"font-family:\s*['\"]([^'\"]+)['\"]", block)
            payload = re.search(r'base64,([A-Za-z0-9+/=]+)', block)
            if family and payload:
                data = base64.b64decode(payload.group(1))
                path = font_cache / (hashlib.sha256(data).hexdigest() + '.otf')
                if not path.exists():
                    font_cache.mkdir(parents=True, exist_ok=True)
                    with TTFont(BytesIO(data)) as face:
                        face.flavor = None
                        face.save(path)
                embedded[family.group(1)] = str(path.resolve())
    font_path, fallback_path = str(Path(font_path).resolve()), str(Path(fallback_path).resolve())
    requested = _open_font(font_path)
    fallback = _open_font(fallback_path)
    cmap, fallback_cmap = requested.getBestCmap(), fallback.getBestCmap()
    misses = set()
    music_fallbacks = set()
    parents = {child: parent for parent in root.iter() for child in parent}
    for text in list(root.iter(f'{{{SVG}}}text')):
        pieces = []

        def collect(node, size, family=''):
            size = float(node.get('font-size', str(size)).removesuffix('px'))
            family = node.get('font-family', family)
            if node.text and node.text.strip():
                pieces.append((node.text, size or 405, family))
            for child in node:
                if child.tag in (f'{{{SVG}}}text', f'{{{SVG}}}tspan'):
                    collect(child, size, family)
                if child.tail and child.tail.strip():
                    pieces.append((child.tail, size or 405, family))
        collect(text, 405)
        glyph_runs = []
        advance = 0
        for string, size, family in pieces:
            runs = []
            for character in string:
                if 0xE000 <= ord(character) <= 0xF8FF:
                    if family not in embedded:
                        raise ValueError(f'Missing embedded SMuFL text font {family}')
                    path = embedded[family]
                    if music_font_name and family != music_font_name:
                        music_fallbacks.add(f'U+{ord(character):04X}')
                else:
                    path = font_path if ord(character) in cmap else fallback_path
                if path == fallback_path and ord(character) not in cmap:
                    misses.add(character)
                    if ord(character) not in fallback_cmap:
                        raise ValueError(f'No text glyph for U+{ord(character):04X}')
                if runs and runs[-1][0] == path:
                    runs[-1] = (path, runs[-1][1] + character)
                else:
                    runs.append((path, character))
            for path, content in runs:
                font = _open_font(path)
                scale = size / font['head'].unitsPerEm
                shaped = _shape_text(path, content)
                for glyph in shaped:
                    if glyph['g'] == 0:
                        raise ValueError('Text shaping produced a missing glyph')
                glyph_runs.append((path, shaped, scale, advance))
                advance += sum(g['ax'] for g in shaped) * scale
        # Page headings put positioning on an enclosing tspan, not the text.
        def positioned(attribute, default):
            return next((n.get(attribute) for n in text.iter()
                         if n.tag in (f'{{{SVG}}}text', f'{{{SVG}}}tspan') and n.get(attribute) is not None), default)
        x, y = float(positioned('x', '0')), float(positioned('y', '0'))
        anchor = positioned('text-anchor', 'start')
        x -= advance / 2 if anchor == 'middle' else advance if anchor == 'end' else 0
        group = ET.Element(f'{{{SVG}}}g', {'class': 'outlined-text', 'data-text': ''.join(s for s, _, _ in pieces)})
        if text.get('id'):
            group.set('id', text.get('id'))
        ET.SubElement(group, f'{{{SVG}}}desc').text = ''.join(s for s, _, _ in pieces)
        for path, shaped, scale, offset in glyph_runs:
            font = _open_font(path)
            glyph_set = font.getGlyphSet()
            order = font.getGlyphOrder()
            cursor = 0
            for glyph in shaped:
                pen = SVGPathPen(glyph_set)
                glyph_set[order[glyph['g']]].draw(pen)
                if pen.getCommands():
                    ET.SubElement(group, f'{{{SVG}}}path', d=pen.getCommands(),
                        transform=f"translate({x + offset + (cursor + glyph['dx']) * scale},{y - glyph['dy'] * scale}) scale({scale},{-scale})")
                cursor += glyph['ax']
        parent = parents[text]
        index = list(parent).index(text)
        parent.remove(text)
        parent.insert(index, group)
    ET.register_namespace('', SVG)
    for style in root.iter(f'{{{SVG}}}style'):
        if style.text:
            style.text = re.sub(r'@font-face\s*\{[^}]+\}', '', style.text)
    return ET.tostring(root, encoding='unicode', xml_declaration=True), dict(
        requested=font_info(font_path), fallback=font_info(fallback_path), shaping='HarfBuzz',
        styles='Regular font outlines; CSS bold/italic is not synthesized',
        music_text_fonts={name: font_info(path) for name, path in embedded.items()},
        music_text_fallbacks=sorted(music_fallbacks),
        fallback_characters=[dict(character=c, codepoint=f'U+{ord(c):04X}') for c in sorted(misses)])


def compact_svg(svg):
    """Crop unused page height using Verovio's absolute drawing bounding boxes."""
    root = ET.fromstring(svg)
    inner = next(n for n in root.iter(f'{{{SVG}}}svg') if n.get('class') == 'definition-scale')
    _, _, width, _ = map(float, inner.get('viewBox').split())
    rectangles = [n for g in root.iter() if 'bounding-box' in g.get('class', '').split()
                  for n in g if n.tag == f'{{{SVG}}}rect']
    if not rectangles:
        raise ValueError('Coverage crops require svgBoundingBoxes')
    # Internal coordinates include a 500-unit page margin; allow extra room for
    # differences between Verovio's metrics and the outlined text face.
    bottom = max(float(r.get('y')) + float(r.get('height')) for r in rectangles) + 1200
    for parent in root.iter():
        for child in list(parent):
            if 'bounding-box' in child.get('class', '').split():
                parent.remove(child)
    inner.set('viewBox', f'0 0 {width:g} {bottom:g}')
    root.set('width', '1100px')
    root.set('height', f'{1100 * bottom / width:g}px')
    ET.register_namespace('', SVG)
    return ET.tostring(root, encoding='unicode', xml_declaration=True), 1100 * bottom / width
