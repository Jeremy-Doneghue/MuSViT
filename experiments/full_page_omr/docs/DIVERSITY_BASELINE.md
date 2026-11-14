# Clean composition diversity experiment — 2026-11-01

> Historical report: the MusicXML-target implementation described here was
> retired on 2026-11-14. Commands and relative source links below describe the
> code at Git commit `1b57dfe`, not the current executable pipeline. See the
> [historical index](HISTORY.md) for retrieval and the
> [current pipeline](HUMDRUM_PIPELINE.md) for ongoing work. Results below are
> retained as recorded; this cleanup did not rerun these experiments.


User reauthorized experiments on 2026-11-01. Test whether increasing clean
training diversity improves validation recognition at a fixed update budget.

## Declared comparison

Expand seed-71 `clean-page-v1` training from 36 to 180 compositions (60 per
instrument). Keep the original 36 as an exact subset and all six validation
pages identical, verified by source/target/raster hashes before training.
Use a new immutable export `outputs/clean_pages_180_20261101_01/`.
Cross-split collision checks and semantic round trips remain mandatory.
The standard exporter also reproduces six test records; training uses
`--skip-test` so these are not loaded or scored by the experiment.

Run `outputs/clean_diversity180_mps_20261101_02/`: fresh adaptor/decoder,
seed 7, original frozen encoder, width 128/two layers, 1024 RGB input,
614-token vocabulary, AdamW lr 0.001, batch size 1, fixed 8192 token cap,
validation every 200 updates, no augmentation or grammar masks.
Bound: 14400 updates or 1800 training-loop seconds, whichever comes first.
Evaluate both validation-selected and final checkpoints on all six validation
pages and the original first three training pages. Test scoring disabled.

Compare with [the longer 36-page run](LONG_BASELINE.md), keeping checkpoints
separate. Primary outcomes: autonomous valid/exact pages, EOS and token error;
musical structural errors only when valid scores permit scoring. Follow with
gold-prefix pitch/duration and image-swap diagnostics if needed.

At 14400 updates, exposure is 80 presentations/page versus 400 previously.
This is a fixed-update-budget comparison, not an equal-exposure experiment or
a pure causal isolation of diversity. One seed and six validation pages limit
conclusions. No claim about degraded scans, handwriting or broader notation.

## Status

Export completed; 576 artifact hashes passed, all 48 original records identical,
all pages four systems. Six focused tests passed. Final results are recorded below.
Initial `_01` interrupted after last logged update 950 (checkpoint at 800) following
host memory compression/slower updates. Preserved partial artifacts. Retry `_02`
adds unused MPS cache release before encoder/teacher pages and every 25 training
updates; no live-tensor/math changes. This is not a controlled allocator benchmark.
Retry log: `/private/tmp/musvit-diversity180-training-retry-20261101.log`. Export log:
`/private/tmp/musvit-export180-20261101.log`. Training and verification results
will be recorded after execution.


## Executed result

Retry `_02` completed all 14400 updates, exactly 80 presentations/page, in
1240.17 training-loop seconds. No time cap, encoder adaptation or test scoring.
Selected checkpoint: update 11200. Independently recomputed all 18 saved
prediction metrics with the unchanged codec; saved `independent_audit.json`.

| Checkpoint | Train sample exact / valid | Validation exact / valid | Validation EOS | Validation token error |
| --- | --- | --- | --- | --- |
| Selected, 11200 | 0/3 / 0/3 | 0/6 / 0/6 | 6/6 | 31.407% |
| Final, 14400 | 0/3 / 0/3 | 0/6 / 0/6 | 6/6 | 20.827% |

All 18 outputs reached EOS without hitting the token cap. Some codec errors say
“truncated token stream”: these refer to incomplete structures despite EOS,
not length-cap termination. Other failures include nested notes, unsupported
placement of directions, measure under/overfill, backup before measure start,
and duration/type disagreement. All structural musical error counts are
unscorable, not zero. No outputs could be re-engraved as valid predictions.

Selected/final validation gold-prefix CE: 0.0779173 / 0.0818730, versus
0.339914 / 0.663299 in the longer 36-page run. Final validation token error is
20.827% versus 30.267%, but selected token error is 31.407% versus 28.027%.
Final sampled training token error is 17.765%, versus zero previously.
Greater diversity at this update budget improves some metrics but still fails
usable autonomous recognition and now includes sampled training underfitting.
Do not describe it as a clean generalization-gap result or proof that scaling
alone solves recognition. Gold-prefix selection did not select the checkpoint
with lower autonomous token error; no selection rule changed after scoring.

Peak process RSS 7,513,096,192 bytes; final sampled MPS driver allocation
3,874,471,936 bytes (not GPU peak). Full suite: 70 tests, 69 passed and one
sandbox MPS skip. Real GPU run exercised backward and prefix/cache agreement.
Whitespace checks passed. Data/weights remain ignored; no commit performed.

Next proposed diagnostic: compare unconstrained and grammar-constrained decoding
on the same checkpoint and fixed validation pages, without retraining. User
raised this technique during the run; discussion does not establish efficacy.
Use only codec/profile rules, never reference target lengths or contents.
Report syntactic validity, musical validity, EOS, exactness/token errors and
valid-subset musical errors separately. Syntax constraints alone cannot enforce
visual fidelity or all duration/voice consistency. Preserve the existing baseline.


## Field and image-conditioning diagnostics

Executed `clean_page_diagnostics` on CPU for both saved checkpoints, verifying
checkpoint/input hashes, first six train pages and all six validation pages.
No training, test scoring or selection changes.

| Gold-prefix diagnostic | Selected | Final |
| --- | --- | --- |
| Validation pitch-step accuracy (247 tokens) | 23.89% | 23.48% |
| Validation duration-value accuracy (564 tokens) | 61.88% | 60.64% |
| Train same-instrument swap CE increase | +0.005124 | +0.002749 |
| Validation same-instrument swap CE change | -0.000462 | +0.001201 |

Pitch/duration metrics improve over the previous run but remain weak. Swaps
barely affect loss on this control, suggesting weak image conditioning here.
These are gold-prefix token measurements, not autonomous note accuracy or proof
of complete image independence. Grammar constraints may address invalid structure;
they do not supply the missing evidence of reliable visual note recognition.


## Longer-training comparison started — 2026-11-01

Following the grammar comparison, user emphasized learning musical relationships
through more training/data, under existing authorization to continue experiments.
Start a fresh decoder on the same 180 compositions with identical seed 7, frozen
encoder, architecture, lr, resolution, validation interval and target cap. Increase
only the bound to 36000 updates (200 presentations/page) or 3600 training-loop
seconds. Keep validation fixed and test scoring disabled. Fresh initialization
preserves the shorter run's schedule as a comparable prefix, subject to MPS
numerical nondeterminism; this is not checkpoint continuation or an optimizer reset.

Run: `outputs/clean_diversity180_long_mps_20261101_01/`. Training log:
`outputs/studio_setup_20261031/diversity_long_training_20261101.log`.
Orchestrator: `outputs/studio_setup_20261031/run_diversity_long_20261101.py`.
After successful training, it runs both saved checkpoints through constrained
validation evaluation, then CPU field/image-swap diagnostics, failing on errors.
Constrained output: `outputs/constrained_diversity180_long_20261101_01/`.
The 60-minute bound covers training/validation/checkpoint work; initialization and
final decoding/diagnostics are additional. No larger export or meter variation.

Hypothesis: additional exposure improves autonomous musical consistency and
visual conditioning. This remains unproven. All current examples use 4/4 and C
major, so this run cannot demonstrate generalization across time signatures.
Do not interpret rhythm consistency alone as image-dependent note recognition.
Compare selected/final checkpoints separately against the 14400-update run;
retain exactness, validity, token errors, pitch/duration diagnostics and swaps.
No result claimed at launch. Exact next action: inspect run result and queued
comparison/diagnostic completion, independently verify predictions, then document
results before selecting more data or architecture changes.


## Longer-training result

All 36000 updates completed, exactly 200 presentations/page, in 3450.78 seconds
(57.51 minutes) of training/validation/checkpoint work; no time cap hit. Selected
update 27600. Both decoding comparisons and CPU field/swap diagnostics completed.
Original encoder frozen, test untouched. No complete valid predictions to re-engrave.

| Checkpoint | Train sample valid | Validation valid | Unconstrained validation token error | Constrained validation token error |
| --- | --- | --- | --- | --- |
| Selected, 27600 | 0/3 | 0/6 | 23.210% | 22.870% |
| Final, 36000 | 0/3 | 0/6 | 24.397% | 36.933% |

Exactness is zero throughout; constrained validation validity is also 0/6 for
each checkpoint. All 30 autonomous outputs reached EOS, no token-cap termination.
All 12 constrained outputs completed the grammar (9/51 interventions selected/final).
Structural musical errors remain unscorable, not zero. Remaining errors include
measure under/overfill, duration/type mismatches and part-ID/order inconsistency.

Relative to the shorter 14400-update experiment, selected unconstrained error
improved from 31.407% to 23.210%, but final error worsened from 20.827% to 24.397%.
There is no consistent recognition improvement, and sampled training still fails.
This does not prove that more data cannot help; it does not justify assuming that
simply extending this configuration will solve recognition either. MPS numerical
nondeterminism means the fresh runs are not guaranteed identical update prefixes.

Gold-prefix selected/final validation CE: 0.0799340/0.117557; training CE:
0.0387232/0.0387453. Selected/final validation pitch-step accuracy 27.13%/25.91%
(247 tokens); duration-value accuracy 65.07%/64.54% (564 tokens). Validation
same-instrument image-swap CE change -0.003995/-0.002085; train +0.003169/+0.004962.
Musical-field prediction remains weak, and this swap control shows little benefit
from matched images. These are gold-prefix diagnostics, not autonomous note accuracy.

Peak process RSS 8,216,035,328 bytes; final sampled MPS allocation 6,021,955,584
bytes, not GPU peak. Completion review independently recomputed all 30 prediction
metrics, verified 200 exposures per page and run contract, saving independent_audit.json.
No source code changed during the completion review; no new tests or training run.

Next proposed action: inspect why the model uses images so weakly before allocating
another longer run—use a bounded visual pitch/rhythm recognition diagnostic with
controlled positions and unseen examples, then decide whether visual adaptation,
training setup or data coverage should change. Exact diagnostic design is open;
no follow-up run is queued.
