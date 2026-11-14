"""Glyph fallback and text outlining used by the active renderer."""
from importlib.util import find_spec
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from experiments.full_page_omr.generation.font_resources import (
    SVG, audit_glyphs, outline_text,
)

BASE_TEXT = Path(find_spec('matplotlib').origin).parent / 'mpl-data/fonts/ttf/DejaVuSerif.ttf'


class FontResourcesTests(unittest.TestCase):

    def test_audit_detects_actual_fallback_and_broken_references(self):
        with tempfile.TemporaryDirectory() as directory:
            selected, fallback = Path(directory) / 'selected', Path(directory) / 'fallback'
            selected.mkdir(); fallback.mkdir()
            (selected / 'E050.xml').write_text('<symbol><path d="M0 0L1 1"/></symbol>')
            (fallback / 'E050.xml').write_text('<symbol><path d="M0 0L2 2"/></symbol>')
            svg = f'<svg xmlns="{SVG}"><defs><symbol id="E050-test"><path d="M0 0L2 2"/></symbol></defs><use href="#E050-test"/><use href="#E999-missing"/></svg>'
            report = audit_glyphs(svg, selected, fallback)
            self.assertEqual(report['fallback_glyphs'], ['E050'])
            self.assertEqual(report['missing_references'], ['E999-missing'])
            self.assertFalse(report['unattributed_glyphs'])

    @unittest.skipUnless(shutil.which('hb-shape'), 'HarfBuzz CLI is required')
    def test_outlined_titles_use_tspan_position_and_ignore_tooltips(self):
        svg = f'''<svg xmlns="{SVG}"><text font-size="0"><tspan x="1000" y="300" text-anchor="middle"><title>not visible</title><tspan font-size="100">Title — étude</tspan></tspan></text></svg>'''
        with tempfile.TemporaryDirectory() as directory:
            outlined, report = outline_text(svg, BASE_TEXT, BASE_TEXT, directory)
            root = ET.fromstring(outlined)
            group = root.find(f'{{{SVG}}}g')
            self.assertEqual(group.get('data-text'), 'Title — étude')
            self.assertNotIn('not visible', outlined)
            self.assertFalse(list(root.iter(f'{{{SVG}}}text')))
            self.assertIn(',300.0)', next(root.iter(f'{{{SVG}}}path')).get('transform'))
            self.assertFalse(report['fallback_characters'])

    @unittest.skipUnless(shutil.which('hb-shape'), 'HarfBuzz CLI is required')
    def test_missing_text_character_is_reported(self):
        from fontTools.ttLib import TTFont
        svg = f'<svg xmlns="{SVG}"><text x="10" y="20" font-size="15">Solo — étude</text></svg>'
        with tempfile.TemporaryDirectory() as directory:
            # Exercise explicit fallback without requiring a downloaded font.
            limited = Path(directory) / 'limited.ttf'
            with TTFont(BASE_TEXT) as font:
                for table in font['cmap'].tables:
                    if table.isUnicode():
                        table.cmap.pop(0x2014, None)
                font.save(limited)
            outlined, report = outline_text(svg, limited, BASE_TEXT, directory)
            self.assertEqual(report['fallback_characters'], [dict(character='—', codepoint='U+2014')])
            self.assertIn('Solo — étude', outlined)


if __name__ == '__main__':
    unittest.main()
