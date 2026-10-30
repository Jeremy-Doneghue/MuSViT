# Synthetic horn parts

For deterministic font comparisons and glyph/fallback audits, see
[Font coverage sheets](FONT_COVERAGE.md).

Generate a feature-driven mixture independently of the original excerpt generator:

```sh
uv run python -m experiments.full_page_omr.generate_parts --count 20 --seed 0
```

The default `mixed` profile uses 50% focused, 35% combined, and 15% complete parts
by example count (largest-remainder rounding for other batch sizes). A 20-example
batch contains exactly 10, 7, and 3 respectively. Default output is
`experiments/full_page_omr/outputs/synthetic_parts_mixture`, independent of the working directory.
Explicit relative `--output-dir` paths are resolved from the current directory.

Older local exports are retained under `experiments/full_page_omr/outputs/archive/`:
`synthetic_parts_v1` uses the earlier `target.json` representation, while
`synthetic_parts_musicxml` predates the current mixture. These are historical
development artifacts, not inputs to the current training pipeline. Current
mixture, regression and font-coverage outputs sit directly under the experiment's
`outputs/`. Generated files remain ignored by Git.

- Focused examples usually have 4–8 written measures and one requested feature.
  Larger features get enough room to fit safely. Every fifth focused example is
  ordinary music with no requested special feature.
- Combined examples usually have 12–20 measures and selected interactions, such
  as key changes with multibar rests or semiquavers with slurs.
- Complete parts have 32–64 measures over 3–4 pages, with a sampled subset of
  features and longer ordinary passages. They do not include everything.

Musical length and page count are independent. Navigation examples can be short
but deliberately span pages. Placement of changes, similes, rests, solo sections,
navigation anchors, and layout breaks varies with the seed. Compressed symbols
cannot hide directions, signature changes, or layout breaks. Parts always end
with a final double barline.

Request specific features and sizes with a single profile:

```sh
uv run python -m experiments.full_page_omr.generate_parts \
  --profile combined --features key_changes,multibar_rests \
  --measures 16 --pages 2 --count 6 --seed 42 --output-dir experiments/full_page_omr/outputs/key_rest_cases
```

Available feature names: `key_changes`, `meter_changes`, `accent`, `staccato`,
`tenuto`, `marcato`, `slurs`, `beams`, `semiquavers`, `semibreves`, `duration_rests`,
`measure_rests`, `multibar_rests`, `one_bar_simile`, `two_bar_simile`,
`chord_symbols`, `improvisation_slashes`, `repeat`, `endings`, `ds_coda`.
Aliases: `articulations` selects all four articulations, `similes` selects both
simile types, and `improvisation` selects chord symbols and slashes. Slashes also
require chord symbols. Choose at most one structural navigation feature.
`--features ''` requests ordinary music. Ordinary rhythms can still contain
beams and duration rests; requesting a feature guarantees coverage rather than
forbidding all incidental basic notation. Impossible feature/length requests fail
instead of silently dropping features.

## Dataset metadata and splits

Each export is checked for requested **visible** coverage, after ignoring notes
hidden behind simile and multibar-rest abbreviations. Conversion checks then
verify that those features survive into MEI, and the actual rendered pages must
match the requested page count. Multi-page navigation must cross a page boundary.

`manifest.json` contains all records, profile counts, observed feature counts, and
source note-event totals by profile. Event totals are a rough cost indicator,
not an exact decoder-token or compute estimate. Per-example metadata records
requested and actual features, their measure/page locations, source hash
(`composition_id`), generation seed, measure count, page count, and playback route.

Use `--split train`, `validation`, or `test`, with different output directories.
Seeds are derived in separate split domains. All engraving variants of a source
must remain with that source's split. The sampler reserves these combinations:

- Validation: `meter_changes` with `two_bar_simile`.
- Test: `ds_coda` with `improvisation_slashes`.

Neither combination is allowed anywhere in training, including complete parts.
Combined and complete validation/test examples include their reserved pair;
focused examples test individual features. Actual coverage is checked again to
prevent accidental leakage. These recipes are configurable in `scenarios.py`;
they are experimental choices, not established benchmark splits. No model
training or OMR dataloader changes are included.

## Fixed regression suite

The original parts remain available separately and are labeled `regression`,
not training data:

```sh
uv run python -m experiments.full_page_omr.generate_parts \
  --profile regression --count 3 --seed 0 --output-dir experiments/full_page_omr/outputs/synthetic_parts_regression
```

This preserves the repeat, endings, and D.S. al Coda examples containing all
supported notation. `make_part()` remains the fixed fixture helper;
`scenarios.make_scenario()` builds the variable feature-driven examples.

The canonical saved musical score is **MusicXML 4.0**, not the earlier custom
`target.json` representation. Python dataclasses are only the generator's internal
working representation. Each example contains:

- `source.musicxml`: written notes, rests, articulations, signatures, instrument
  transposition, directions, repeats, endings, and segno/coda navigation. This is
  the editable musical source for future engraving variants.
- `source.mei`: derived from the saved MusicXML through Verovio, normalized to MEI
  5.1 All. Slash noteheads require attributes outside MEI Basic. Never edited or
  generated as an independent competing source.
- `metadata.json`: seeds, split/profile, requested/actual coverage, and expected playback route
  using the source's measure IDs. This is dataset metadata, not a score format.
- `layout.json`: renderer version, conversion check result, and actual rendered
  measure-to-page mapping, including the component bars represented by each
  compressed multibar rest. Each future layout variant needs its own mapping.
- `page_*.svg`: rendered pages; optionally `page_*.png`.

No dataset download or model is needed. Existing output directories are never
reused. Seeds reproduce MusicXML and metadata; converter-generated MEI/SVG IDs
and formatting can vary. All variants of a source part belong in the same split.

## Re-engrave an existing score

```sh
uv run python -m experiments.full_page_omr.generate_parts \
  --source experiments/full_page_omr/outputs/synthetic_parts_mixture/part_0001/source.musicxml \
  --output-dir experiments/full_page_omr/outputs/part_0001_variant
```

This reads the saved MusicXML, not the seed or the old JSON target. It copies the
canonical score into a new variant directory and derives MEI and page mappings.
The generator's original metadata remains alongside the original source; it is
not regenerated from an edited score. Expected playback routes need review after
editing navigation.

The converter and checks currently support our generated single-staff subset,
not arbitrary external MusicXML. Compressed `.mxl` input is not supported.
Generation varies system/page breaks; re-engraving preserves breaks from the
saved score. Font controls and separate layout-variant generation remain future work.

For PNGs, add `--png`. CairoSVG needs native Cairo. On Homebrew macOS:

```sh
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uv run python -m experiments.full_page_omr.generate_parts --png
```

## Current coverage

The regression profile cycles through a cross-page repeat, first/second endings,
and D.S. al Coda. Each regression part has 24 written measures with distinct key signatures and
meters at measures 1, 9, and 17, and ends with a final double barline. Supported
meters are 4/4, 3/4, 6/8, and 5/4. MusicXML pitch alterations are explicit even
when supplied visually by a key signature. Tenor saxophone notes are written
pitches with a sounding transposition of a major ninth downward. Section labels,
dynamics, and a swing direction are included.

Regression parts include accent (`>`), staccato, tenuto (`—`), and marcato (`^`,
MusicXML `strong-accent`), with varied positions. Legato is represented by
explicit slur start/end note references. Short slurred groups span consecutive
notes without rests; their individual articulations are cleared. The generator
currently keeps slurs within four-measure phrases; conversion and rendering tests
also cover slurs across a page boundary. Overlapping slurs are not supported yet.
Detached legato (dot plus line) is a separate articulation and is not generated.

Quaver and semiquaver runs have explicit MusicXML beam levels, including partial
secondary-beam hooks for mixed and dotted rhythms. Beams group within quarter-note
beats in 3/4, 4/4, and 5/4, and dotted-quarter beats in 6/8. Rests, longer notes,
barlines, and notes crossing a beat boundary break runs. Isolated short notes
retain flags. 5/4 currently uses five quarter-note beam groups; configurable 3+2
or 2+3 accent patterns and beams through rests are not implemented. The conversion
check verifies primary beam membership; secondary beams are inferred by MEI's
engraver from durations within those groups.

Durations use integer sixteenth-note ticks internally (MusicXML divisions=4).
Generated examples include semiquaver and semibreve notes and duration rests,
along with eighth, quarter, half, and dotted values. Semibreves are placed only
in meters with enough space for four quarter-note beats; in 5/4, the remaining
beat is filled separately. An explicit full-measure rest fills the current meter,
including 3/4 and 6/8, rather than always lasting a semibreve.

Multibar rests are engraving instructions over ordinary consecutive silent
measures. The canonical MusicXML keeps every bar and its full-measure rest, with
a `multiple-rest` measure-style hint. The initial generator chooses a two- or
three-bar quiet passage inside one system, clear of directions and navigation
anchors. Conversion validates that it does not hide signature changes or layout
breaks. MEI renders one `multiRest`; layout metadata maps all underlying bars
to that visible representative and page. Playback retains all of those bars.
Future engraving variants can expand or regroup the same silent passage.

In regression fixtures, one-bar similes repeat measure 2 at measure 3; a two-bar simile repeats measures
11–12 at 13–14. MusicXML retains the actual duplicated notes/rests and uses
`measure-repeat` start/stop instructions for their abbreviated appearance. The
converter checks that each target really matches its preceding source pattern.
One-bar similes render as `mRpt`; two-bar similes render as a single `multiRpt`
with count 2, correcting Verovio 5.0's import as two separate one-bar repeats.
Layout metadata maps both canonical bars to the visible two-bar representative
and retains the source-measure references. These local similes do not create
extra jumps in the structural playback route.

In regression fixtures, measures 23–24 contain an improvisation passage with a written ii–V–I chord
progression (minor seventh, dominant seventh, major seventh). Chord roots follow
the written key, with explicit accidentals and onset positions. MusicXML uses
`harmony` plus stemless slash noteheads and a slash-style instruction. Slash
events have rhythm and staff position, but no melody pitch or rest label; they
do not prescribe an improvised melody. In 6/8 there are two dotted-quarter slashes;
in simple meters there is one slash per quarter beat. More chord qualities,
altered extensions, bass notes, rhythmic slash variants, and longer solo forms
remain future work.

This remains a synthetic starting distribution rather than validated real-part
coverage. Only the regression fixtures retain fixed feature anchors and two
systems per page. Melody uses bounded diatonic walks and recurring rhythms.
Ties, tuplets, chromatic accidentals, font/spacing augmentation, scan degradation,
and other instrument families remain future work.
The OMR dataloader does not consume these scores yet; training tokens will be a
separate derived representation.

## Conversion validation

Before rendering, compare the MusicXML and derived MEI for measure/event identity,
pitch spelling and alterations, durations, rests, articulations, slur endpoints, primary beam groups, effective key
and meter, text directions, repeats, ending extents, navigation functions, final
barline, full-measure/multibar rest semantics, simile source material and pattern
size, chord text/positions, slash noteheads/durations, and instrument transposition.
Conversion failures stop generation. Add
checks whenever adding a musical feature.

Verovio 5.0 imports navigation as generic directions, uses MEI All attributes, and
imports the compound diatonic transposition incorrectly. The normalization step
uses MusicXML to produce compatible signatures, accidentals, articulations,
endings, navigation marks, simile groups, chord labels, and transposition.
The original MusicXML remains unchanged.

Signature definitions are rebuilt from MusicXML because Verovio can drop a key
change at the beginning of a multibar rest.

Exported scenarios are also checked against the official MusicXML 4.0
XSD and MEI 5.1 All Relax NG schemas. Schema validation and Verovio rendering do
not establish complete notation-editor interoperability. For MEI validation:

```sh
curl -L https://music-encoding.org/schema/5.1/mei-all.rng -o /tmp/mei-all.rng
xmllint --noout --relaxng /tmp/mei-all.rng experiments/full_page_omr/outputs/synthetic_parts_mixture/part_0001/source.mei
```

Run the focused regression checks with:

```sh
uv run python -m unittest discover -s tests -p test_generate_parts.py -v
uv run python -m unittest discover -s tests -p test_part_scenarios.py -v
```
