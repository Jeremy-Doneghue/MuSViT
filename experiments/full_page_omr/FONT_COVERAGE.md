# Music font coverage sheets

Render the same deterministic notation specimens in several fonts:

```sh
uv run python -m experiments.full_page_omr.font_coverage \
  --fonts Leipzig,Petaluma \
  --output-dir experiments/full_page_omr/outputs/font_coverage --png
```

The default output directory is `experiments/full_page_omr/outputs/font_coverage`,
independent of the working directory. Explicit relative paths are resolved from
the current directory. Choose a new output directory for subsequent runs. Existing results are never
overwritten. `--png` requires native Cairo; on Homebrew macOS prefix the command
with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` if necessary. Text shaping
requires `hb-shape` from HarfBuzz (already available on the development machine).
The Python FontTools WOFF dependencies are declared in `pyproject.toml`.

Open `index.html` for the overview, or a font's `coverage.svg` directly. Each font
gets the same 14 labeled specimens:

1. Note/rest durations, quaver/semiquaver beams, and partial beam hooks.
2. Sharp/flat key signatures and changes.
3. 4/4, 3/4, 6/8, and 5/4 with appropriate beaming.
4. Accent, staccato, tenuto, and marcato.
5. Slurs within a bar and across a system break.
6. Full-measure rests in different meters.
7. Multibar rests.
8. One-bar repeat similes.
9. Two-bar repeat similes.
10. Repeat and final barlines.
11. First/second endings.
12. Segno, To Coda, D.S. al Coda, and coda symbols.
13. Improvisation slashes with minor/major/dominant sevenths and sharp/flat roots.
14. Title, Unicode text, directions, rehearsal marks, and dynamics.

This covers the generator's currently supported notation, not the entire SMuFL
character set. Case expectations are checked against visible MusicXML coverage,
and the existing MusicXML-to-MEI preservation checks run before each engraving.

## Bundled fonts

Use Verovio's installed music resources directly. The default comparison is
`Leipzig,Petaluma`; use `--fonts` to select other bundled faces. No downloaded
Petaluma files, local preparation step, or `--petaluma-dir` option are needed.
Font resource hashes and the renderer version are recorded in reports.
Engraving line weights and spacing stay at the same settings across fonts.

The earlier downloaded-font comparison is retained under
`outputs/archive/font_coverage_downloaded_history/` as static images and audit
history. Its prepared fonts and temporary text-font caches were removed;
historical source paths in its reports are not current resources.

## Text and portability

Normal text uses the DejaVu Serif face packaged with Matplotlib. Music glyphs
and embedded SMuFL music text use Verovio's bundled resources. Override normal text with
`--text-font-file path/to/Regular.otf`. All text is shaped with HarfBuzz and then
outlined from the actual font files, including fonts embedded by Verovio for
SMuFL symbols within chord text. Browsers and Cairo therefore do not need fonts
installed system-wide. Missing normal-text characters use an explicitly recorded
DejaVu Serif fallback. No .notdef box is silently accepted.

The selected text files are regular styles; synthetic bold and italic are not
applied to those outlines. Distinct bold/italic files and general multilingual
layout remain future work. SVG text descriptions retain the original strings.
The sheet's UI labels use generic sans-serif; they are not specimens of the
selected notation text face.

## Reports and review

- `manifest.json`: renderer version, identical source hashes per case, font
  summaries, fallback selection, and audit limitations.
- `<font>/coverage.svg`, optionally `coverage.png`: compact labeled sheet.
- `<font>/report.json`: per-case glyph/source audit and text fallback characters.
- `<font>/<case>/source.musicxml`, `source.mei`, `layout.json`: inspectable sources
  and actual engraving configuration.
- `<font>/<case>/page_01.svg`: raw Verovio diagnostic output.
- `<font>/<case>/preview.svg`: cropped, self-contained specimen with outlined text.

Music glyphs are compared by their emitted SVG outlines against the requested
and fallback resource files. Reports distinguish requested matches, known
fallback, identical/ambiguous matches, unexplained outlines, and broken SVG
references. Embedded music-text faces are tracked separately. Font file/resource
hashes and available versions identify what was actually used; bundled resources
without version metadata explicitly record a null font version.

These checks do **not** certify engraving quality or automatically detect all
collisions. Inspect beam slopes, glyph proportions, spacing, slur placement,
chord readability, and font mixing visually. A font can have every required glyph
and still produce poor engraving.

Run checks with:

```sh
uv run python -m unittest discover -s tests -p test_font_coverage.py -v
```
