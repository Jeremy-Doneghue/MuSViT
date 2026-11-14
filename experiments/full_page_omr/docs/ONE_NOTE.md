# Bounded one-note pitch pilot — 2026-11-06

> Historical report: the MusicXML-target implementation described here was
> retired on 2026-11-14. Commands and relative source links below describe the
> code at Git commit `1b57dfe`, not the current executable pipeline. See the
> [historical index](HISTORY.md) for retrieval and the
> [current pipeline](HUMDRUM_PIPELINE.md) for ongoing work. Results below are
> retained as recorded; this cleanup did not rerun these experiments.


Status: short and longer seed-7 MPS runs and controls completed; held-out transfer
failed. The longer run mastered training at 16k/24k, then regressed. This is
the first recognition diagnostic in the proposed curriculum, not the full
curriculum or a comparison showing that curriculum improves learning.

## Question and fixed scope

Can the current frozen encoder and small decoder learn one quarter note in staff
context, and read absolute pitch positions absent from training? Keep the existing
codec, RGB input, encoder, learning rate and decoder architecture. This reduces
sequence/content difficulty without simultaneously changing the representation.
Rhythm discrimination, clef changes, accidentals and encoder adaptation are later
experiments. Correct duration here only checks a fixed value; it does not establish
rhythm recognition.

## Dataset and honest denominators

Immutable export: `outputs/one_note_pitch_20261106_03/`, recipe
`one-note-pitch-v1`. Generation is deterministic and does not sample random scores.

- Treble clef, C major, 4/4; exactly one quarter note, voice/staff 1, and final
  barline. The sole measure is explicitly `implicit="yes"`, making the short
  measure valid without introducing filler rests or a pitch-dependent duration.
- Support: the 14 natural pitches C4–B5. Training has C4, D4, F4, G4, B4, C5, E5,
  F5, A5, B5; validation has E4, A4, D5, G5. Every step name and both octave values
  occur in training, but the four held-out absolute staff positions do not.
- Eight fixed page translations per pitch: horizontal offsets 0/8/16/24 pixels
  crossed with vertical offsets 0/32 pixels in the 1400-square source raster.
  Every pitch uses exactly the same offsets. Translation preserves scale and
  refuses to clip notation. Both splits share these layouts; this is not a
  held-out-layout or font-generalization experiment.
- **80 training images / 10 musical targets; 32 validation images / four musical
  targets.** The eight translations are correlated variants, not independent
  compositions. All variants of an absolute-pitch source stay in one split.
  No test export or access to existing test data.
- Square pages preserve the existing 1024-square input path and engraving scale
  (Verovio scale 55). No tight cropping, degradation or per-image normalization.
  All targets contain 157 tokens; fixed generation cap is 256.

The general clean-page fingerprint intentionally ignores transposition, which
would identify *every* source here as the same musical pattern. This pilot uses
an explicitly documented **absolute-pitch semantic fingerprint** to test unseen
pitch positions. It cannot satisfy the stronger composition/transposition-family
isolation standard of a repertoire benchmark and must not be reported as such.
The earlier proposed 100-held-out-family gate is inapplicable to this finite task;
do not manufacture independent families by rendering more copies. Full musical
source/family/target/raster isolation still applies to subsequent repertoire work.

Exports verify codec round trips, rendered measure presence, one system, square
page geometry, translation bounds, source/target/image hashes, fixed token cap
and cross-split collisions. Original renders and sources are retained; the
manifest records each translated raster's source and family. Exports refuse
overwrite. Setup attempts `-01` and `-02` are preserved incomplete exports: an
initial renderer setting cropped the page; the final recipe uses encoded layout
and explicitly checks square geometry. They are not training inputs.

## Training bound and checkpoint selection

Fresh decoder/adaptor, seed **7**, width 128, two decoder layers, batch size 1,
1024 RGB, frozen local encoder, AdamW lr .001, zero weight decay/dropout. No
warm-start, grammar constraints, label truncation, repair or automatic curriculum
advancement. No encoder or codec changes.

Hard wrapper limits: **8000 updates or 300 training-loop seconds**, whichever
comes first; validation every 400 updates. Full completion gives exactly 100
presentations per training image. The shared timer includes periodic validation
and checkpoint writes; it is checked between updates, not an interruptible wall
timeout. Dataset loading, feature extraction, initial diagnostics and post-run
decoding/controls are outside this time bound. Decoding has its own fixed
256-token cap per image. Minimum validation gold-prefix cross entropy selects
`best.pt`; `last.pt` is reported separately. CE does not establish recognition.

Seed **19** is the predefined replication, run separately in a new output
directory after reviewing seed 7. Neither run nor a learning-rate sweep launches
automatically. Checkpoints retain the existing format; they are not exact
optimizer/RNG continuation snapshots.

## Evaluation and gates

For both selected and final checkpoints, `one_note_controls/result.json` reports:

- Autonomous transcription of **all 80 training images**, all 32 validation
  images, and validation swaps. The shared trainer's three-example sample remains
  in its own result but is not the mastery criterion.
- Exact token sequence, complete semantic validity/equality, EOS, full pitch
  (step, alteration, octave), duration and joint single-event correctness.
  Invalid outputs remain musically unscorable. An all-image success rate counts
  them as failures; they are never excluded to inflate accuracy. Valid multi-note
  outputs also fail the single-event criteria. Per-held-out-pitch results expose
  whether success is concentrated on one position.
- Image swaps between **different pitches at the same layout offset**, scored
  against both recipient and donor references. Donor correctness establishes
  actual reading; merely reproducing a donor's incorrect prediction does not.
- Matched/swapped gold-prefix field accuracy and CE, explicitly separate from
  autonomous metrics. Training-label priors cannot predict the four held-out
  full pitches; fixed duration has a trivial 100% prior.

The single-seed gate requires at least **99% validity, 99% joint-event accuracy
and 95% exact transcription** on each of full training, matched validation and
swaps against donor targets. On 32 validation images the 99% thresholds require
32/32 successes. These are engineering thresholds on a tiny finite support, not
statistical guarantees or the broader 100-family advancement gate. Selected is
primary; a final-only pass is an optimization finding, not a selected-model pass.
Replication is required before recommending advancement; the report never
automatically authorizes a later curriculum stage.

If training fails, inspect visual-feature accessibility with a local pitch probe
and then a controlled learning-rate comparison. If training succeeds and held-out
positions fail, investigate position transfer/encoder adaptation on this fixed
task. If selected passes and replication confirms it, propose the next duration
diagnostic, followed by combined pitch/duration holdouts. Broader PDMX training
remains deferred.

## Commands

Run from the repository root. Existing outputs must remain untouched.

```sh
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh
.venv/bin/python -m experiments.full_page_omr.training.one_note_experiment train \
  --dataset experiments/full_page_omr/outputs/one_note_pitch_20261106_03 \
  --output experiments/full_page_omr/outputs/one_note_pitch_mps_NEW \
  --encoder-weights model.safetensors \
  --encoder-config experiments/full_page_omr/outputs/studio_setup_20261031/encoder/config.json \
  --device mps --seed 7
```

New immutable export and evaluation-only recovery (when controls have not begun):

```sh
.venv/bin/python -m experiments.full_page_omr.datasets.one_note_data \
  --output experiments/full_page_omr/outputs/one_note_pitch_NEW
.venv/bin/python -m experiments.full_page_omr.training.one_note_experiment evaluate \
  --run experiments/full_page_omr/outputs/one_note_pitch_mps_NEW
```

Controls refuse to overwrite an existing `one_note_controls` directory. Preserve
partial controls before retrying. Input/checkpoint identity is checked before
evaluation. There is no silent CPU fallback for MPS training.

## Setup verification

The dedicated tests cover finite pitch support, complete short-measure semantics,
round trips, source-grouped translations, same-layout/different-pitch donors,
cross-split collision rejection, tampered image hashes, no overwrite, wrong-octave
and invalid-output scoring, gate behavior and hard training limits. A one-update
CPU wiring test uses a tiny random encoder and forced EOS outputs to exercise
training and both checkpoint controls; it is not recognition evidence. Executed
checks and independent export audit are recorded in the project diary.

## Executed seed-7 result — 2026-11-06

User requested execution. Run `outputs/one_note_pitch_mps_20261106_02/` completed
all **8000 updates** and exactly **100 presentations per training image** in
**73.728 training-loop seconds**, without reaching the time limit. Feature
extraction, decoding and controls are additional. Minimum validation gold-prefix
CE selected update **1600**. Original encoder frozen, no codec/model changes,
no test scoring. The process and controls exited successfully.

The first attempt (`one_note_pitch_mps_20261106_01/`) stopped before initialization
because sandbox MPS access was unavailable. That directory is preserved. The
actual run used approved GPU access outside the sandbox and a fresh output
directory. Log: `/private/tmp/musvit-one-note-training-20261106-02.log`.

| Outcome | Selected, update 1600 | Final, update 8000 |
| --- | --- | --- |
| Full training valid | 80/80 | 80/80 |
| Full training pitch / joint-event / exact | 8/80 (10%) | 15/80 (18.75%) |
| Held-out valid | 32/32 | 32/32 |
| Held-out pitch / joint-event / exact | 0/32 | 0/32 |
| Swaps: correct donor pitch / exact | 0/32 | 0/32 |
| Fixed quarter-note duration | 100% | 100% |
| Held-out token error | 0.9554% | 0.8161% |
| Preregistered gate | Fail on all three checks | Fail on all three checks |

All 294 saved autonomous outputs reached EOS and were complete valid scores,
including the trainer's six sampled training outputs. Pitch error is the decisive
failure; valid output and less than 1% token error mostly reflect the 155 or so
predictable structural/constant tokens. Fixed-duration correctness does not test
rhythm discrimination. Validation has four independent absolute-pitch targets,
each with eight layout variants, not 32 independent musical examples.

The selected checkpoint predicts **F5 for every training and validation image**.
Its 10% training accuracy equals a constant pitch guess on the balanced ten-pitch
training support. At the final checkpoint, training predictions are F5 (50),
F4 (20) and B5 (10); validation predictions are F5 (21), F4 (9) and B5 (2).
Neither checkpoint predicts any of the four held-out pitches correctly.

Swaps reproduce the donor image's own matched prediction 32/32 at both checkpoints.
For the selected checkpoint this is trivial because its output is constant.
At the final checkpoint image-dependent variation exists, but donor references
are still wrong 32/32: this does not establish pitch reading.

Validation gold-prefix diagnostics (separate next-token fields, not joint notes):

| Field accuracy | Selected matched / swapped | Final matched / swapped |
| --- | --- | --- |
| Pitch step | 0% / 0% | 0% / 0% |
| Octave | 50% / 50% | 71.875% / 46.875% |
| Duration | 100% / 100% | 100% / 100% |

**Interpretation:** even the training pitch task was not mastered. This is not a
clean held-out generalization failure, and the result does not justify advancing
to rhythm, longer passages or PDMX. It narrows the next investigation to visual
feature accessibility and optimization on this elementary task; it does not prove
that the encoder lacks pitch information or that curriculum learning cannot work.
Next proposed action: a bounded local pitch probe using the same frozen encoder,
with training-fit and held-out-position measurements, followed by a controlled
learning-rate comparison if warranted. Seed-19 replication remains unrun; no
additional experiment was launched.

Independent CPU audit recomputed musical correctness for all 294 saved autonomous
predictions, checked both checkpoint identities, all 336 dataset artifact hashes,
input hashes, exact presentation counts, donor/layout pairing, donor prediction
agreement, reported totals and gate decisions. Saved `independent_audit.json`
under the run; script `/private/tmp/audit_one_note_run_20261106.py`, output
`/private/tmp/musvit-one-note-run-audit-20261106.json`. Gold-prefix fields were
read from the executed GPU controls, not independently rerun. Actual MPS training
and the shared cached/full-prefix decoder agreement check passed. No source code
changed during this run; the setup's 82-test suite remains the latest regression
check (81 passed, one sandbox MPS skip).

## Longer-run comparison — contract fixed before launch, 2026-11-06

The user authorized the proposed longer run. Fresh initialization, seed 7, same
immutable dataset and weight/config files, same model, constant learning rate,
optimizer, shuffle procedure and validation CE selection every 400 updates.
Bound: **40,000 updates or 900 training-loop seconds**, whichever occurs first.
Full completion gives 500 presentations per training image. No decoder-weight
warm-start: the previous run lacks optimizer/RNG continuation state.

The explicit `--extended` flag allows this fixed higher bound while retaining
the original limits for ordinary pilot invocations. The shared trainer now
optionally saves snapshots at 8000/16000/24000/40000 updates. Snapshot saving does
not draw random numbers, perform inference or change optimization; a CPU wiring
test compares final weights with/without snapshots for equality. At each reached
snapshot, decode all 80 training and 32 validation images **after training** using
the fixed 256-token cap, recording validity, full pitch/joint correctness and
exactness. Final snapshot outputs reuse the existing final evaluation. Unreached
snapshot steps are reported explicitly if the time cap stops training early.
Selected and final checkpoints still receive the full image-swap and gold-prefix
controls. Intermediate musical results are diagnostic; they do not select weights
or automatically advance the curriculum. Extraction and post-run decoding remain
outside the training-loop time cap.

Run directory: `outputs/one_note_pitch_long_mps_20261106_01/` (new, refuses overwrite).

```sh
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh
.venv/bin/python -m experiments.full_page_omr.training.one_note_experiment train \
  --dataset experiments/full_page_omr/outputs/one_note_pitch_20261106_03 \
  --output experiments/full_page_omr/outputs/one_note_pitch_long_mps_20261106_01 \
  --encoder-weights model.safetensors \
  --encoder-config experiments/full_page_omr/outputs/studio_setup_20261031/encoder/config.json \
  --device mps --seed 7 --extended --steps 40000 --max-train-seconds 900
```

No change to the finite pitch-support limitation, preregistered gate, test boundary
or dataset fingerprint policy. A fresh seed does not guarantee exact MPS replay;
compare the new 8000-update snapshot against the previous final checkpoint before
interpreting later changes as a continuation of the earlier trajectory.

## Executed longer-run result — 2026-11-06

The authorized run completed all **40,000 updates / 500 presentations per training
image** in **343.255 training-loop seconds**, without reaching the 900-second
limit. Feature extraction and post-run decoding are additional. Run directory:
`outputs/one_note_pitch_long_mps_20261106_01/`; log:
`/private/tmp/musvit-one-note-long-training-20261106-01.log`. MPS process exited
successfully, original encoder frozen, same dataset/weights/model/lr/optimizer,
no warm-start, no test scoring. Validation CE again selected update **1600**.

| Checkpoint | Training valid | Training pitch / joint / exact | Held-out valid | Held-out pitch / joint / exact |
| --- | --- | --- | --- | --- |
| Selected, 1600 | 80/80 | 8/80 | 32/32 | 0/32 |
| Snapshot, 8000 | 58/80 | 21/80 | 26/32 | 0/32 |
| Snapshot, 16000 | 80/80 | **80/80** | 32/32 | **0/32** |
| Snapshot, 24000 | 80/80 | **80/80** | 32/32 | **0/32** |
| Final, 40000 | 0/80 | 0 successes; all invalid | 0/32 | 0 successes; all invalid |

Pitch, joint-event and exact counts coincide at these snapshots. Invalid outputs
are musically unscorable and cannot earn success credit; zero successes at the
final checkpoint do not measure the pitches inside invalid sequences. Validation
still represents four absolute pitches with eight correlated translations each.

**More training did establish training-set mastery.** Autonomous decoding at
16k and 24k transcribes every training image correctly, including all ten pitches
and all eight layouts. The frozen encoder/decoder pipeline therefore has enough
visual information and capacity to distinguish and memorize this finite training
set. This supersedes the initial 8k result's conclusion that training recognition
had not been established. It does not establish generalizable pitch reading:
all four held-out pitches remain wrong at both mastered snapshots. Valid held-out
outputs at 16k/24k use training-support pitches; no held-out reference is correct.

**Training later regressed sharply.** Loss had approached zero, then jumped
around 28k (the first logged post-20k example with loss above 1 is update 28000).
By 40k, all final training/validation/swap outputs plus the three sampled training
outputs—147 predictions—hit the 256-token cap without EOS or valid scores.
The snapshots preserve the earlier learned state. The cause of this late
instability has not been isolated; a learning-rate/schedule comparison is a
candidate, not an executed explanation. Intermediate results do not replace the
predeclared validation-CE checkpoint selection or authorize advancement.

Selected predicts F5 on every image; selected donor-reference accuracy is 0/32.
Final donor-reference outputs are all invalid. Both selected/final gate reports
fail all three checks. Intermediate checkpoints were measured for autonomous
training/validation recognition as planned; they did not receive extra swap or
gold-prefix runs. Their held-out failure is already sufficient to fail transfer.

**Fresh-run comparison limit:** the new 8k snapshot differs from the original
8k run's final weights in all 57 trainable tensors (maximum absolute difference
1.259953). Its training exactness is 21/80 versus the original 15/80, and validity
also differs. The same seed/settings did not give a bit-exact replay; the cause
of that numerical divergence was not isolated. This is a fresh longer-run
comparison, not an exact continuation. The strongest learning-over-time evidence
is the within-run 8k → 16k → 24k → 40k trajectory.

Independent CPU audit verified all **630 saved autonomous predictions**, all
336 dataset artifact hashes, input/checkpoint identities, exposure counts,
selected/final totals and gates, donor/layout pairing and donor prediction
consistency. It recomputed all intermediate musical totals, verified the final
snapshot matches `last.pt` tensor-for-tensor, and compared the 8k snapshot with
the previous run. Saved `independent_audit.json` under this run; script/output:
`/private/tmp/audit_one_note_long_run_20261106.py`,
`/private/tmp/musvit-one-note-long-run-audit-20261106.json`. Gold-prefix fields
were read from executed selected/final GPU controls, not independently rerun.
Prelaunch full regression suite: 82 tests, 81 passed/one sandbox MPS skip;
`/private/tmp/musvit-one-note-long-tests-20261106.log`. Snapshot tests include
identical CPU final weights with/without saving snapshots. Actual MPS training
and cached/full-prefix decoder agreement passed. No code changed during execution.

No further run is queued. Next candidates are a bounded pitch-feature/readout
probe to investigate unseen staff-position transfer and a controlled lower-lr or
decaying-lr run to investigate late instability. Keep these questions separate;
neither PDMX scaling nor a full-codec rewrite follows from this result.

## Curriculum interpretation reconsidered — 2026-11-06

The user questioned withholding whole pitches during the first learning stage.
The existing validation tests inference of untaught absolute staff positions;
it does not measure new images of taught notes or new sequences made from taught
notes. Its results remain valid for that harder question, but using this holdout
as the initial curriculum gate was premature. At 16k/24k, the model has learned
every taught training example, a useful first-stage result.

Revised recommendation (not implemented or launched): teach every pitch in the
chosen range, then test the same labels on controlled new renderings/placements.
Report this finite rendering assessment explicitly, without claiming source-family
isolation or treating raster variants as independent compositions. Subsequent
short-passage datasets should test unseen sequences of known notes with complete
composition-family grouping. Retain unseen absolute pitches as a separate later
rule-inference diagnostic. Keep encoder/decoder/codec fixed, specify musical
accuracy/validity selection and training bounds in advance, and handle the late
optimization regression as its own controlled comparison.
