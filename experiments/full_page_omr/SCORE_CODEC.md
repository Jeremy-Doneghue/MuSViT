# Score codec prototype

`musvit-score-v1` translates a restricted MusicXML 4.0 score-partwise profile
into deterministic integer tokens and back into editable MusicXML. This is the
implemented first prototype approved after the [format analysis](TARGET_FORMAT_ANALYSIS.md).
It is independent of the old bekern loader and does not change the trainer.

## Use

```python
from experiments.full_page_omr.score_codec import encode, decode, encode_with_metadata
from experiments.full_page_omr.score_semantics import inspect_score

tokens = encode(source_musicxml)
decoded_musicxml = decode(tokens)
assert inspect_score(source_musicxml) == inspect_score(decoded_musicxml)

# Preserve this mapping alongside source/page/region evidence when exporting data.
record = encode_with_metadata(source_musicxml)
record.source_ids             # original XML IDs -> canonical local IDs
record.profile               # musvit-score-v1
record.vocabulary_sha256      # bind saved tokens/checkpoints to this vocabulary
```

These APIs take XML strings and return values; they do not modify source files.
`CodecError` reports unsupported notation, invalid timing/relationships, or a
malformed prediction. `decode()` expects Python integer IDs for one complete
sequence. Explicitly remove batch padding before calling it; missing EOS,
truncation, trailing tokens, invalid UTF-8 and noncanonical streams are errors.
The vocabulary has no unknown-word token and never reads a dataset to grow itself.

## Token and normalization contract

- 614 fixed tokens: PAD=0, BOS=1, EOS=2, profile marker, structural delimiters,
  element/attribute names, common literal values and all 256 UTF-8 bytes.
- Vocabulary SHA-256:
  `319f5494be4d9f9908c94896eddebbd77be66fa3f55059f24db9b6d638d0b5c9`.
  Vocabulary IDs are sorted/constructed from the profile, independent of Python
  hash seed or training/validation/test text. Changes require a profile/version
  decision before retaining trained checkpoints.
- Grammar: BOS, profile, one element tree, EOS. Each element has a structural
  start token, sorted attributes and their values, an attribute terminator,
  optional text, child elements in score order, and an end token. Values use a
  common literal or escaped UTF-8 bytes followed by a value terminator.
- Literal text such as `<eos>` remains text bytes, not a control token. Non-ASCII
  names, punctuation, newlines and leading/trailing instruction spaces survive.
- XML formatting whitespace is removed; leaf score values are trimmed. Mixed
  XML content is rejected rather than flattened. Optional source IDs are renamed
  deterministically and references rewritten, with the source-ID map retained.
  This does not synthesize IDs for every previously unlabelled event.
- Divisions, durations and direction/harmony offsets are normalized to the
  smallest common integer divisions per part using exact rational arithmetic.
  Staff/voice identity, written note type, dot count and time modification remain
  explicit. Event order is retained because backups/forwards determine time.
- XML serialization puts navigation attributes before other `sound` attributes
  to avoid a demonstrated Verovio 5.0 attribute-order bug. Attribute order remains
  lexicographic in the token grammar. This is a serialization compatibility rule,
  not a musical difference.
- This is restricted semantic normalization, not equivalence of every possible
  MusicXML spelling. It does not collapse all default/explicit fields, redundant
  attributes or arbitrary alternative event orders into one representation.

## Implemented subset

The explicit element/attribute allowlists live in [score_codec.py](score_codec.py).
Unknown elements and attributes fail, including engraving coordinates: the codec
never silently removes an unsupported feature.

Supported fixtures exercise:

- Document title, composer/arranger, rights, library reference and instrument label.
- Clef/key/time/transposition fields, printed measure labels and page/system flags.
- Written pitches and accidentals, rests, dotted/double-dotted durations, tuplets
  with explicit brackets, chord tones, independent voices and multiple staves.
- A voice beamed across staves, voice-specific ties, cross-page ties/slurs,
  glissando endpoints, fall articulation, accents and fermatas.
- Drum staff locations, normal/x noteheads and separate rhythmic voices. Named
  instruments are optional; literal instructions remain attached to their passage.
- Arbitrary directions/rehearsal text, metronome markings, dynamics, wedges and
  pedal endpoints; voice/staff and rational offset attachments are retained.
- Written multibar-rest, simile, slash and harmony structures already emitted by
  the synthetic generator. Their source representation is preserved, including
  underlying rests/notes; the codec does not replace the written markers with a
  playback expansion. Minimizing that redundancy for page targets is future work.
- Simple nonnested repeats, numbered endings and one D.S./coda route, including
  a normalized first-pass/second-pass example whose branches are on different pages.

The independent inspector in [score_semantics.py](score_semantics.py) checks raw
source timing before normalization: chord onsets, voice overlaps, measure extent,
type/dot/tuplet consistency, staff assignment, cursor bounds, tie continuity,
paired slur/glissando/tuplet/beam/control endpoints, instrument references and
bounded navigation. Tests assert known notes/onsets/endpoints/routes, not only
that encoding and decoding agree with each other.

## Fixtures and visual verification

Run the automated tests:

```sh
.venv/bin/python -m unittest tests.test_score_codec -v
```

Create a **new** review directory (existing output directories are refused):

```sh
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
MPLCONFIGDIR=/private/tmp/musvit-matplotlib \
.venv/bin/python -m experiments.full_page_omr.codec_fixtures \
  --output experiments/full_page_omr/outputs/codec_review_NEW --png
```

The environment settings above match the local macOS renderer setup. `--png` is
optional. Outputs contain source/decoded MusicXML, tokens with vocabulary/profile
and ID mapping, semantic summaries, source/decoded SVGs and optional PNGs, plus
the vocabulary and a summary report. Source files are original synthetic fixtures;
no real scans or user annotations are embedded. Generated artifacts stay ignored.

PNG review uses the existing text-outlining helper with packaged DejaVu Serif and
Verovio's embedded music text fonts, avoiding unavailable system music fonts.
Prose previews use regular outlines; saved MusicXML preserves supported style
attributes. Original generated horn fixtures also use the existing checked
single-staff MEI normalization, which is not applied to piano/drum fixtures.

Executed review on 2026-10-31 with Verovio `5.0.0-b3f7bc6`:

| Fixture | Tokens including BOS/profile/EOS | Notes/rest events | Pages |
| --- | ---: | ---: | ---: |
| Horn: double dot, tuplet, spans and text | 1090 | 8 | 2 |
| Piano: chord and independent voices | 610 | 5 | 1 |
| Cross-staff beamed voice | 620 | 6 | 1 |
| Drums: appearance and passage instructions | 775 | 7 | 1 |
| Pass-specific alternatives | 1067 | 10 | 2 |
| Existing seed-7 repeat regression | 4938 | 89 | 3 |
| Existing seed-7 endings regression | 5008 | 89 | 3 |
| Existing seed-7 D.S./coda regression | 5018 | 89 | 3 |

All eight fixtures retained inspected score semantics and expected performed
measure routes. All 16 source/decoded rendered page pairs matched pixel-for-pixel
at 900 pixels wide. Inspected decoded previews of all pages, including the cross-
page phrase, tuplets, drum instructions and both conditional passages. This checks
round-trip preservation with this renderer, not perfect source engraving or
score-editor interoperability. The actual Charmaine score was not transcribed.

Final local artifacts: `outputs/codec_validation_v1_20261031_03/`. Earlier `-01`
and `-02` directories are retained development attempts, not final review output.
The first exposed the sound-attribute-order issue. A later visual review exposed
an empty page when Verovio split a single ending across pages; the final fixture
places page breaks between alternatives and tests cross-page spans in the horn
fixture instead. Splitting inside an ending remains a renderer limitation to test.

## Limits and next step

This is not a full MusicXML schema validator, general playback engine, OMR model
or page assembler. The v1 profile rejects DTDs/entities, namespaces, comments,
mixed rich text, grace notes, microtones, unlisted ornaments/layout fields,
span continuation/change forms, nested repeats, combined repeat+D.S. navigation,
and open/partial score fragments. It requires initial meter/divisions and complete
measures (or an explicitly implicit pickup), positive integer voice labels and
pitch alterations limited to integer -2..2. Special notation outside the allowlist
must be added with tests and a version decision, not passed through silently.

Some allowlisted structures are retained without exhaustive semantic validation;
for example this inspector does not prove all simile underlying-note relationships
or every MusicXML enum/schema constraint. The old generator's validators remain
in force for its source scores. No constrained incremental neural decoding or
error-repair policy is implemented.

Source-ID maps support linking evidence but do not constitute a complete region,
clipping/inference or historical-layout sidecar. Blank manuscript staves and
uncertain clipped content are recognition/annotation cases, not invented events
in these synthetic round trips. Instrument-change words/transposition fields can
be retained; arbitrary playback instrument-change structures are outside v1.

Follow-up: the user approved the [single-page overfit pilot](OVERFIT_PILOT.md).
It now exports complete, self-contained single-page scores, has a local adapter
and successfully overfits eight tiny clean examples. This does not implement
continuation-page targets or multi-page assembly. Measure realistic target lengths
before choosing a general model limit; these tiny/full-part fixtures are not a
page-length benchmark. No notation-editor import has been performed.
