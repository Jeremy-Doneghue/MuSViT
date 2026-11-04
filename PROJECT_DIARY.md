# MuSViT project diary

This is the session handoff: current state, standing decisions and next actions.
Detailed recipes, artifact paths and audits belong in the linked experiment reports.
Condensed at the user's request on 2026-11-04; the full earlier diary is available
in Git at `d1d4f3c:PROJECT_DIARY.md`. No historical experiments were rerun for this summary.

## Goal and standing decisions

Transcribe degraded scans of big-band instrumental parts, potentially handwritten,
into editable digital notation that can be re-engraved. Piano is the main
polyphonic case, but other instruments, independent voices and staff arrangements
must be supported. Current synthetic engraving results do not establish real-scan
or handwriting recognition.

- MusicXML is the canonical synthetic source and current interchange format;
  MEI, rasters and model tokens are derived. The user did not require raw MusicXML
  generation as the model target. The approved restricted target is
  `musvit-score-v1` (614 fixed tokens); see the [codec contract](experiments/full_page_omr/docs/SCORE_CODEC.md).
- Preserve written notation separately from playback expansion: repeats/endings,
  similes, multibar rests, D.S./coda, chord symbols and slashes carry meaning.
  Unsupported notation must fail explicitly rather than disappear from labels.
- Polyphony, text/instruction attachment and changing staff roles are required.
  Paired staves may be alternative repeat passages rather than simultaneous voices;
  instrument identity alone is insufficient to decide. Named drum playback mappings
  are optional; readable noteheads/positions, rhythms, voices and scoped text are
  required. Standardization needs verified conventions.
- Include readable content. Clipped but inferable notation is a required case;
  reconstruction/uncertainty policy remains open. Do not label inference as observation.
  The complete collection checklist and supplied-example observations are in
  [target coverage](experiments/full_page_omr/docs/TARGET_COVERAGE.md).
- Keep every page and engraving/degradation variant of a source composition in
  one split. Preserve source/family identity and provenance; never overwrite exports
  or tune against reported test outputs. Fixed vocabulary must not depend on held-out data.
- RGB/grayscale work was set aside by the user; it is not the next investigation.
- Full-page OMR, staff OMR, detection, synthetic generation, scan degradation and
  Bar Review remain in scope. Difficulty/embedding experiments and the legacy
  bekern/Lightning pipeline were removed. Consult the
  [original repository](https://github.com/OMR-PRAIG-UA-ES/MuSViT) for the latter.

## Current state

The latest completed experiment is the [short-staff transfer diagnostic](experiments/full_page_omr/docs/SHORT_STAFF.md)
(`outputs/short_staff_mps_20261101_01/` under full-page OMR). It used 96 training
passages and 16 validation families with base/pitch/rhythm variants (48 records).
Each passage has two bars/eight notes; targets are 459 tokens. Encoder frozen,
1024 RGB, width-128/two-layer decoder, seed 7, constant lr .001, AdamW without
weight decay. Completed 9600 updates/100 presentations per passage in 106.456
training-loop seconds; decoding and controls are additional. Selected update 3200.

| Outcome | Selected checkpoint | Final checkpoint |
| --- | --- | --- |
| Sampled training valid / exact | 0/3 / 0/3 | 0/3 / 0/3 |
| Validation valid / exact | 0/48 / 0/48 | 0/48 / 0/48 |
| Validation token error | 3.440% | 3.958% |
| Gold-prefix pitch-step accuracy | 22.14% | 17.97% |
| Gold-prefix duration-value accuracy | 63.02% | 50.26% |

All outputs stopped with EOS. Failures were duration/type disagreements and bar
under/overfill. Low token error mostly reflects predictable structure, not accurate
music. Gold-prefix fields are separate next-token accuracies, not joint note accuracy.
Selected pitch-step/duration accuracy falls to 13.80%/36.20% under image swaps.
Swapped autonomous outputs follow the donor image's own prediction, but none
matches its reference exactly: visual sensitivity exists without reliable reading.
The transfer gate failed; sampled training failure means this is not a clean
held-out generalization gap. The 48 validation records represent only 16 independent
families, with fixed staff position, meter and a narrow rhythm distribution.

Other retained capabilities and limits:

| Area | Established | Still missing / unverified |
| --- | --- | --- |
| Synthetic scores | Seeded horn scenarios, MusicXML/MEI, rendered measure/page alignment | Representative real-part coverage; broad instrumentation |
| Codec | Semantic/token round trips, polyphonic/percussion fixtures, re-engraving checks | Editor interoperability and complete collection coverage |
| Page export | Complete single-page examples with provenance and split checks | Continuation-page context, cross-page references and part assembly |
| Fonts | Verovio bundled-font coverage/fallback tools, including Petaluma | Integrated dataset font augmentation |
| Scan effects | Augraphy light-copy and framed/rotated library-scan recipes | OMR evaluation, calibration and geometry mapping for spatial labels |
| Bar Review | Reviewed crops and MusicXML export | OMR predictions, assembled full-part export and fidelity review |

## Proposed next investigations

**First candidate: a bounded one-note curriculum diagnostic.** The user requested
recording this as something to explore, not launching it. Specify the dataset,
held-out gates and compute bound before execution.

- Start with one note on a staff: vary pitch with fixed duration, then vary
  duration; progress to a few notes, complete bars, systems and pages. Add
  polyphony, notation features and degradation in later stages.
- Preserve realistic note scale/staff context, valid score labels and source-family
  splits. Vary one difficulty at a time initially and retain some easier examples.
  Advance on unseen-example musical accuracy, not training memorization or aggregate
  token accuracy. Eventually compare against a mixed-complexity baseline at comparable compute.
- The purpose is to locate the first recognition failure before further full-page
  scaling. A local pitch/rhythm feature probe and a lower-learning-rate comparison
  remain candidates; encoder adaptation and a compact event target are proposals,
  not selected changes to the architecture or score contract.

**Longer training / delayed generalisation remains open.** A bounded unchanged
short-staff run with intermediate autonomous training/validation and musical-field
measurements could test it. Classical grokking follows training-set mastery, which
has not been established on this task. Performance worsened after the selected
checkpoint, but this does not rule out later improvement. Saved checkpoints omit
optimizer/RNG state, so loading weights would not give an exact continuation.
Research context: [grokking](https://arxiv.org/abs/2201.02177),
[image-task evidence](https://proceedings.mlr.press/v235/humayun24a.html), and
[OMR curriculum learning](https://arxiv.org/abs/2405.12105); none predicts success here.

No experiment is running or queued. The next action is to design the one-note
pilot and transfer criteria, or choose among the controlled comparisons above.
Longer systems/pages should follow evidence of short-passage transfer. Multi-page
recognition/context and assembly remain separate work; do not cut complete-score
tokens at page boundaries or assume concatenated page images solve continuity.

## Experiment evidence to retain

All learning results below used a frozen encoder. These are development diagnostics,
not a representative real-scan benchmark. Exactness, EOS, grammar completion,
semantic validity and visual recognition are different outcomes. Invalid scores
remain musically unscorable; an empty valid subset does not imply zero musical error.

| Experiment | Main result and interpretation | Detailed report |
| --- | --- | --- |
| Tiny overfit, 2026-10-31 | One/eight sparse pages learned exactly; image swaps and pixel-identical re-engraving passed. Mac Studio reproduction passed. Pipeline/memorization check only. | [Pilot](experiments/full_page_omr/docs/OVERFIT_PILOT.md) |
| First 36-page baseline, 1200 updates | All 3 training samples, 6 validation and 6 test pages hit the token cap without valid scores/EOS. Training failure, not an established generalization gap. | [Clean baseline](experiments/full_page_omr/docs/CLEAN_BASELINE.md) |
| Dense overfit | One/two horn pages and six horn/piano/drum pages learned exactly; donor-following swaps and re-engraving passed. Fresh six-page decoder also passed, so warm-start was unnecessary for that seed/subset. | [Dense overfit](experiments/full_page_omr/docs/DENSE_OVERFIT.md) |
| Longer 36-page run, 14400 updates | Final sampled training 3/3 exact/valid, validation 0/6 valid. Selected checkpoint failed sampled training too. Demonstrates a sampled generalization gap at the final checkpoint. | [Long baseline](experiments/full_page_omr/docs/LONG_BASELINE.md) |
| Controlled edits | Trained one-note contrast passed; two unseen edits failed. Five trained edit controls passed; 5/7 unseen combinations exact. Limited composition within a memorized page, not unseen-score reading. | [Controlled edits](experiments/full_page_omr/docs/CONTROLLED_EDITS.md) |
| 180-page diversity, 14400 / 36000 updates | Both runs/checkpoints: sampled training 0/3 valid, validation 0/6 valid. Longer training did not consistently improve recognition. Includes underfitting, not just held-out failure. | [Diversity](experiments/full_page_omr/docs/DIVERSITY_BASELINE.md) |
| Constrained decoding | Initial comparison: all 12 grammar-complete, none semantically valid; token errors worsened. Later comparisons also produced no valid scores. Remains opt-in. | [Constraints](experiments/full_page_omr/docs/CONSTRAINED_DECODING.md), [longer results](experiments/full_page_omr/docs/DIVERSITY_BASELINE.md) |
| Short staff, 2026-11-01 | 0/48 valid validation and 0/3 valid sampled training at selected/final checkpoints; image sensitivity without reliable recognition. Latest result, summarized above. | [Short staff](experiments/full_page_omr/docs/SHORT_STAFF.md) |

The initial test set was scored in the first clean baseline; subsequent development
runs disabled test scoring. Use validation for development and preserve the test boundary.

## Workspace and supporting tools

Use the [full-page directory guide](experiments/full_page_omr/README.md) for module
ownership and commands. Current code is grouped into generation/, representation/,
datasets/, training/ and diagnostics/, with shared smt_foundation/ and reports in
docs/. `training/overfit_pilot.py` and `datasets/pilot_data.py` still provide shared
helpers; their historical names do not make them dead code. Full-page experiments
use Python module entrypoints; `musvit` lists only staff OMR and detection.

- [Synthetic parts](experiments/full_page_omr/docs/SYNTHETIC_PARTS.md): generator,
  provenance and scenario-specific split recipes. Reserved feature pairs in that
  sampler are not universal settings for the later clean-page/short-staff datasets.
- [Font tools](experiments/full_page_omr/docs/FONT_COVERAGE.md): use Verovio's bundled
  fonts, not the removed downloaded Petaluma bundle.
- [Scan degradation](experiments/scan_degradation/README.md) and its
  [notebook](experiments/scan_degradation/scan_degradation.ipynb): library-scan visually
  accepted, light-copy acceptable. Rejected worn/custom noise should not return as
  defaults without new review. Geometry-changing library-scan has no coordinate
  mapping; the random/JIT-state wrapper is not for concurrent threads.
- [Bar Review](apps/bar_review/README.md): local transcription review and export.
- [Historical target audit](experiments/full_page_omr/docs/TARGET_FORMAT_ANALYSIS.md):
  evidence behind the codec decision; the legacy parser/audit script is removed.

Generated data, reference scans, annotations, credentials and model weights stay
out of documentation/commits. Local artifacts live under each experiment's
outputs/; older full-page exports are under outputs/archive/. Shared real references
are in `data/reference_parts/`. Preserve immutable exports and recorded hashes;
old source/module paths in historical scripts may need migration before rerunning.

Local Mac Studio rendering setup and encoder config are under
`experiments/full_page_omr/outputs/studio_setup_20261031/`; installation/reproduction
is documented in the [pilot report](experiments/full_page_omr/docs/OVERFIT_PILOT.md#mac-studio-rerun--2026-10-31).
For the existing local setup:

```sh
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh
.venv/bin/python -m unittest discover -s tests -v
```

Latest executed regression check (legacy deletion, 2026-11-04): 78 tests ran,
77 passed/one sandbox MPS skip. Actual earlier MPS training/backward/cache checks
passed outside the sandbox. `uv lock --check --offline`, CLI registry, internal
imports and documentation links passed after deletion. These are recorded checks,
not new executions during diary condensation.

## Condensed session history

- **2026-10-31 — Requirements and representation:** established the re-engraving,
  polyphony and big-band notation contract; inspected supplied drum/alternative-pass
  examples without claiming transcription. Audited the original cleaned bekern path,
  then implemented the approved restricted codec and round-trip/re-engraving fixtures.
  Codec fidelity is distinct from recognition quality.
- **2026-10-31 — Tools and training:** retained accepted Augraphy profiles and bundled
  fonts; organized local artifacts. Tiny/dense overfit diagnostics passed, while the
  first held-out baseline failed. Longer training and controlled edits established
  memorization, a sampled generalization gap and limited local edit composition.
  Detailed results are in the experiment table; completed run-start/retry logs are
  omitted here.
- **2026-11-01 — Generalisation diagnostics:** diversity, additional updates and
  grammar constraints did not produce valid unseen scores. Short-staff transfer
  was implemented and executed; its failure shifted the proposed next work toward
  basic recognition/optimization diagnostics rather than full-page scaling.
- **2026-11-04 — Review and cleanup:** discussed delayed generalisation and recorded
  one-note curriculum learning as a candidate. Organized full-page code and reports,
  then deleted the legacy pipeline at the user's request, including its launcher,
  source-dependent audit and legacy-only dependencies (`names`, `wand`, `wonderwords`).
  Current experiments, shared model code and saved artifacts remain. User committed
  these changes before requesting this diary review.
- **2026-11-04 — Diary condensation:** replaced the 1529-line diary with this handoff,
  removing superseded milestones, launch/monitor instructions, temporary setup errors,
  repeated checks and duplicate report detail. Preserved standing requirements,
  key results/limits and unexecuted proposals; full prior text remains in Git.
  Documentation-only change; checked local links and whitespace, no tests/training run.
  Next action remains choosing/designing the next controlled recognition experiment.

For future entries, record the decision/change, evidence or report link, remaining
uncertainty and exact next action. Keep the current state current; put long recipes,
full metrics and transient troubleshooting in subsystem reports rather than repeating them here.
