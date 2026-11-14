# Humdrum recognition scope

Decision recorded 2026-11-14. The user approved revisiting the recognition goal
around kern/Humdrum, then selected these first-milestone requirements:

- Pitched single-staff parts, piano polyphony **and percussion**.
- Common dynamics **and performance text from the start**.
- Transcribe supported content and flag omissions for review, rather than
  abandoning an entire passage because it contains an unsupported feature.

The goal is editable, re-engraveable notation within an explicit tested profile.
The model-target direction is normalized Humdrum centered on **kern, with
established dynamics/text/percussion conventions. Humdrum is also the canonical
musical source; MusicXML is optional at import/editor boundaries. The
[direct-source preview pipeline](HUMDRUM_PIPELINE.md) is implemented. Imported-score
normalization and new model training remain pending. Historical pilot artifacts stay intact; the retired code is available in Git.
Compatibility with early targets/checkpoints is not required.

## What belongs in the first milestone

| Area | Required behavior | Current acceptance status |
| --- | --- | --- |
| Pitched parts | Written notes/rests, accidentals, clefs, keys/meters and exact rhythms; preserve written versus sounding pitch through instrument transposition | Existing source fixtures; full Humdrum fidelity unverified |
| Piano | Chords, independent voices and multiple staves; voice-specific ties/slurs; readable staff relationships | Native preview chords/voices/staff/pedal counts checked; comprehensive timing/span fidelity remains pending |
| Percussion | Preserve readable note positions, noteheads, rhythm, voices and passage instructions; named playback mappings remain optional | Native previews check x-head counts and preserve both passage instructions; general imported percussion fidelity unverified |
| Dynamics | Common symbols and hairpins with staff/voice attachment and span | Dynamics spine, one dynamic and one hairpin present in the horn smoke output; fidelity unverified |
| Performance text | Preserve original words, Unicode/punctuation, musical attachment and passage scope where ascertainable | Native generation retains exact tested instructions; old converted horn fixture still loses text |
| Rhythmic notation | Dots, tuplets, ties and beams; retain distinctions between written notation with equal sounding duration | Representative source fixture; counts only inspected after conversion |
| Structure | Preserve supported barlines/repeats/endings in written order; explicit decisions for navigation and abbreviations | Humdrum path not yet tested |
| Output | Editable standard notation with a visible, separate omission/review report | SVG/MEI and exact source exported/restored; editor interoperability unverified |

No 32nd-note cutoff was selected: that was discussed as a possible simplification,
not agreed as a restriction. Do not round or silently simplify finer values.
Print/scan/handwriting remain input-domain goals; support in the output language
is separate from demonstrated recognition in any of those domains.

## Candidate conventions and normalization

Use established Humdrum/Verovio conventions instead of inventing new syntax:

- **kern for musical events and voice structure; explicit spine interpretation,
  split/merge/null rules without assumptions of exactly two staves.
- **dynam for dynamics. Performance directions use supported text layout comments
  such as `!LO:TX:`; **text is a lyric spine, not automatically a substitute for
  arbitrary scoped performance instructions.
- Percussion clefs/unpitched markers, staff positions and notehead conventions
  supported by the chosen importer/renderer. Confirm their conversion explicitly.
- Required metadata/reference records and layout comments remain part of the
  profile when they carry target content. Never indiscriminately strip comments.

Normalize property order inside tokens, chord member order, spine/staff/voice
ordering, equivalent rhythmic spellings and partial-voice split/merge conventions.
Pin a deterministic choice for each before training, and check equivalent scores
converge. Preserve displayed accidentals, beaming and other retained visual
features; do not inherit a paper's target deletions merely because it uses kern.
Permit arbitrary retained text through a compositional tokenizer with a fallback;
do not recover the old closed-vocabulary cleaner or build vocabulary from held-out
labels. Standardize written/sounding pitch once, including transposing instruments.

These are design requirements, not a completed tokenizer/normalizer. The precise
profile is gated on conversion, rendering and editor-export fixtures. Papers use
different cleaned subsets: using Humdrum does not make our targets or metrics
identical to theirs.

Primary references:
[core kern](https://www.humdrum.org/rep/kern/),
[notation, dynamics, text directions and transposition](https://doc.verovio.humdrum.org/humdrum/getting_started/),
[percussion](https://doc.verovio.humdrum.org/humdrum/percussion/).

## Omissions and review

Known unsupported features must be recorded separately with feature, source/page
or measure context where known, reason and review status. Outputs with omissions
must be presented as partial, not a complete faithful transcription. Keep original
source files and scan evidence. Do not alter supported durations, voices or
navigation to hide an omitted feature. If unsupported content prevents a coherent
partial score, mark the affected region unresolved rather than fabricate it.

For synthetic/source-backed examples, a coverage audit can identify known omitted
source features. For real scans, a reliable detector of arbitrary unsupported
notation does not yet exist: a general scope warning and manual review are needed
until region-level detection is validated. Do not claim all omissions will be
located automatically by the recognizer.

Jazz falls, glissandi, chord symbols, improvisation slashes, similes, multibar rests,
D.S./coda, cross-staff notation and unusual repeat alternatives need dedicated
acceptance fixtures. Their status is unverified, not inherently unrepresentable
and not an agreed blanket exclusion. Exact historical page layout is distinct
from readable, standardized re-engraving. Retain the older
[collection inventory](TARGET_COVERAGE.md) as the review checklist.

## Historical conversion smoke audit

The results below were recorded before direct Humdrum generation replaced the
conversion path. The audit script depended on retired MusicXML fixtures and was
removed with that stack. Retrieve it at Git commit `1b57dfe`; the following was
its historical command, not a current entrypoint:

```sh
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
.venv/bin/python -m experiments.full_page_omr.diagnostics.humdrum_scope_audit
```

The library-path setting is the existing local macOS setup. Each fixture runs in
an isolated process with a 15-second timeout and core dumps disabled. The command
prints summary counts only; no labels/scans/weights are written to documentation
or exported. Exit zero means the probes ran, not acceptance of the notation.

Executed 2026-11-14 using Verovio 5.0.0: load source with `inputFrom=musicxml-hum`,
read `getHumdrumBuffer()`, load that buffer with `inputFrom=humdrum`, then inspect
`getMEI()` element counts/text. Three original programmatic fixtures:

| Fixture | Conversion/reimport | Selected observations |
| --- | --- | --- |
| Horn | Both succeed; 370 UTF-8 bytes; one initial kern spine | 7 notes + 1 rest, 1 dynamic, hairpin, slur, tie and tuplet in returned MEI. Two text-layout comments in Humdrum, but neither complete source instruction found in MEI text. Source has two glissando endpoint markers; returned MEI has no gliss element. |
| Piano | Both succeed; 287 bytes; two initial kern spines and voice split | 5 notes + 1 chord in returned MEI. Neither of two source pedal markers represented as pedal elements. |
| Drums | Both succeed; 308 bytes; one initial kern spine and voice split | 6 notes + 1 rest and both source instructions found in returned MEI. Notehead/position and attachment fidelity still untested. |

These are smoke observations only. Counts/substrings do not prove pitch, timing,
attachment, rendering or editor fidelity; marker counts are not equivalent to
musical event counts. The earlier 2026-10-31 native failures were not reproduced
on these three probes today; no converter patch or dependency upgrade was made.

Follow-up pedal isolation (2026-11-14): documented `*ped` (down) and `*Xped`
(up) are supported in kern spines. A minimal directly encoded Humdrum example
loads in local Verovio 5.0.0 and produces two MEI pedal elements, with `dir=down`
and `dir=up`. The converted piano fixture contains no pedal-related tokens.
This localizes that fixture's loss to MusicXML-to-Humdrum conversion, rather
than pedal syntax or the basic Humdrum importer. It does not certify pedal line,
change/half-pedal, placement or export coverage. See
[the pedal documentation](https://doc.verovio.humdrum.org/humdrum/pedal_marks/).

Dependency inspection: Verovio 5.0.0 is installed; music21/converter21 are absent;
standalone musicxml2hum/hum2xml/hum2mei commands were not found on PATH. This does
not establish that no other converter binaries exist elsewhere on disk. No
upstream Transcoda converter was installed or executed.

## Next concrete implementation

Update after the direct-source preview change: authoring Humdrum directly removes
the MusicXML converter from new curriculum previews. The conversion gaps below
remain relevant to optional imports, not a prerequisite for native generation.
The current next action is broader scoped-notation validation and a Humdrum
training adapter; see [the implemented pipeline](HUMDRUM_PIPELINE.md).

Earlier conversion-focused plan (retained for optional import work):

Investigate text escaping/attachment, pedal and glissando conversion on minimal
fixtures. Select or repair the converter using these acceptance checks, including
a tested editor-export route. Then extend the feature sheet to cross-staff notes,
transposing parts, percussion noteheads, repeats and jazz notation. Compare exact
musical events/relationships and rendered notation, not counts alone. Freeze the
normalization/tokenization contract after that evidence, then expose the actual
Humdrum target beside its image in Curriculum and create a fresh training export.
No new training run is selected or launched by this scope decision.
