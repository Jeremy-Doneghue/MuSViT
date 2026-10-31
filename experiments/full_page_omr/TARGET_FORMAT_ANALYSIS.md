# Target-format analysis — 2026-10-31

Implementation update: the user subsequently approved the prototype. See
[SCORE_CODEC.md](SCORE_CODEC.md) for the implemented v1 contract, executed fixtures
and remaining limits. The analysis below records the preceding recommendation
and audit evidence; its statements about unimplemented work refer to that stage.

## Recommendation

Do not use the current bekern training targets as the complete transcription
contract. Retain that pipeline as a baseline. For the new pipeline, prototype a
versioned, compact tokenization of a defined MusicXML semantic profile, retaining
an editable MusicXML score plus source evidence. This is a recommendation, not
an implemented tokenizer or a demonstrated learning result.

This choice is about the score vocabulary and conversion contract. The existing
autoregressive decoder can emit a different vocabulary; a new neural architecture
is not necessary just to change the target language. Token embeddings/output
weights and their vocabulary mapping will need deliberate initialization.

User clarification after this audit: named drum-instrument/playback mappings are
optional for the intended output. Preserving readable notation and arbitrary
passage instructions is sufficient; verified standardization is acceptable too.
The observed mapping loss below remains a conversion finding, but is not by
itself a blocker or a reason to reject a format. Primary drum acceptance checks
are noteheads, staff positions, rhythms/voices and text with meaningful scope.

MusicXML is recommended for the first interchange/export implementation because
our generator already produces it, and its specification supplies structures for
the required percussion, voices, directions, credits, and navigation. This does
not mean asking the model to reproduce arbitrary XML, application formatting,
random IDs, engraving coordinates or whitespace. MEI remains a credible alternative,
especially if preserving the historical source layout becomes a primary goal.

The decisive distinction is between the full Humdrum format and our cleaned,
closed-vocabulary bekern pipeline. The latter has demonstrated information loss.
This audit does not establish a fundamental inability of Humdrum to encode the
collection, nor prove that a MusicXML-derived tokenizer learns better.

## Evidence and reproduction

Code inspected: [data.py](data.py),
[SynthGenerator.py](Generator/SynthGenerator.py),
[vocab_utils.py](utils/vocab_utils.py), [smt_trainer.py](smt_trainer.py),
[modeling_smt.py](smt_foundation/modeling_smt.py),
[musicxml_score.py](musicxml_score.py), [generate_parts.py](generate_parts.py)
and [scenarios.py](scenarios.py). Visual requirements/examples are recorded in
[TARGET_COVERAGE.md](TARGET_COVERAGE.md).

Executable audit:

```sh
.venv/bin/python -m experiments.full_page_omr.audit_target_format
```

Optional native converter probe (isolated in a subprocess because it can abort):

```sh
.venv/bin/python -m experiments.full_page_omr.audit_target_format --include-humdrum-converter
```

`--output NEW_FILE.json` saves diagnostics and refuses an existing file. Parser
functions are compiled unchanged from their source ASTs to avoid initializing
datasets, ImageMagick and the training stack. Fixtures are original synthetic
micro-scores, not scan transcriptions. JSON records parser-source/vocabulary
hashes and the installed Verovio version. These diagnostics are not a dataset
export or a production tokenizer. Reports from this session are in
`/private/tmp/musvit-target-audit-20261031-03.json` (final), with earlier probes in
the corresponding `-01.json` and `-02.json` paths;
temporary reports are not durable project history.

### Executed parser and vocabulary findings

Nineteen probes exercised the current source function bodies:

- Bar numbers 12 and 99 produce identical labels: a regular expression deletes
  digits immediately following `=`. Printed numbering cannot be recovered.
- Staff, pedal, cue, tuplet-display and rhythmic-scale interpretations are
  deleted by the cleaner. It deletes the entire row: a clef change in a second
  spine disappears when the first spine has a pedal instruction.
- The parser removes the first four space-separated fields positionally. This
  fits a specific two-spine header, removes the meter in a single-spine fixture,
  and leaves part of a three-spine header in the target. A leading title record
  also changes which fields are removed. Arbitrary metadata is not safely handled.
- With no final newline, `parse_kern_file()` drops the final spine terminator;
  trailing-newline presence changes targets.
- Positive controls: chord separators, double dots, split/join markers and null
  events survive. A simple marker-free two-spine chord fixture reconstructs its
  original Humdrum text exactly. This is narrower than full score fidelity.
- Saved vocabularies have 181 (GrandStaff), 191 (Mozarteum), and 215 (Polish
  Scores) entries. All contain split/join tokens. None contains the literal
  instruction `BRUSHES`; current dictionary lookup has no arbitrary-text fallback.
  Absence of a single token does not prove that the underlying format lacks text.
  Mozarteum contains staff tokens despite current cleaners removing them; saved
  vocabulary contents alone do not establish active parser coverage.

Inspection also found that the generator prepends exactly two `**kern` spines,
selects excerpts by two terminators, and can render an added random title without
including that title in the returned target. The vocabulary builder enumerates
an unsorted set, and data modules pass train/validation/test targets into vocabulary
construction when no saved dictionary is found. The new adapter must avoid these
assumptions and must define deterministic IDs without held-out transcription input.

### Executed conversion findings

Installed renderer: Verovio `5.0.0-b3f7bc6`.

1. An original two-staff MusicXML fixture imported directly to MEI with three
   layers, five notes, a chord, fall articulation, slur, fermata, rehearsal mark,
   tempo, dynamic, hairpin and two pedal events. Title, composer text and rights
   text survived (composer is a `persName`, not a `composer` element). This checks
   selected structures/values, not every duration, attachment or visual result.
2. A percussion fixture retained two layers, unpitched staff locations, an x
   notehead and the instruction `BRUSHES`. However, the source's two named
   score-instruments and note-to-instrument references were absent from the
   inspected MEI: there were no instrument metadata elements or note instrument
   references. This is not a blocker under the user's clarified drum requirements.
   Keep the original semantic score; do not treat renderer-converted MEI as a
   lossless canonical training source.
3. A two-staff Humdrum fixture containing a chord and unequal-duration voices
   imported successfully. After current tokenization and text reconstruction,
   the staff/event fingerprint matched, including staff/layer assignments,
   notes and durations. Generated IDs and bar numbering are excluded. This
   supports basic polyphonic use of the existing path; it does not test
   navigation, percussion identity, cross-staff beams, or arbitrary text.
4. The alternate `musicxml-hum` importer aborted on the piano fixture with
   inconsistent-field diagnostics and an uncaught native `std::length_error`
   (return code -6 in the isolated probe). An earlier regression-score probe
   also terminated natively. This is a local conversion-path failure, not a
   conclusion about representational capacity. No dependency upgrade attempted.

The existing `check_conversion()` explicitly checks the synthetic single-staff
subset. It sums note durations within each measure, which is inappropriate for
overlapping voices. It cannot certify the piano/drum/alternative-layout cases.
The trainer currently measures transcription string errors; it does not establish
valid score reconstruction, percussion mapping or correct navigation.

## Coverage comparison

Status refers to this repository, not every implementation of a standard.
"Retained" means a narrow executed probe; "unverified" is not "unsupported".
The MusicXML column identifies candidate standard structures, not a working
exporter or successful score-editor interoperability test.

| Requirement | Current pipeline / evidence | Candidate MusicXML semantic structure |
| --- | --- | --- |
| Chords and independent voices | Chord/split/join controls retained; restricted polyphonic reconstruction passed | `chord`, `voice`, `staff`, `backup`/`forward`; independent voice/staff identities |
| Piano, cross-staff notation, pedal | Two-spine assumptions; pedal/staff controls erased; cross-staff fidelity unverified | Multiple staves, voice and staff per event, beams, pedal directions; cross-staff fixture still needed |
| Dots and double dots | Double-dot token retained; no new full rhythmic round trip | `type`, repeated `dot`, exact `duration`; tuplets retain time modification/display separately |
| Falls / glissandi | Full kern documents glissandi; fall distinction unverified in current targets | `falloff`, `glissando`/`slide`, paired endpoints; fall retained in direct-import probe |
| Numeric/letter rehearsal marks | New generator emits marks; legacy target/export path unverified | `rehearsal` text at musical position; letter A retained in direct probe |
| Printed bar-number references | Digits stripped from bar tokens | Measure identity separate from display numbering; `measure-numbering` and explicit text where needed |
| Title, arranger, composer | Added generator title can be image-only; leading metadata breaks header skip | `work`, `identification/creator`, `credit` with original text/role |
| BPM, swing | Generator can carry words; legacy vocabulary/semantic export unverified | `metronome`, `words`, `sound tempo`, swing; distinguish printed unit/value from playback tempo |
| Instrument labels | Two-spine header does not establish instrument identity or arbitrary label support | `part-name`, abbreviation and `score-instrument`; retain original wording |
| Double barlines | Kern has barline syntax; user-case export unverified | `barline/bar-style`, independent of rehearsal marks and navigation |
| Pauses / fermatas | Full kern has pause syntax; current user-case attachment unverified | `fermata`, breath/caesura articulation or original instruction as appropriate |
| Tacet | Arbitrary text lookup is inadequate; scope unverified | `words` plus explicit/resting measures where known; preserve text without inventing scope |
| Library numbers / copyright | No general document-metadata target contract | Credits, identification/rights, typed miscellaneous metadata; retain visible text too |
| D.S. al coda | New generator/checks support a restricted route; legacy token/export route unverified | Printed marks/words plus named `sound` navigation; check actual traversal |
| Dynamics / hairpins | Restricted generated dynamics checked; full target path unverified | `dynamics`, paired `wedge`, staff/voice/offset; structures retained in direct probe |
| Rall. / rit. | No open text contract | Original `words`, optional span/dashes; do not invent a numeric tempo curve |
| Charmaine alternatives | No fixture or validated assembler/exporter; brace alone ambiguous | Normalize verified alternatives to pass-specific sections/endings; keep source grouping separately; exact historical layout unverified |
| Drum notation | No new drum generator; notehead/location and BRUSHES text survive direct probe; named mappings lost but optional | `unpitched`, `notehead`, voice and scoped text; optional score-instrument references; preserve source appearance unless standardization is verified |
| Blank staves after ending | Input/structure problem; no demonstrated end detection | No extra measures for blank paper; EOS after actual content, backed by region evidence |
| Instrument changes | Not represented by new generator's fixed instrument; legacy export unverified | Original instruction, instrument references/changes, clef and transposition state |
| Instructions anywhere | Token text and attachment not specified | `direction/words`, offsets, staff/voice; preserve page-region evidence if attachment unclear |
| Cues | Cue controls erased | `cue`, size/display and source-instrument text; preserve cue/main-voice distinction |
| Clipped but inferable content | No uncertainty/provenance contract | Inference provenance outside core interchange, linked to events; mark unresolved cases for review |
| Similes, multirests, slashes, chord symbols | New generator has subset checks, no new-target adapter | `measure-repeat`, `multiple-rest`, slash style/noteheads, `harmony`; retain written abbreviations |

The old charts expose a distinction that applies to every candidate: a visual
staff is not necessarily a concurrent voice. Charmaine's user-confirmed
alternative passages need pass conditions. An ossia indicating performer choice
is not automatically equivalent. Sequential pass-specific sections are a proposed
normalized export; preserving the exact stacked historical layout needs a separate
engraving test. Do not claim standard ending support alone proves that layout works.

## Alternatives and tradeoffs

| Candidate | Why consider it | Main cost / risk | Recommendation |
| --- | --- | --- | --- |
| Existing cleaned bekern | Small vocabulary, working neural path, narrow polyphony controls pass | Demonstrated losses; fixed headers; incomplete text/export contract | Keep for comparison, not the complete new output |
| Broader Humdrum with robust tokenizer | Documented polyphony, text/dynamic spines, section/strophe/repeat mechanisms | Need new parser/serialization profile, text fallback, extension/render/export validation; local converter failed | Viable challenger, not rejected as incapable |
| Arbitrary raw MusicXML tokens | Direct standard structures and source data | Many equivalent encodings, verbose syntax and application layout noise | Do not train on arbitrary editor output |
| Normalized MusicXML-derived token profile | Existing source; standard score meanings; direct export path | Profile, codec, semantic validators and sequence-length measurements still needed | Preferred first prototype |
| Normalized MEI-derived profile | Existing renderer; explicit staff/layer/control-event structures and rich source description | Current MusicXML import loses some information; current normalization is single-staff-specific; editor export still needs validation | Strong alternative if source-layout fidelity drives the design |
| Entirely new event/graph language | Can directly express uncertain regions and alternative branches | We would own all score semantics, validation and export mappings | Avoid a broad new score standard; keep only needed source-evidence extensions |

No token-count or training-speed comparison has been measured here. Existing
vocabulary size does not equal sequence length, and a smaller alphabet does not
prove a better learning target.

## Concrete proposed contract and first experiment

Use MusicXML semantics for document/part/measure, written pitched or unpitched
events, independent voices/staves, durations, notation, directions and navigation.
Specify one serialization order and exact rational timing; keep duration, written
note type/dots and tuplet information consistent. Generate canonical local IDs
for relationships rather than learn arbitrary source IDs. Exclude renderer-only
coordinates from musical labels while retaining necessary display facts such as
notehead shape, cue size, accidental display and cross-staff assignment.

Define structural tokens for the profile's elements/attributes and encode
unrestricted text with an explicit escaped UTF-8 byte fallback or another fixed
text codec. Names and instructions must not require new vocabulary entries for
each word. Fix vocabulary IDs deterministically from the format, with reserved
BOS/EOS/PAD; test literal delimiter text, non-ASCII names and unseen instructions.
Byte fallback is a proposed initial mechanism, not a trained tokenizer result.

Maintain linked source evidence for page/system/staff regions, observed text,
alternate staff roles, and clipped/inferred content. Keep these distinct from
musical voices and performance order. A sidecar initially suffices; this analysis
does not require multiple models or a graph neural decoder. Page-local outputs
need explicit inherited context and unresolved cross-page references for assembly.

Before training, implement and inspect round trips for:

1. A simple horn page with dots/double dots, dynamics, rehearsal marks and text.
2. Piano with a chord and independent same-staff voices, ties, rests and pedal;
   then a separate cross-staff case.
3. Percussion with mixed noteheads, simultaneous voices and arbitrary scoped
   instructions. Re-engrave source positions/heads or a verified standard mapping.
   Named sound mappings are optional; do not silently invent unresolved identities.
4. Written similes/multirests/slashes, repeats/endings and D.S./coda traversal.
5. A small original Charmaine-like conditional-passage fixture spanning pages,
   with known pass assignments, distinct from simultaneous staves and free-choice
   ossia. Later annotate the actual example against the full source.
6. Headers/footers and an unseen instruction/name; blank trailing staves and
   clipped edges as recognition/evidence cases rather than invented score events.

Reject unsupported constructs explicitly. Compare decoded score structure,
onsets/durations, attachments, drum notation/text, written abbreviation counts,
text and traversal; render and inspect, then import into a notation editor.
This audit has not performed the editor/re-engraving acceptance step. Measure
target lengths after the codec exists before setting a decoder length limit.

Only then run the proposed clean 1-page debug fit and 8–16-page overfit with piano
and drum examples included. Use batch size 1 initially, disable augmentation and
teacher-forcing token corruption, and start with the frozen encoder. Check
autoregressive output validity and semantic accuracy, EOS/truncation, runtime and
memory. Do not expand the generator or launch training as part of format analysis.
Keep reviewed real development scans distinct from reserved evaluation scans;
this conversation's inspected examples are development material.

## Primary references checked

- [Humdrum kern](https://www.humdrum.org/rep/kern/): notes, dots, chords,
  articulation, glissandi and pause syntax; these capabilities exceed our cleaner.
- [Humdrum nonlinear structures](https://www.humdrum.org/guide/ch20/): section
  labels, expansion lists and strophic alternative paths. Therefore repeat and
  alternative support is not unique to MusicXML.
- [MusicXML voice](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/voice/)
  and [backup](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/backup/):
  independent lines and musical-position movement.
- [MusicXML percussion](https://www.w3.org/2021/06/musicxml40/tutorial/percussion/):
  display location, noteheads and multiple named instruments per part.
- [MusicXML directions](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/direction/)
  and [credits](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/credit/):
  musical versus document-level indications.
- [MusicXML endings](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/ending/)
  and [sound](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/sound/):
  pass conditions and navigation parameters.
- [MusicXML falloff](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/falloff/)
  and [measure-repeat](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/measure-repeat/):
  distinct written notation rather than inferred playback notes.
- [MEI common notation](https://music-encoding.org/guidelines/v5/content/cmn.html):
  staff/layer/control events, cues and ossia; performer-choice ossia should not be
  conflated with mandatory pass-specific alternatives.
- [Verovio input formats](https://book.verovio.org/toolkit-reference/input-formats.html):
  direct MusicXML and MusicXML-through-Humdrum are separate conversion paths.

Standards describe available structures. Executed probes above describe the
installed implementation. Neither alone establishes end-to-end OMR performance.
