# Re-engraveable score coverage

## Goal and status

Transcribe degraded scans of big-band parts, potentially handwritten, into an
editable digital score that can be re-engraved. Piano is the most common
polyphonic case, but the representation must support other instruments and
staff arrangements. MusicXML is the current synthetic generator source format;
neither MusicXML nor bekern has been selected as the model target.

This is a requirements inventory. The user supplied the collection-specific
features below on 2026-10-31. See [the format analysis](TARGET_FORMAT_ANALYSIS.md)
for executed parser/conversion probes, coverage status and a recommended next
prototype. The user has real scans available for evaluation; observations from
the supplied screenshots are recorded below, not verified transcriptions.

## User-supplied collection requirements

| Feature | Information the digital score needs to preserve | Audit/example needed |
| --- | --- | --- |
| Falls and glissandos | Type, affected notes, and endpoints when applicable | Distinct handwritten/printed forms; distinguish discrete falls from connecting glissandi |
| Rehearsal marks | Numeric or letter label and musical location | Both label types |
| Written bar-number references | Printed labels and their bar associations, including below barlines or at system starts | Distinguish printed labels from internal measure IDs; decide regeneration/display policy |
| Title, arranger, composer and related information | Text and role | Header examples and attribution variants |
| BPM instructions | Tempo text, beat unit and numeric value where present | Text-only and metronome forms |
| Instrument names | Original label, including variants such as Tenor 2, Bari, Trombone 4 | Preserve label separately from any normalized instrument identity |
| Double barlines | Barline type and position, including at rehearsal marks | Double barlines alongside other structural markings |
| Pauses and fermatas | Symbol/instruction and association with note, rest or barline | Clarify any pause signs distinct from ordinary fermatas |
| Tacet instructions | Text and scope where ascertainable | Local passage versus remainder/whole-part examples |
| Library reference numbers | Text and document location/role | Distinguish collection identifiers from musical numbering |
| Copyright notices | Text and attribution role | Footer/header examples, including degraded text |
| Dotted and double-dotted durations | Base duration and dot count | Notes and rests; verify exact rhythmic duration |
| D.S. al coda | Instruction, segno/coda markers and navigation relationships | Preserve written order separately from playback |
| Dynamics and hairpins | Text/symbol, attachment and span | Hairpins across systems/pages and voice/staff association |
| Rallentando and ritardando | Original text and location; span/end when indicated | Abbreviated and full forms |
| Alternative first-/second-time passages | Both written alternatives, their pass conditions and common continuation | User describes old layouts with alternatives arranged like piano form: play first line on first pass, second line on second pass; inspect a scan before formalizing layout semantics |
| Drum notation | Readable noteheads, staff positions, voices, rhythms and text instructions with their attachment/scope | Named sound mappings are optional; preserve source notation or use a verified standard convention without changing meaning |
| Empty pre-lined staves after the piece | End of musical content despite remaining staff lines | Handwritten manuscript-paper example; do not create extra measures just from empty staves |
| Instrument changes | Original instruction, location and resulting instrument context | Examples needed to determine transposition/clef implications |
| Performance instructions anywhere | Original text with document placement and musical attachment when ascertainable | Between/above/below systems, margins and other atypical placements |
| Cues for other instruments | Cue notes/text, source instrument and voice/staff association | Distinguish cue content from the main part |
| Partially clipped but inferable content | Visible evidence and any inferred reconstruction | Edge-clipped examples; inference and uncertainty policy remains to be agreed |

## Other established requirements

- Polyphony: simultaneous chord notes and independent voices with different
  rhythms, rests and durations; multiple staves; voice-specific ties and slurs.
- Editable written notation, including abbreviations, rather than a playback-only
  event stream. Existing synthetic repeats, endings, similes, multibar rests,
  chord symbols and improvisation slashes remain audit cases.
- User's annotation policy: if readable, include it. No known crossed-out passage
  examples were identified. If ambiguous cancellations occur later, inspect the
  case rather than invent a cancellation rule.
- Degraded print and handwriting are required input domains. Clean synthetic
  round trips and tiny overfit runs alone cannot establish recognition quality.

## Proposed representation and evaluation implications

These are recommendations, not selected format or architecture decisions:

- Preserve musical structure, descriptive text/metadata, and attachment/location
  information. They need not all share a single decoder or token stream.
- Keep source wording alongside normalized meaning when normalization is useful.
- Preserve enough layout evidence to interpret alternatives, cues and floating
  instructions without requiring pixel-identical re-engraving.
- Distinguish observed content from inferred clipped content and retain unresolved
  cases for review. Define acceptable inference with the user before scoring it.
- Test header/footer text, instruction attachment, navigation, percussion notation
  and end-of-piece detection in addition to pitch/rhythm accuracy.

User clarification after the format audit: named drum-instrument/playback mappings
are not essential to the re-engraving goal. Readable drum notation and arbitrary
text instructions over the relevant passages are essential. Standardized output
is acceptable if the convention is verified; otherwise preserve source positions,
noteheads and text rather than guess instrument identities. Preserve text scope
(for example ride versus brushes over a passage), not just a bag of words.

## Next action

The approved [codec prototype and synthetic round-trip fixtures](SCORE_CODEC.md)
and [complete single-page overfit pilot](OVERFIT_PILOT.md) are implemented; eight
tiny clean examples overfit exactly. Next establish source-disjoint held-out clean
evaluation and realistic page density. Continuation-page context/assembly remains
unimplemented. Extend coverage to unverified features and actual notation-editor export. Verify source
annotations for alternative repeat layouts, drum notation/instructions and floating
instructions; clipped-edge inference policy remains open.
Use separate development examples and reserved evaluation scans; preserve
source-composition identity across pages and variants. Keep scans and annotations
out of documentation and commits; record local references rather than embed them.

## Supplied visual examples (2026-10-31)

The user supplied screenshots in conversation. These observations are visual
inspection, not verified transcriptions or completed format tests. Images were
not copied into the repository. Durable source references are still needed when
assembling fixtures; temporary screenshot paths are not stable dataset IDs.

### Corner Pocket — drums

- Printed title/instrument label with handwritten-style musical notation and
  instructions. Visible instructions include brushes, ride cymbal, crash and
  handles, plus a bass-drum indication. Exact wording/attachment should be
  verified during annotation rather than normalized from this inspection.
- Swing/tempo marking, 4/4, letter rehearsal marks, and later location labels
  such as D9/D17/D25 need separate roles in the representation.
- Repeated-measure symbols appear in runs with numbers above selected bars.
  Preserve the marks and numbers before deciding their semantic role; do not
  assume every number denotes a multibar rest or standalone bar number.
- Explicit first/second endings, with an ending continuing across a system
  break. Repeat structure and spans need identities independent of line breaks.
- Cross-shaped and ordinary noteheads at different staff positions, simultaneous
  upper/lower rhythmic events, rests, accents and a triplet marking. Recovering
  percussion instrument identity requires verified convention/context; staff
  position alone must not be treated as a universal drum mapping.

### Charmaine — second tenor saxophone

- User identifies this as the first-/second-time alternative layout discussed
  above. After an initial single-staff passage, paired staves continue through
  multiple systems. Their appearance alone could be mistaken for simultaneous
  music. The pass assignment comes from the user's explanation, not legible
  explicit first-/second-time labels in this screenshot.
- Model the paired passages as alternatives in one instrumental part, with
  corresponding musical positions and pass conditions. Do not automatically
  create a piano part or two simultaneous voices from the brace/staff grouping.
  Exact repeat entry, exit, pass order and continuation need verified annotation.
- Visible header credits, instrument/transposition label, tempo word, vocal
  chorus/soli text, dynamics, hairpin, accidentals, long slurs, footer copyright
  and reference numbers provide additional coverage cases.
- Proposed fixture: reconstruct both alternatives and their order, including
  cross-system continuity; verify by inspecting the re-engraved score and
  traversing the intended performed route. Playback order alone is insufficient
  if the editable score loses the alternatives.

Second-page clarification from the user:

- The instrument is one tenor saxophone, the initial passage on page 1 uses one
  staff, and the paired-staff layout only covers part of the piece. User identifies
  these as clues to its alternative-pass meaning rather than piano-style
  simultaneity. Instrument identity is supporting context, not a universal rule
  that grouped staves on non-piano parts must be repeats.
- Page 2 continues paired staves, shows an explicit first-ending bracket over
  the end of the paired section with repeat barlines, then an explicit second
  ending in single-staff layout. The rest of the page remains single-staff.
  This supplies structural evidence beyond the isolated first-page grouping;
  exact pass assignment and repeat route still require verified annotation.
- Recognition/assembly must retain context across pages and permit staff-group
  roles to change within a part. Cropping each staff independently would discard
  evidence needed to distinguish alternatives from simultaneous voices.
- Additional visible cases include a key-signature change, textual tempo
  modification (Broadly/Rit.), tutti/soli instructions, hairpins, and a final
  fermata. This is a visual inventory, not a full transcription.
