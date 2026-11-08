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
  On 2026-11-06 the user also approved a diagnostic four-token pitch target,
  paired against the current target on the same all-pitches-taught images. It is
  restricted to the fixed one-note task, with MusicXML context supplied by code;
  it does not replace the full-score contract.
- Preserve written notation separately from playback expansion: repeats/endings,
  similes, multibar rests, D.S./coda, chord symbols and slashes carry meaning.
  Unsupported notation must fail explicitly rather than disappear from labels.
  User clarification (2026-11-06): codec restrictions are early-stage simplifications,
  not a permanent coverage boundary. Broader/full MusicXML acceptance is acceptable
  if restrictions hinder useful data or notation coverage. No replacement codec has
  been selected or implemented; distinguish preserving XML from validated musical
  interpretation and renderer support.
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

Latest completed run: seed-19 [placement replication](experiments/full_page_omr/docs/PLACEMENT_COMPARISON.md),
`outputs/placement_seed19_mps_20261108_01`. Same data/features/medium model/lr
.0001/bounds, new initialization and shuffle seed. Selected control 13/56
validation (23.21%); expanded 48/56 (85.71%), matching seed 7 expanded result.
Expanded selected/final training 224/224, all valid; selected update 11200,
final 16800. Control selected training 14/56; final training 33/56, validation
10/56 with 55/56 valid. Both completed 16800 updates; active 259.928/259.049s,
no cap. Placement benefit repeated, but only one of eight selected expanded
errors is shared across seeds. Same validation set, not independent datasets.
All 1344 predictions audited; all 280 feature hashes match seed 7. Appearance/
donor gates still fail. Next proposed action: inspect remaining error patterns
and specify bounded generalization diagnostic; no further run queued.

Previous run details retained below:

Previous result: [placement comparison](experiments/full_page_omr/docs/PLACEMENT_COMPARISON.md),
`outputs/placement_mps_20261108_01`. Same medium 4x256/lr .0001/initial weights,
frozen features, shared fresh validation, 16800 updates each. Four-placement
control selected 25/56 (44.64%) validation exact; sixteen-placement expanded
selected/final 48/56 (85.71%). Final training exact 56/56 and 224/224.
All outputs valid. Exposures 300/control image vs 75/expanded image; active times
250.830s/259.479s, no cap. Donor correctness matches validation. All 1344 saved
predictions audited. Supports placement variety in this single-seed task; eight
validation errors remain, appearance/donor gates fail. No test scoring or advance.
Next proposed action: bounded second-seed replication before adding complexity;
no further run queued. Previous 57.14% used different validation placements.

Previous experiments retained below:

Previous experiment: [medium lower learning rate](experiments/full_page_omr/docs/MEDIUM_LOWER_LR.md),
`outputs/medium_lr_mps_20261108_01`. Medium 4x256 at lr .0001 completed
16800 updates/300 presentations in 254.952 active seconds. Exact initial tensors,
112 feature hashes, image order/exposures match prior lr .001 medium run.
Selected=final: training 56/56 exact; new-placement validation/donor 32/56
(57.14%); all outputs valid. Validation correct trajectory 4/7/10/28/32 at
560/2800/5600/11200/16800. Sustained collapse avoided; training gate passes,
appearance/donor gates fail. All 504 saved predictions audited. No test scoring.
Single seed/simple pitch task; proposed next step is a bounded replication or
appearance-generalization comparison at .0001, neither launched.

Previous result retained below:

Previous result: [capacity comparison](experiments/full_page_omr/docs/CAPACITY_COMPARISON.md),
`outputs/capacity_mps_20261108_01`. Matched 16800 updates/order, score targets,
frozen features. Selected small training/validation 7/56 and 10/56; medium 8/56
and 7/56. Medium collapsed by 2800; later outputs invalid. Small final training/
validation 4/56 and 9/56, valid. Neither passed. Active times 139.675s/257.556s,
no cap. All 1008 predictions audited. Extra capacity did not help at lr .001.
Proposed next step: bounded lower-lr comparison; no further run launched.
User clarified the one-note question was not a requested change.

Previous experiment retained for context:

The preceding experiment is the [paired score/compact-pitch comparison](experiments/full_page_omr/docs/PITCH_TARGETS.md)
in `outputs/pitch_targets_mps_20261106_01/`. All 14 natural pitches C4–B5 taught;
56 training / 56 new-placement validation images, four correlated placements per
pitch per split. Shared sources/labels are intentional in this finite appearance
diagnostic; no composition-family isolation claim. Same cached frozen encoder
features, identical initial decoder state/model/vocabulary (614 tokens), seed 7,
image order and AdamW lr .001/no decay. Score target 157 tokens, pitch target four.
Both completed 16,800 updates / 300 presentations per training image, no time cap
hit; active training times 139.825s score / 142.173s compact, diagnostics additional.
Selection used validation pitch correctness, then validity/exactness, earliest tie.
Both versions failed the training/appearance/donor gate; no test scoring.

| Selected checkpoint outcome | Score target | Compact pitch target |
| --- | --- | --- |
| Selected update | 11200 | 560 |
| Training pitch / joint / exact | 35/56 (62.50%) | 4/56 (7.14%) |
| New-placement pitch / joint / exact | 18/56 (32.14%) | 4/56 (7.14%) |
| Training / validation validity | 56/56 each | 56/56 each |
| Swapped-image donor correctness | 18/56 | 4/56 |

The selected compact version predicts B5 everywhere (a constant-guess baseline).
Final score: training 8/56, validation 9/56 correct/exact, all outputs valid.
Final compact: all training/validation/swap outputs invalid, musically unscorable;
17/56 validation outputs reached EOS malformed, 39 hit the eight-token cap.
Gold compact labels export to exactly matching source MusicXML; all 672 valid
predicted exports passed audit. No parser repair or fabricated pitches.

Shorter output did not improve this matched run and did not reduce active training
time. Neither selected/final version mastered training. This does not establish
that compact targets are intrinsically unsuitable: loss allocation and sequence
length change together, and the common lr was not tuned separately. Next proposed
diagnostic is a bounded direct 14-way choice from frozen features, removing
sequence generation; optimization stability remains a separate candidate. No
further run is queued. Use "versions" with the user rather than unexplained "arms".

The [preceding longer one-note run](experiments/full_page_omr/docs/ONE_NOTE.md#executed-longer-run-result--2026-11-06)
on a different withheld-pitch dataset did achieve 80/80 training exact at 16k/24k,
with 0/32 unseen-pitch transfer, then collapsed near 28k. That establishes finite
memorization capacity but is not a controlled target-format comparison with this
new dataset. Its 8k weights did not exactly replay the first run despite seed 7;
cause unisolated. Earlier results/limits remain in the evidence table and reports.

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

**2026-11-08 budget steering:** user prefers exploring a medium local pilot over
an expensive full reproduction. Proposed four layers/width 256 versus two/128,
using the existing all-notes appearance dataset and full score target first.
Keep encoder, labels, optimizer, image order and evaluation fixed; fresh small
control plus medium run, up to 16,800 updates or 600 active training seconds each.
This budget excludes extraction/evaluation and is not a total wall-clock promise.
Compare common reached checkpoints if capped. This is a capacity comparison at
one optimizer setting, not a paper reproduction; no training launched yet.


**2026-11-08 recommendation revision:** prioritize an audit against the published
full-page OMR recipe before selecting a replacement model. The paper reports
16.4% frozen-encoder and 10.9% fine-tuned average SER; our modified small-decoder,
restricted-target diagnostics are not a reproduction. Qwen remains a comparison
candidate, not an evidence-backed superior choice. Exact proposed next action:
compare original bekern data/tokenization, decoder, curriculum, optimizer and
selection settings with our implementation and specify a bounded reproduction.
No training or restoration of the removed pipeline has been authorized/launched.

**Next recommended diagnostic: direct choice among the 14 taught pitches.** The
paired output-target comparison is complete and failed. Specify a bounded small
readout from frozen features on the same known-label appearance task, preserving
spatial staff context, reporting training fit and new-placement accuracy separately.
It should remove autoregressive sequence generation rather than merely shorten
it. A failed linear readout would only establish failure of that readout; include
appropriate controls before drawing encoder conclusions. A separate controlled
learning-rate/stability comparison remains an alternative. Neither is launched.

User-reported pretrained baseline (2026-11-06): ChatGPT identified one uploaded
example as written G5 and additionally inferred Horn-in-F concert C5. The exact
image/model/prompt were not supplied here and the note identification has not
been independently verified. This motivates a fixed-sample pretrained vision-
language baseline alongside local readout diagnostics, before more custom training.
ChatGPT's already-trained image-to-language behavior is not equivalent to our
frozen visual encoder plus newly initialized decoder trained on 56 examples.
Do not infer its exact training data or internal mechanism from one response.
Inspecting the local G5 fixture confirms part-name "Horn" and no `transpose`
element; Horn-in-F is added context, not explicitly encoded in this pilot. Our
target is written G5; sounding-pitch conversion is separate. A broader baseline
must fix model, prompt and written-versus-sounding convention and measure actual
accuracy over balanced pitches/placements and representative passages. No API
call, new benchmark or image upload is authorized by this discussion.

The design notes below explain the completed [comparison](experiments/full_page_omr/docs/PITCH_TARGETS.md).
They are not instructions to repeat it or advance the curriculum automatically.

**Design basis: all pitches taught, new renderings held out.**
The user questioned withholding notes when a musician normally practices the full
note range, then asked for an independent recommendation. The recommended change
is based on task design and the observed 16k/24k training mastery: teach all 14
natural pitches C4–B5 at fixed duration/clef, with balanced examples, then measure
those same labels on new renderings/placements. Initially vary a controlled
appearance factor rather than adding multiple musical difficulties. A finite
one-note same-label rendering assessment explicitly differs from composition-
family-disjoint validation; preserve the old exports/results and document this
diagnostic policy before implementation. Do not disguise render copies as new
independent compositions. At the next sequence stage, all individual pitches
remain represented in training while complete held-out note sequences/families
test compositional transfer. Unseen absolute pitches can remain a separate later
rule-inference test, rather than the initial advancement requirement.

Initially proposed keeping the current encoder/decoder/codec for the all-notes comparison; propose
checkpoint selection on held-out-render pitch accuracy/validity, with fixed bounds
and snapshots declared before running, instead of aggregate token CE alone.
Treat the observed late collapse as a separate stability problem: preserve the
mastered snapshots and specify any lower/decaying-lr comparison independently.
This revised design was subsequently authorized and implemented in the paired
comparison. Its measured results are now summarized above; no new run is queued.

Output-burden clarification (2026-11-06): the user questioned jointly learning
notation recognition and MusicXML generation. Local code inspection confirms the
pretrained component is the image encoder; the small adaptor/decoder is freshly
initialized and predicts restricted MusicXML-tree tokens, which the codec writes
as XML. One note requires 157 output tokens, mostly constant structure. Existing
exact in-sample outputs establish capacity for this restricted target; valid but
wrong held-out outputs do not establish accurate reading or general MusicXML
coverage. Serialization burden may affect learning, but has not been isolated as
the cause of the held-out failure.

Completed experiment design: use one fixed all-notes-taught dataset and rendering
assessment for two matched versions, current score-token
target versus a compact pitch target, retaining the same frozen encoder and
decoder architecture/width/layers rather than also switching to a classifier.
Match image presentations, seed/optimizer settings and musical evaluation; report
runtime because target lengths differ. A deterministic writer can serialize the
compact pitch plus the task's explicitly fixed clef/meter/duration/staff context
into MusicXML. Fixed context is supplied by the experiment, not recognized.
When rhythm/voices/notation vary later, their information must become explicit
predicted fields/relations; a pitch list is not a complete big-band score format.
This tests output representation separately from the revised pitch-support split.
Do not compare a new compact/all-notes run only against the old withheld-pitch run
and attribute differences to representation. The paired diagnostic is now executed;
the compact representation has not replaced the general score codec.

**Other candidates: unseen-position readout and training-stability diagnostics.**
The longer one-note pilot mastered training at 16k/24k while failing held-out pitch
transfer, then regressed. A local pitch-feature probe can examine how accessible
staff position is without autoregressive decoding, distinguishing training fit
from unseen-position regression. Separately, a controlled lower/decaying-lr run
could investigate late instability; its cause has not been proved. Encoder
adaptation remains a later comparison, not an established fix. Specify probe or
comparison inputs, held-out task and compute bound before execution. Seed-19
replication is unrun; no further experiment is queued. See the
[one-note report](experiments/full_page_omr/docs/ONE_NOTE.md) for all executed results.
The wider curriculum below remains proposed and should not yet advance.

2026-11-06 clarification after reviewing the
[MuSViT paper, appendix A.9.1](https://arxiv.org/html/2606.31811v1#A9.SS1): frozen
encoder OMR succeeds in the authors' setup, supporting an expectation that useful
pitch information exists. Our failure does not establish an encoder deficiency.
First verify local checkpoint provenance against the intended published release:
the pilot setup report records a configuration from
`carlospm12/LSMT-MAE-Base-1024-16` and a hashed root weight file, while the current
release is `PRAIG/musvit`. Subsequent checksum check: the user reported MD5
`d4e67487e3b93d600609c5926e7e6b25` for their PRAIG download; our root weight file
matches that MD5 exactly and still matches the SHA-256 recorded in the pilot.
This resolves the weight-file mismatch concern against the user's download;
the older configuration identifier alone does not imply different weights.
Local code inspection confirms a strict
ViT weight load, unmasked ordered patch outputs, and 1024 RGB [0,1] preprocessing
consistent with the current model-card example; no new inference experiment ran.

Proposed probe design: bypass the 768-to-128 adaptor and autoregressive decoder,
retain the spatial encoder patches covering a fixed whole-staff region (not a
pitch-dependent note-centred crop), and fit a direct linear pitch readout. Report
training separability and same-pitch rendering robustness separately from unseen
pitch-position transfer. A classifier cannot evaluate a pitch class never used
to train its output: use ordinal staff-position regression for the existing
four-pitch holdout. Layout-only holdouts inside the training partition are an
explicit diagnostic of repeated targets, not source-disjoint validation. Include
label-shuffle/constant controls; a failed linear probe only rules out that readout,
not all information in the encoder. Strong raw-feature results would direct the
next check toward the adaptor, attention/decoding and optimization. This remains
a proposal; no new datasets, probes or weight downloads are authorized by discussion.

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

2026-11-06 initial recommendation (wider curriculum remains proposed; finite
pilot now executed above): defer broad PDMX training and a full-codec rewrite
until basic unseen-example reading works.
Use clean, realistic-scale staff contexts: one-note pitch discrimination, then
duration discrimination with pitch fixed, then joint pitch/duration combinations,
short sequences/complete bars, multiple bars/systems, polyphony and pages. Treat
this as a diagnostic ladder first; later compare curriculum against mixed training
at matched compute. Retain easier examples as stages advance. Use valid complete
scores (e.g. explicit pickups for short examples), balanced labels and separately
reported held-out content combinations and engraving/layout variations. Do not
confound first learning a symbol class with compositional generalization.

Provisional advancement gates: at least 99% joint pitch/duration event accuracy,
95% exact autonomous passage transcription and 99% semantic validity over at
least 100 held-out source families, with image-swap controls and replication under
a second training seed. These are suggested engineering thresholds, not research
results; fix the sample design and per-stage update cap before running. If the
one-note task fails, use a pitch/rhythm probe on the same encoder features and a
controlled lower-learning-rate comparison to distinguish feature accessibility
from sequence-decoding/optimization trouble. Consider encoder adaptation only
as a subsequent controlled comparison. Keep codec/model changes separate from
the first diagnostic. Introduce a curated simple PDMX subset once short-passage
transfer works, increasing musical and visual complexity separately. Real-scan
evaluation remains necessary. The initial proposed action was to specify the
one-note dataset, held-out splits, metrics and compute bound; the finite pitch
pilot above has now executed with its narrower evaluation claims and failed its gate.

**Longer training / delayed generalisation remains open.** The 40k one-note run
established training-set mastery at 16k/24k, but held-out pitch remained wrong and
training collapsed around 28k. A stable longer post-mastery window remains
untested. This does not predict delayed improvement; distinguish it from simply
running an unstable optimization longer. Short-staff training/mastery remains a
separate question. Saved checkpoints omit optimizer/RNG state, so loading weights
would not give an exact continuation.
Research context: [grokking](https://arxiv.org/abs/2201.02177),
[image-task evidence](https://proceedings.mlr.press/v235/humayun24a.html), and
[OMR curriculum learning](https://arxiv.org/abs/2405.12105); none predicts success here.

The authorized longer comparison and the subsequent all-notes-taught paired-target
comparison are complete. No experiment is running or queued. Direct readout
and controlled learning-rate comparisons remain alternatives, using the saved
16k/24k training mastery and held-out failures as evidence. The wrapper's
explicit extended mode retains the original default bounds and saves fixed-step
snapshots; it does not authorize automatic extensions, replication or curriculum
advancement. Preserve the current immutable export and all completed runs.
Longer systems/pages should follow evidence of short-passage transfer. Multi-page
recognition/context and assembly remain separate work; do not cut complete-score
tokens at page boundaries or assume concatenated page images solve continuity.

**Additional resource candidate (reviewed 2026-11-06): [PDMX](https://github.com/pnlong/PDMX/).**
The [Zenodo v9 release](https://zenodo.org/records/15571083) documents over 250K
MuseScore-derived scores, with MXL and corresponding PDF exports where available.
This could supply varied musical content for re-rendering/degradation and expose
codec coverage gaps. It does not establish recognition of historical scans or
handwriting, and representative big-band part coverage has not been measured.
The authors report conflicting license metadata for 12.29% of scores and recommend
`no_license_conflict`; their `all_valid` flag identifies available associated exports,
not compatibility with our codec. Metadata also includes deduplication groups.

Proposed first action if pursuing PDMX: audit a small, fixed sample from the
intersection of `no_license_conflict`, `all_valid` and `deduplicated`, stratified
across single-staff instruments, piano and percussion. Preserve original MXL and
provenance; inventory unsupported notation before defining any explicit import
normalization. Our codec rejects engraving coordinates and other common MusicXML
features, so direct compatibility is unverified. Compare source-PDF and imported
render semantics, including written repeats, voices and text. Group related
compositions/arrangements before splitting; the deduplicated subset alone does
not establish our family-isolation requirement. No download, importer, codec
change or training run is approved or queued by this resource review. One-note
transfer failure and late instability favor feature/optimization probes before PDMX.

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
| Short staff, 2026-11-01 | 0/48 valid validation and 0/3 valid sampled training at selected/final checkpoints; image sensitivity without reliable recognition. | [Short staff](experiments/full_page_omr/docs/SHORT_STAFF.md) |
| One note, 8k updates, 2026-11-06 | All outputs valid; full training pitch/exact 8/80 selected and 15/80 final; held-out and donor-reference pitch/exact 0/32 at both. Training recognition failure on finite pitch support. | [One note](experiments/full_page_omr/docs/ONE_NOTE.md) |
| One note, 40k updates, 2026-11-06 | Training exact 80/80 at 16k/24k, held-out pitch/exact 0/32; late loss spike and all final outputs invalid. Fresh seed-7 run does not exactly replay the original 8k weights. | [Longer one note](experiments/full_page_omr/docs/ONE_NOTE.md#executed-longer-run-result--2026-11-06) |
| All-notes paired targets, 2026-11-06 | Same images/features/initialization/order, 16,800 updates each. Selected score training/validation 35/56 and 18/56 correct; compact 4/56 each, predicting B5. Both gates fail; compact final predictions malformed. Latest result, summarized above. | [Paired targets](experiments/full_page_omr/docs/PITCH_TARGETS.md) |

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

Latest regression check (paired-target setup, 2026-11-06): 86 tests ran, 85 passed
and one sandbox MPS check skipped, in 14.151s. New tests cover paired labels,
strict compact parsing/MusicXML export, explicit appearance-policy checks,
tampering, musical selection and both versions' CPU wiring. Retained tests include
extended bounds, snapshot evaluation and equal CPU final weights with/without saving.
The earlier dedicated suite also passed family-consistency/extra-note assertions.
Independent export audit
verified 336 artifact hashes, semantic round trips, grouped splits, matched-layout
donors and 112 distinct 1024 RGB inputs. These were setup checks; the subsequent
production MPS run and its independent prediction audit are recorded above/below.

Earlier regression check (legacy deletion, 2026-11-04): 78 tests ran,
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
- **2026-11-06 — PDMX resource review:** inspected the upstream README, paper abstract
  and Zenodo v9 release documentation, alongside the local codec contract. Recorded
  potential use as a score-content source and a proposed bounded compatibility audit
  above. No dataset files were downloaded or experimentally validated; codec acceptance,
  PDF/MXL fidelity, relevant instrumentation and family grouping remain unverified.
  Documentation-only change; checked diff whitespace. Exact next action for this
  candidate is to select and audit a fixed filtered sample before implementing an
  importer; this is a proposal, not a decision to replace the recognition diagnostic.

- **2026-11-06 — Codec scope clarification:** user clarified that the restricted
  codec was chosen for early simplicity and may be broadened to all MusicXML if
  it obstructs progress. Inspected current element/attribute allowlists and fixed
  vocabulary: removing rejection checks alone would not encode new XML names.
  Broad preservation, semantic validation and rendering need separate guarantees.
  No codec or vocabulary changed and no experiments ran. Next action, if pursuing
  broader support, is to design a versioned general XML encoding or schema-derived
  vocabulary and preservation checks, using a fixed PDMX sample to measure actual
  coverage needs; this implementation approach remains a proposal.

- **2026-11-06 — Curriculum sequencing discussion:** recommended prioritizing
  bounded recognition diagnostics before broad PDMX training, based on the recorded
  short-staff failure. Added proposed stages, advancement gates and failure branches
  above; these are recommendations awaiting experiment selection. Revisited the
  [OMR curriculum paper abstract](https://arxiv.org/abs/2405.12105), which supports
  curriculum as a research direction but does not validate these thresholds or this
  architecture. Also retained the user's intervening clarification: a codec rewrite
  may start fresh without maintaining multiple codec versions; incompatible tokens
  and checkpoints must still be detected, and existing exports stay preserved.
  Documentation-only change; diff whitespace checked, no tests or training run.
  Exact next action: define a bounded one-note pilot before implementation/execution.

- **2026-11-06 — Bounded one-note pilot setup:** user approved setup. Implemented
  `datasets/one_note_data.py`, `training/one_note_experiment.py` and dedicated tests;
  [fixed contract and launch command](experiments/full_page_omr/docs/ONE_NOTE.md).
  The shared dataset adapter now accepts explicitly grouped one-note raster
  variants while checking source/family consistency. No codec/model change.
  Final immutable export: `experiments/full_page_omr/outputs/one_note_pitch_20261106_03/`;
  80/32 training/validation images, 10/four absolute-pitch targets, 157-token
  labels under a fixed 256 cap. All page translations stay with their source.
  Explicitly documented that one-note transposition equivalence collapses the
  entire task, so this finite absolute-pitch holdout uses a different fingerprint
  and cannot claim composition-family transfer or 100 independent validation
  families. Earlier incomplete setup exports remain untouched.
  Bound: 8000 updates or 300 training-loop seconds; initialization/decoding are
  additional. Seeds 7 and 19 are fixed first-run/replication choices, not queued.
  Controls assess every training image, all held-out images, both checkpoints,
  gold-prefix fields and autonomous donor correctness. Invalid outputs remain
  unscorable and cannot earn success credit. No automatic stage advancement.
  Checks: 82-test suite passed with one MPS skip; final dedicated four tests also
  passed. Tiny random-encoder/forced-EOS one-update CPU smoke test exercised wiring
  only. CLI help and whitespace passed. Independently audited 336 artifact hashes,
  round trips, split/donor grouping, source hashes and 112 distinct 1024 RGB inputs;
  saved `setup_audit.json` in the export. Audit script:
  `/private/tmp/audit_one_note_20261106.py`; test logs:
  `/private/tmp/musvit-one-note-tests-20261106.log` and
  `/private/tmp/musvit-one-note-final-tests-20261106.log`. Visually inspected one
  validation page. Local encoder weight/config paths exist; production training
  and GPU behavior remain untested for this pilot. Exact next action: execute the
  documented seed-7 command in a new run directory and review selected/final gates.

- **2026-11-06 — One-note pilot execution:** user requested the prepared run.
  Sandbox MPS attempt stopped before initialization; preserved its empty `-01`
  run directory. Approved GPU execution in new
  `experiments/full_page_omr/outputs/one_note_pitch_mps_20261106_02/` completed all
  8000 updates, exactly 100 presentations/image, in 73.728 training-loop seconds;
  selected update 1600. Original contract unchanged; no time cap reached, no test
  scoring, encoder frozen, no production source-code changes. Both checkpoint
  controls completed successfully. All 294 autonomous outputs valid/EOS with
  correct constant duration; training pitch/exact 8/80 selected and 15/80 final,
  validation and donor-reference pitch/exact 0/32 at both. Selected predicts F5
  everywhere; final predicts only F5/F4/B5. All three gate checks failed. Fixed
  duration and score validity do not establish rhythm or pitch reading; this is
  a training-recognition failure, not only a generalization gap. Full results and
  limits: [one-note report](experiments/full_page_omr/docs/ONE_NOTE.md).
  Independent CPU audit recomputed all 294 autonomous metrics, verified 336
  artifact hashes, input/checkpoint identities, exposure counts, source-grouped
  donor/layout pairing, donor prediction consistency, totals and gate decisions.
  Saved `independent_audit.json` under the run. Gold-prefix fields were read from
  executed GPU controls, not rerun. Actual MPS training and cached/full-prefix
  decoder agreement passed. Latest regression suite remains setup's 82 tests
  (81 passed/one MPS skip); documentation whitespace checked after execution.
  Log: `/private/tmp/musvit-one-note-training-20261106-02.log`; audit script/output:
  `/private/tmp/audit_one_note_run_20261106.py`,
  `/private/tmp/musvit-one-note-run-audit-20261106.json`. Seed 19 and later stages
  remain unrun. Proposed exact next action: specify a bounded local pitch probe
  on these frozen features, reporting training fit and held-out-position transfer
  separately; no additional experiment was launched.

- **2026-11-06 — Encoder probe rationale and paper check:** user asked whether the
  MuSViT paper already supports encoder capability. Reviewed the original paper
  (especially A.9.1), author model card and local loader/preprocessing/feature path.
  Paper reports successful frozen-encoder OMR, so the probe is a local diagnostic,
  not evidence that the published encoder lacks pitch information. Flagged the
  older recorded configuration identifier versus the current published model;
  weight equivalence remains unverified. Proposed direct spatial-feature readout,
  separating training fit, layout robustness and unseen-position regression;
  noted unseen-label classification would be invalid. Documentation-only change,
  no inference/training/downloads; diff whitespace checked. Exact next proposed
  action: verify checkpoint provenance, then specify a bounded probe and controls.

- **2026-11-06 — PRAIG weight checksum comparison:** user supplied MD5
  `d4e67487e3b93d600609c5926e7e6b25` for their downloaded PRAIG `model.safetensors`.
  Executed local MD5 and SHA-256 checks: MD5 matches exactly; SHA-256 remains
  `109bbaf31d9f2184df1b841579e06d25bc58ed6a42a10dd5f4a5d27d01889db2`, matching
  the one-note run configuration. Our experiment used the same file checksum as
  the user's PRAIG download. This resolves the raised weight-file provenance
  concern; no weight replacement or retraining is needed on that basis. No new
  model inference or experiment ran. Next proposed action remains specifying
  the bounded direct pitch-feature probe; diff whitespace checked.

- **2026-11-06 — Longer one-note run discussion:** user asked about more training.
  Inspected saved training/validation loss histories and checkpoint keys. The
  final checkpoint omits optimizer/RNG state; loading decoder weights alone is
  not exact continuation. Proposed an unchanged fresh seed-7 40,000-update /
  900-training-second comparison with intermediate autonomous pitch measurements.
  Loss histories were nonmonotonic and validation CE best remained step 1600;
  existing 10%/18.75% training accuracy does not establish a plateau or predict
  later success. No code/weights/data changed, no additional training launched.
  Next action is to select this bounded comparison or the direct feature probe;
  an extended run requires updating the wrapper's explicit limits first.

- **2026-11-06 — Longer one-note run launch:** user authorized execution. Added
  explicit extended bounds (40,000 updates / 900 training-loop seconds) and optional
  fixed-step snapshots in the shared trainer. Evaluation decodes all training and
  validation images at reached 8k/16k/24k/40k snapshots after training, with final
  outputs reused; selected/final swap controls remain. CPU tests check both bounds,
  intermediate/final snapshot evaluation and identical final weights with/without
  snapshot saving. Full suite: 82 tests, 81 passed/one sandbox MPS skip, 12.681s;
  log `/private/tmp/musvit-one-note-long-tests-20261106.log`. Launch contract recorded
  before execution in [one-note report](experiments/full_page_omr/docs/ONE_NOTE.md).
  Fresh seed-7 MPS run launched with approved GPU access outside the sandbox in
  `experiments/full_page_omr/outputs/one_note_pitch_long_mps_20261106_01/`.
  Log: `/private/tmp/musvit-one-note-long-training-20261106-01.log`.
  Original dataset, weights, architecture and optimizer settings preserved. No
  numerical results yet. Exact next action: monitor completion, audit both controls
  and the fixed-step trajectory, compare the 8k snapshot with the prior final
  weights, then update the current state and report without launching another run.

- **2026-11-06 — Longer one-note run completed:** MPS run
  `outputs/one_note_pitch_long_mps_20261106_01/` completed 40,000 updates, exactly
  500 presentations/image, in 343.255 training-loop seconds; no time cap reached.
  Same data/model/lr/optimizer, frozen encoder, fresh seed 7, no test access.
  Selected update 1600 still predicts F5 (training 8/80 exact, validation 0/32).
  New 8k snapshot: training 21/80 exact with 58/80 valid; validation 0/32 exact,
  26/32 valid. **16k and 24k: training 80/80 exact/valid, validation 0/32
  pitch/exact with 32/32 valid.** This establishes training mastery and a finite
  held-out pitch gap, superseding the initial short run's undertraining-only
  evidence. Loss spiked around 28k; all 147 final outputs hit the cap without EOS
  or valid scores. Late instability cause remains unisolated. Both selected/final
  gate reports fail. No harder stage, replication or follow-up run launched.
  Audited all 630 saved autonomous predictions and intermediate musical totals,
  336 dataset artifact hashes, inputs/checkpoints, exposures, donor pairing,
  selected/final gates and final snapshot/last tensor equality. Compared new 8k
  to old final: all 57 tensors differ, max absolute difference 1.259953; numerical
  divergence cause is unisolated, so use within-run snapshots for time comparisons.
  Saved `independent_audit.json` under the run. Audit script/output:
  `/private/tmp/audit_one_note_long_run_20261106.py`,
  `/private/tmp/musvit-one-note-long-run-audit-20261106.json`.
  Full report/limits: [one-note report](experiments/full_page_omr/docs/ONE_NOTE.md).
  Actual MPS training/cached decoder agreement passed. Latest prelaunch regression
  suite is 82 tests (81 passed/one skip); no runtime code changes after launch.
  Documentation whitespace checked. Proposed next action: choose a bounded
  staff-position readout for transfer or a separate lower/decaying-lr comparison
  for stability; training-set mastery alone does not authorize advancing curriculum.

- **2026-11-06 — Reconsidering the curriculum gate:** user questioned whether
  withholding complete note positions was appropriate for initial music reading,
  then asked for an independent recommendation rather than deference to their
  analogy. Reassessed experiment design against the executed evidence: withheld
  absolute pitch positions test inference of untaught mappings; 16k/24k establish
  memorization of all taught targets, but do not test new appearances of taught
  labels. Recommended a new bounded comparison teaching all 14 pitches in the
  current range and assessing unseen renderings, then unseen sequences of known
  notes. Explicitly distinguish finite rendering assessment from composition-family
  isolation; preserve prior results and the harder unseen-position test. Proposed
  musical accuracy/validity for checkpoint selection and separate stability work.
  This corrects the role of the original gate, not its measured outcomes. No new
  experiment/code/data changed; documentation diff whitespace checked. Exact next
  proposed action: specify all-notes rendering pilot/split/evaluation/bounds before
  implementation; no further run is authorized by the discussion alone.

- **2026-11-06 — Recognition versus serialization discussion:** user questioned
  whether the current model is equipped to output MusicXML and whether two hard
  tasks are being learned together. Inspected the codec contract, fresh decoder
  construction, feature path and earlier exact-output evidence. Confirmed that
  MuSViT is the pretrained encoder; our new decoder learns both image-conditioned
  labels and the restricted MusicXML-tree token sequence. Restricted in-sample
  generation works, including 80/80 one-note targets at 16k/24k; neither general
  MusicXML coverage nor serialization as the cause of recognition failure is
  established. Recommended a controlled target comparison on the same future
  all-notes dataset, with the same decoder architecture and deterministic MusicXML
  export from compact predictions plus explicitly fixed task context. Later varied
  musical content must be predicted explicitly. No code/data/weights/experiments
  changed; diff whitespace checked. Exact next proposed action: specify the shared
  all-notes dataset, rendering assessment and paired target/evaluation/budget
  contract before implementing either arm.

- **2026-11-06 — Paired compact-target setup and launch:** user authorized trying
  the compact pitch target. Implemented an explicit all-pitches-taught appearance
  diagnostic, paired score/pitch labels and a matched autoregressive trainer;
  [prelaunch contract](experiments/full_page_omr/docs/PITCH_TARGETS.md). Four-token
  pitch stream reuses existing BOS/literal/EOS IDs and all 614 vocabulary entries;
  no classifier, masking or general codec replacement. Strict compact parsing
  and deterministic MusicXML export preserve the fixed fixture exactly for all
  14 pitches; quarter duration/clef/meter/part context are supplied, not inferred.
  New immutable export: `outputs/pitch_targets_20261106_01/`, 56 training and 56
  validation images, same 14 labels but disjoint fixed placements. Explicitly
  shared-source finite diagnostic, not composition-family isolation; original
  adapters still reject it and prior exports are preserved. One encoder extraction
  and one initial non-encoder state shared by both arms, seed/image order matched;
  same model and full vocabulary, full score target 157 tokens versus pitch 4.
  Bound 300 presentations/image / 16,800 updates or 600 active training seconds
  per arm; extraction/diagnostics additional. Musical validation selection at
  fixed checkpoints; selected/final train-all and same-placement donor controls.
  Dedicated four tests passed, then full suite: 86 tests, 85 passed/one MPS skip
  (14.151s). Logs `/private/tmp/musvit-pitch-target-setup-tests-20261106.log`,
  `/private/tmp/musvit-pitch-target-full-tests-20261106.log`. Independent audit
  verified 336 artifact hashes, 112 distinct 1024 RGB inputs, paired source/target
  semantics and source hashes; saved `setup_audit.json` under the export, script
  `/private/tmp/audit_pitch_target_setup_20261106.py`. Launched MPS outside the
  sandbox with approved GPU access in `outputs/pitch_targets_mps_20261106_01/`;
  log `/private/tmp/musvit-pitch-target-training-20261106-01.log`.
  No learning result yet. Exact next action: complete both arms, independently
  audit checkpoints/predictions/exposure matching, then update current results.

- **2026-11-06 — Paired target comparison completed:** MPS run
  `outputs/pitch_targets_mps_20261106_01/` finished both versions at 16,800 updates,
  exactly 300 presentations/image; active training times score 139.825s / compact
  142.173s, no time cap. Same 56/56 known-pitch/new-placement images, 112 shared
  frozen feature tensors, identical initial non-encoder state, same reconstructed
  image order/vocabulary/model/optimizer/lr. Selected score update 11200: training
  35/56 and validation/donor 18/56 pitch/joint/exact; all valid. Selected compact
  update 560: constant B5, training/validation/donor 4/56 each, all valid. Final
  score training/validation 8/56 and 9/56, all valid. Final compact outputs all
  malformed; validation EOS 17/56, remaining 39 hit cap 8. Both selected/final
  gates fail every check. No evidence that short output alone fixes learning at
  these settings; one matched learning rate is not an optimization study of each
  representation. No claim that compact targets cannot work or encoder lacks
  pitch information. Fixed MusicXML context is supplied rather than recognized.
  Independent CPU audit recomputed all 1008 predictions, verified all 672 valid
  MusicXML exports, 336 dataset artifact hashes, input/implementation hashes,
  checkpoint identities, selection/tie rules, musical totals, order/exposures,
  same-placement donors, donor-prediction consistency and gates. Saved
  `independent_audit.json` under the run. Audit script/output:
  `/private/tmp/audit_pitch_target_run_20261106.py`,
  `/private/tmp/musvit-pitch-target-run-audit-20261106.json`. GPU inference was not
  rerun by this audit. Actual MPS training and cached/full-prefix checks passed
  for both versions. Full prelaunch suite 86 tests (85 passed/one skip); no
  production code changes after launch. Documentation whitespace checked.
  Full report: [paired targets](experiments/full_page_omr/docs/PITCH_TARGETS.md).
  During execution the user asked what "arms" meant; explained the two experimental
  versions and adopted plain "versions" wording. No follow-up experiment launched.
  Exact next proposed action: specify a bounded direct 14-note choice from frozen
  features, removing sequence generation and measuring training/new-placement fit;
  keep optimization/stability comparisons separate and predeclared.

For future entries, record the decision/change, evidence or report link, remaining
uncertainty and exact next action. Keep the current state current; put long recipes,
full metrics and transient troubleshooting in subsystem reports rather than repeating them here.

- **2026-11-08 — Pretrained multimodal alternative review:** user asked about
  fine-tuning Qwen3.5 and whether the current architecture has sufficient capability.
  Reviewed diary evidence and local decoder defaults (width 128, two layers,
  frozen encoder). Current results establish limited memorization, not reliable
  recognition; they do not prove an architectural impossibility. Reviewed the
  official [Qwen3.5-9B model card](https://huggingface.co/Qwen/Qwen3.5-9B)
  (image/text input, Apache-2.0) and NVIDIA's
  [multimodal fine-tuning recipe](https://docs.nvidia.com/nemo/automodel/nightly/model-coverage/vision-language-models/qwen/Qwen3.5-9B).
  Proposed evaluating the intact pretrained VLM before adapter fine-tuning, using
  balanced written-pitch examples plus short passages and representative scans;
  retain musical metrics, source grouping and deterministic export validation.
  This is an alternative research direction, not an agreed replacement or evidence
  of Qwen OMR accuracy. Existing data/export/review infrastructure is reusable;
  model input processing, tokenizer and trainer require separate integration.
  No model download, inference, training or image upload executed. Exact proposed
  next action: specify a fixed Qwen3.5-9B baseline, output contract and compute
  bound before implementation; local memory/runtime feasibility remains unverified.

- **2026-11-08 — Published OMR success reconsidered:** user challenged abandoning
  MuSViT given its published results. Rechecked paper section 3.1 and A.9.1,
  tables 15–16: frozen SER 17.6/15.2 and fine-tuned 10.5/11.3 on
  Mozarteum/Polish Digital Scores, versus prior 14.1/25.8. SER is edit distance,
  not exact-page success. Paper trains on synthetic GrandStaff pages with an
  increasing-system curriculum, then mixes target scans; fine-tuning unfreezes
  the encoder at the real-page stage. Local pilot report explicitly documents
  a two-layer width-128 diagnostic decoder versus original eight-layer width-256
  configuration. Current experiments do not reproduce that recipe. Revised the
  previous preference for Qwen: audit/reproduce the published approach first;
  intact Qwen remains an untested alternative (paper compares visual encoders,
  not intact Qwen3.5). No experiment executed. Next action is the recipe audit
  specified above; documentation whitespace check passed.

- **2026-11-08 — Medium pilot proposal:** inspected paired trainer and model
  factory in response to budget constraint. Suggested four layers/width 256,
  retaining score targets and same 56/56 all-pitches placement diagnostic, with
  a fresh small control. Proposed retaining seed 7, AdamW .001 and existing
  checkpoint selection; optimization sensitivity remains a limitation. Executed
  CPU model construction/counting only with a config-bearing dummy encoder
  (initial dummy without config failed, then corrected); no data inference or
  training. Next action: expose bounded capacity/target selection in the paired
  runner, validate wiring and run the matched small/medium score comparison
  when proceeding with this proposed experiment. Existing exports preserved.

- **2026-11-08 — Capacity comparison authorized and launched:** user approved
  small/medium run. Added explicit `--capacity-comparison` mode to paired trainer,
  sharing frozen features across fresh 2x128 and 4x256 score decoders. Contract:
  [capacity comparison](experiments/full_page_omr/docs/CAPACITY_COMPARISON.md).
  Same existing all-pitches export, seed/order/optimizer/evaluation, 16800 updates
  or 600 active seconds per version, diagnostics extra. Full suite 86 tests,
  85 passed/one sandbox MPS skip (14.804s), including new capacity wiring check.
  Initial test attempt lacked native Cairo environment; passed after sourcing
  documented activation script. Log `/private/tmp/capacity-tests.log`.
  GPU run authorized outside sandbox, output `outputs/capacity_mps_20261108_01`,
  log `/private/tmp/capacity-training-20261108.log`. No results yet. Next action:
  monitor completion, audit musical totals and matched exposure, record results.

- **2026-11-08 — Capacity comparison completed:** matched 16800 updates/order,
  300 presentations/image. Selected small validation 10/56, medium 7/56;
  medium later collapsed (all final outputs invalid). No capacity benefit at
  lr .001. All 1008 saved predictions, exports, summaries and checkpoint selection
  audited on CPU; data integrity and implementation hashes verified. Report:
  [capacity comparison](experiments/full_page_omr/docs/CAPACITY_COMPARISON.md),
  including initialization metadata caveat. No inference rerun. Prelaunch 85 tests
  passed/one skipped; actual MPS cache checks passed. User's one-note question is
  not steering. Next proposed action: bounded lower-lr comparison, not launched.
  Explained persistent GPU approval through a narrow command-prefix rule using
  official OpenAI documentation; no permission settings changed. Whitespace checked.

- **2026-11-08 — Lower learning rate authorized and launched:** user approved
  medium .0001 run against completed .001 medium baseline. Added explicit
  `--medium-lr-baseline` mode and configurable lr; fail before training unless
  dataset/encoder identities, seed/resolution/presentations, frozen feature hashes
  and initial medium tensors match baseline. Contract in
  [lower-lr report](experiments/full_page_omr/docs/MEDIUM_LOWER_LR.md).
  Same 16800-update/600-active-second bound, evaluation additional; no new data.
  Full suite 86 tests: 85 passed/one MPS skip (15.415s), including baseline
  comparison wiring. Log `/private/tmp/medium-lr-tests.log`. GPU launch in
  `outputs/medium_lr_mps_20261108_01`; specific trainer prefix approval saved.
  Next action: monitor, audit matching exposures/initialization/features and
  musical outcomes against .001, update report. No results yet.

- **2026-11-08 — Lower-lr run completed and audited:** lr .0001 medium reached
  56/56 training and 32/56 new-placement/donor exact at selected/final 16800,
  all valid; active time 254.952s, 300 presentations/image, no cap. Initial
  tensors, features, order/exposures exactly match .001 baseline. Validation
  trajectory 4/7/10/28/32. Stable relative to baseline collapse; generalization
  still below gate. Audit verified 504 saved predictions/XML, summaries,
  checkpoint selection/hashes and data/implementation identities; no inference
  rerun. Report: [lower lr](experiments/full_page_omr/docs/MEDIUM_LOWER_LR.md).
  Prelaunch 85 tests passed/one skipped; actual MPS cache check passed. No follow-up
  launched. Exact next proposed action: specify bounded replication or placement
  generalization comparison retaining .0001. Documentation whitespace checked.

- **2026-11-08 — Placement comparison authorized and launched:** user approved
  four versus sixteen placements/pitch, fresh shared four-placement validation.
  Contract [placement comparison](experiments/full_page_omr/docs/PLACEMENT_COMPARISON.md).
  Added fixed placement recipe and dedicated runner reusing evaluated training
  logic; explicit common checkpoint steps support unequal dataset sizes.
  New immutable dataset `outputs/placements_20261108_01`: 224 train/56 validation;
  control is 56-image subset identical to previous training images. Setup audit
  verified all 280 distinct resized inputs and existing image/source identities.
  Fixed 16800 updates (300/control image, 75/expanded), 600 active seconds each,
  medium decoder/lr .0001, same restored initial tensors/shared cached features.
  Full suite 87 tests: 86 passed/one skip (16.244s), log
  `/private/tmp/placement-tests.log`; new CPU wiring covers common checkpoints
  and exposure counts. Run `outputs/placement_mps_20261108_01` launched on MPS;
  dedicated command-prefix approval saved. Next action: monitor both versions,
  audit outputs and common evaluation, record conclusions. No results yet.

- **2026-11-08 — Placement comparison completed:** both versions finished
  16800 updates without cap; selected control 25/56 validation, expanded 48/56.
  Final training 56/56 and 224/224; final validation 24/56 and 48/56. All valid,
  donor correctness matches validation. Same initial weights/shared validation;
  300 vs 75 presentations/image. Active times 250.830s/259.479s. More placements
  improved single-seed interpolation at fixed updates; not broad OMR mastery.
  Audit recomputed all 1344 predictions/XML, summary/donor/selection/checkpoint
  metrics and exposures; data and implementation identities verified, no inference
  rerun. Report [placement comparison](experiments/full_page_omr/docs/PLACEMENT_COMPARISON.md).
  Full prelaunch suite 86 passed/one skip; actual MPS cache checks passed.
  No further run launched. Exact proposed next action: bounded second-seed
  replication. Documentation whitespace checked; all previous exports preserved.

- **2026-11-08 — Seed-19 placement repeat launched:** user authorized replication.
  Exposed CLI seed choice 7/19, leaving recipe unchanged. Dedicated placement
  wiring test passed (1.231s), CLI help and whitespace checked; previous full
  suite remains 86 passed/one skip. Same dataset, lr .0001, medium decoder,
  16800 updates/600 active seconds per version, fresh seed19 initialization/order.
  Run `outputs/placement_seed19_mps_20261108_01` launched using saved GPU command
  approval. Contract appended to placement report. Next action: monitor both
  versions, audit and compare with seed7; no further experiment queued.

- **2026-11-08 — Seed-19 placement repeat completed:** selected control 13/56,
  expanded 48/56 validation; expanded training 224/224, all valid. Expanded
  selected 11200/final 16800 tie, earliest selected. Control final validation
  10/56, 55 valid; training 33/56. Full trajectory/limits in placement report.
  Both 16800 updates, no cap; active 259.928/259.049s. Benefit replicated
  despite control seed sensitivity; only one expanded selected error shared
  with seed 7. Audit checked 1344 saved predictions/XML, totals/selection/hashes/
  exposures; features and fixed settings match seed 7, initialization differs.
  No inference rerun; MPS cache checks passed. Dedicated test and CLI checks passed.
  No further experiment launched. Next proposed action: inspect remaining error
  patterns and specify bounded generalization diagnostic. Whitespace checked.
