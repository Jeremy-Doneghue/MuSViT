from contextlib import redirect_stdout
from importlib.util import find_spec
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from experiments.full_page_omr.font_coverage import coverage_cases, generate_coverage
from experiments.full_page_omr.font_resources import (
    SVG, audit_glyphs, outline_text,
)
from experiments.full_page_omr.scenarios import FEATURES, observe_features

BASE_TEXT = Path(find_spec('matplotlib').origin).parent / 'mpl-data/fonts/ttf/DejaVuSerif.ttf'


class FontCoverageTests(unittest.TestCase):
    def test_catalog_covers_every_supported_feature(self):
        cases = coverage_cases()
        self.assertEqual(len(cases), 14)
        self.assertEqual({f for case in cases for f in case.expected}, FEATURES)
        for case in cases:
            self.assertFalse(set(case.expected) - observe_features(case.source()).keys())
        self.assertEqual([c.source() for c in cases], [c.source() for c in coverage_cases()])

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

    @unittest.skipUnless(shutil.which('hb-shape'), 'HarfBuzz CLI is required')
    def test_sheet_is_self_contained_and_has_unique_ids(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            folder = Path(directory) / 'coverage'
            manifest = generate_coverage(folder, fonts=['Leipzig', 'Petaluma'])
            self.assertEqual([font['name'] for font in manifest['fonts']], ['Leipzig', 'Petaluma'])
            report = json.loads((folder / 'Leipzig/report.json').read_text())
            self.assertEqual(len(report['cases']), 14)
            self.assertFalse(report['summary']['unattributed'])
            self.assertFalse(report['summary']['missing_references'])
            sheet = (folder / 'Leipzig/coverage.svg').read_bytes()
            root = ET.fromstring(sheet)
            ids = [n.get('id') for n in root.iter() if n.get('id')]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertIn('encoding=', sheet[:80].decode())
            self.assertNotIn(b'@font-face', sheet)
            self.assertNotIn(b'<image', sheet)
            self.assertTrue((folder / 'index.html').exists())
            self.assertTrue((folder / 'Leipzig/text/preview.svg').exists())
            petaluma = json.loads((folder / 'Petaluma/report.json').read_text())
            self.assertEqual(petaluma['font']['provenance'], 'Verovio bundled resources')
            self.assertFalse(petaluma['summary']['unattributed'])
            self.assertFalse(petaluma['summary']['missing_references'])
            self.assertTrue((folder / 'Petaluma/coverage.svg').is_file())
            with self.assertRaises(FileExistsError):
                generate_coverage(folder, fonts=['Leipzig', 'Petaluma'])

    def test_unknown_font_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'invalid'
            with self.assertRaisesRegex(ValueError, 'not bundled'):
                generate_coverage(folder, fonts=['MissingFont'])
            self.assertFalse(folder.exists())


if __name__ == '__main__':
    unittest.main()
