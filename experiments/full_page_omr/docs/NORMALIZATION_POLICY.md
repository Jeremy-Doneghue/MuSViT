# MusicXML target normalization policy

2026-11-14 update: the selected next model-target direction is now
[normalized Humdrum](HUMDRUM_SCOPE.md). This document records the earlier
MusicXML-target design and audit. Its preservation/normalization principles remain
useful, but implementing all six MusicXML serialization gaps is no longer the
immediate target work.

Recorded 2026-11-13 following the Transcoda discussion. The user selected staying
with MusicXML and specifying normalization/acceptable omissions. The concrete
rules below are the recommended implementation contract; the audit below checks
the existing codec, which does not yet implement all of them. Existing early
training exports/checkpoints are disposable: no migration or compatibility layer
is required. No new dataset or training run is part of this work.

## Boundary

Keep the original MusicXML unchanged as source evidence. Derive a canonical
MusicXML recognition target and its model tokens, with a machine-readable record
of applied rules and omissions. MusicXML interchange and the current integer
codec remain distinct from asking a model to emit arbitrary editor XML.

Normalize alternative encodings of the same written notation. Preserve notation
that changes what the musician reads, even when playback is identical. A quarter
note is not two tied eighths, C-sharp is not D-flat, and independent voices are
not a chord. Do not infer absent markings or repair contradictory scores.

Validate source timing and references before normalization, then validate the
result again. Unknown/unclassified features must produce an explicit rejection
or coverage report; permission to omit a named feature is not permission to strip
arbitrary unsupported XML. Originals must never be rendered with extra target
notation silently missing: render the normalized target or explicitly record the
intended image/target difference.

## Canonicalize

| Feature | Rule | Current codec |
| --- | --- | --- |
| Timing | Interpret durations, offsets and cursor movements using exact rational quarter-note units under the active divisions value. Never round. | Implemented for supported inputs. |
| Divisions | Choose one integer divisions value per part: LCM of reduced denominators of all retained durations, offsets and cursor movements. Emit it once in the first measure's attributes; remove later divisions declarations and empty attributes containers. Rebuild cursor movements before choosing the scale. | Scale normalization exists; redundant declarations remain. |
| Chord members | Sort pitched members by written octave, diatonic step C–B, then alteration. Preserve member-specific staff, accidental, tie, cue, notehead and articulation data. Equal-key members use retained note content as a deterministic tie-breaker. Regenerate chord markers. | Source order retained. |
| Unequal chord durations | MusicXML requires the advancing anchor to be at least as long as other members. Choose a longest-duration member as anchor, breaking ties by written pitch; sort remaining members by written pitch. Never shorten, split or merge notes to obtain pitch order. | Not normalized. |
| Independent voices | Resolve absolute onsets before reordering. Emit whole voice streams in numeric voice-ID order, events by onset, retaining chord groups. Derive the required backup/forward movements from exact cursor state; preserve voice identity across measures and cross-staff movement within a voice. | Source serialization retained. |
| Directions and harmony | Resolve onset, voice/staff scope and span endpoints before moving anything. Emit anchored directions/harmony in a deterministic measure prefix with absolute offsets from measure start, after initial attributes. At a shared onset use staff, explicit voice scope, element family and retained content as the sort key. Resolve same-number span stop/start order explicitly. | Source cursor placement retained. |
| Equivalent defaults | Omit pitch `alter=0`, note `print-object=yes`, measure `implicit=no`, zero offsets, and default span `number=1` where the MusicXML default and our semantic interpretation agree. Preserve their nondefault forms. Do not generalize this to unspecified engraving defaults. | These equivalent spellings mostly remain distinct. |
| Numeric spellings | Canonical integers for integer fields; exact canonical decimal spelling for accepted decimal fields. Do not apply numeric conversion to printed text such as measure labels, rehearsal marks or tempo words. | Timing is canonical; other integer spellings are largely retained. |
| IDs | Assign deterministic required IDs after event ordering. Omit unreferenced optional event IDs from the target; retain a source-to-target map outside it. Rewrite every retained reference; never discard a referenced endpoint. | Present IDs renamed in original traversal order; presence remains significant. |
| XML syntax | Remove formatting whitespace; sort attributes; follow schema child order. Preserve free-text characters, punctuation, case and deliberate whitespace. | Implemented for the restricted profile. |

Voice serialization is ordered by voice identity, not by staff: a voice may cross
staves. Renumbering arbitrary voice labels into a unique identity is deferred;
consistent relabelling across measures/spans needs its own rule. Likewise,
unpitched chord ordering needs a staff-position/notehead contract. Do not pretend
these rules establish a unique form for every possible MusicXML score.

Reordering must operate on parsed events and relationships, not a sort of XML
children. Preserve the written pitch and transposition separately. Span references
must remain attached to the same musical events after note/chord ordering.
Unsupported mid-measure attribute changes remain explicit coverage gaps until the
parser understands their timing; do not move them to the measure start.

## Preserve

- Written pitches and enharmonic spellings, displayed accidentals including
  courtesy/editorial/parenthesized signs, clefs, keys and transposition.
- Written note values, dots, tuplet ratios and display, ties, slurs, beams,
  articulations, stems, noteheads, cue status and staff/voice relationships.
  Equal sounding duration alone is insufficient to declare equivalence.
- Dynamics, wedges, pedal, chord symbols, lyrics when supported, rehearsal marks,
  tempo/swing/passage instructions and their scope. Text is notation, not a
  distractor merely because it is not a note.
- Repeats, endings, D.S./coda, navigation references, multibar rests, similes and
  slashes. Preserve written abbreviations rather than expanding playback.
- Printed measure labels, titles, instrument labels, composer/arranger, rights
  and visible library references. Hidden source metadata remains in the original.
- Explicit visibility suppression such as `print-object=no` until a dedicated
  written-only simplification proves that timing and references survive.

## Omit from the recognition target

These are proposed named omissions, not currently implemented import support:

| Feature | Treatment and condition |
| --- | --- |
| Editor/software/export metadata | Omit software names/versions, export dates and editor bookkeeping; retain source provenance externally. Do not remove creator, rights or printed credits with them. |
| Absolute engraving coordinates | Omit editor x/y positions, page dimensions and numeric margins. Retain semantic staff/voice assignment, attachment and above/below placement. Exact historical layout is outside this target. |
| Automatic page/system breaks | Omit engraving break hints. Keep actual input-page boundaries, continuation context and source grouping in the page assembly contract; never merge conditional/alternative passages as a layout simplification. |
| Playback-only settings | Omit MIDI program/channel, velocity and humanization; omit standalone playback tempo values from the recognition target. Preserve printed tempo/metronome content and navigation-bearing `sound` fields. Do not remove a whole `sound` element merely because it also contains tempo. |
| Unprinted analytic metadata | Omit only explicitly classified source-analysis fields, retaining the original. Unknown miscellaneous fields must be reviewed, not presumed invisible. |

No omission of readable musical content is selected by this policy. Additional
coverage reductions should name the feature, reason, lost capability and affected
source count before applying them. Contradictory accidentals, invalid rhythms,
missing endpoints and clipped/uncertain notation require rejection or a separate
review task, not normalization by guessing.

## Executed audit of the current codec

Run without a renderer, data export or model:

```sh
.venv/bin/python -m experiments.full_page_omr.diagnostics.normalization_audit
```

The command reports only named cases, token counts and outcomes. Exit 1 means
policy gaps/lost distinctions, exit 2 an invalid probe, and exit 0 full agreement
on these fixtures. A gap is an observed missing normalization, not a passing test
of the proposed implementation. All inputs are original programmatic fixtures.

Executed 2026-11-13: 15 paired cases; 9 satisfied, 6 normalization gaps,
0 lost distinctions, 0 probe errors. Every case also passed token round trip and
canonicalization idempotence checks.

| Check | Result |
| --- | --- |
| Uniform division rescaling; renamed IDs/attribute order | Equivalent tokens, as required (2 cases). |
| Later equivalent divisions declaration | Different tokens (1090 versus 1099); numerical timing converges but declaration structure does not. |
| Reordered chord members; reordered independent voices | Different tokens (2 cases). |
| Absent versus explicit zero alteration; default note visibility | Different tokens (2 cases). |
| Same direction onset expressed at different cursor locations | Different tokens. |
| Courtesy accidental; chord versus independent voices; whole note versus tied halves; enharmonic spelling; passage text; rehearsal mark; dynamics | Distinct tokens retained (7 cases). |

These checks do not prove general semantic equivalence or visual identity. They
use deliberately constructed equivalent/different pairs, validated by the current
semantic inspector. No score-editor import or renderer comparison was executed.
The existing inspector includes serialization order in its summaries; testing a
future reorderer needs comparisons keyed by musical event/endpoint identity,
rather than equality of source-order event arrays.

## Next implementation action

Apply exact timing/default/declaration normalization directly to the current
codec, then implement event-based chord/voice/direction serialization with
independent onset/relationship checks. Existing training artifacts need no
migration. Extend the paired audit with fractional/signed offsets, unequal-duration
chords, cross-staff chords, reused span numbers, voice-label changes, percussion,
pickups and navigation. Re-render source/canonical fixture pairs to check visible
preservation, then measure realistic page token lengths before exporting training
data. Do not shorten output by silently truncating notation.
