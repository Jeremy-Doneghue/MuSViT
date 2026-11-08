# All-notes paired output-target comparison — 2026-11-06

Status: both versions and independent audit completed; neither passed the gate.
Contract below was fixed before launch. This compares output representations on taught pitches at new placements;
it is not a composition-disjoint benchmark or a complete compact score format.

## Shared dataset and target formats

Immutable export: `outputs/pitch_targets_20261106_01/`.
All 14 natural pitches C4–B5 occur in both training and validation. Each source
contains one quarter note in treble clef/C major/4/4, an explicitly short implicit
measure, Horn part name, voice/staff 1 and final barline. No musical variable
besides pitch is introduced. The one-note source helper and fixed engraving scale
are shared with the preceding pilot; earlier exports remain untouched.

- 56 training images: each pitch at source-raster translations (0,0), (24,0),
  (0,32), (24,32).
- 56 validation images: each pitch at (8,8), (16,8), (8,24), (16,24).
- All offsets refer to 1400-square rendered pages. Validation placements lie
  inside the training placement range; neither axis position occurs in training.
  All pitches have the same placement distribution. Inputs remain RGB [0,1],
  bilinear 1024-square resize. Translation preserves scale and refuses clipping.
- **14 independent pitch identities, four correlated images per identity per
  split.** Source scores and labels intentionally overlap. This is a finite
  appearance diagnostic, explicitly exempt from composition-family isolation;
  it makes no repertoire-generalization claim. The existing composition-disjoint
  adapters still reject this recipe. No existing test examples are loaded.

Every image has two labels:

| Version | Target | Length including BOS/EOS |
| --- | --- | --- |
| `score` | Existing `musvit-score-v1` complete score-tree stream | 157 tokens |
| `pitch` | `BOS V:step V:octave EOS`, e.g. BOS / V:E / V:4 / EOS | 4 tokens |

Both arms use the **same existing 614-token vocabulary and IDs**, including its
embedding/output layers. There is no constrained vocabulary, grammar masking or
classification head. Compact parsing requires exactly one of the 14 complete
four-token sequences; malformed/trailing/truncated outputs fail explicitly.

The compact writer uses the predicted pitch and the task's fixed context to
produce MusicXML. Quarter-note duration, clef, meter, key, part, voice/staff and
barline are **supplied by the experiment, not recognized** in that arm. The writer
matches each source score exactly for all 14 gold compact targets. The compact
format cannot represent variable rhythm, accidentals, polyphony or arbitrary
notations; future stages must predict any varying information explicitly.

## Matched model and compute contract

One frozen local encoder extraction is shared by both arms, with per-image
feature hashes recorded. One initial non-encoder state is saved and restored
tensor-for-tensor at each arm's start. Same width-128/two-layer autoregressive
decoder/adaptor, model positional capacity 256, 653,798 trainable parameters,
no dropout, batch size one, seed 7. Both optimizers are new AdamW instances,
constant lr .001, zero weight decay, clip norm 1. Same shuffled image order,
verified with an order hash. Arm order fixed: score first, pitch second.

Bound per arm: **300 presentations per training image / 16,800 updates, or 600
active training-loop seconds**, whichever occurs first. Frozen extraction,
autonomous validation, teacher diagnostics, checkpoint copies and final controls
are outside that time budget. Validation/checkpoints at 10/50/100/200/300 complete
presentations per image: updates 560/2800/5600/11200/16800. A time-limit endpoint
is evaluated too. Same update/presentation budget, not identical FLOPs: sequence
length differs. Report measured runtime and any unequal actual steps/order if a
time cap prevents matching. This is one seed, not a replicated architecture result.

Model capacity and weights at initialization are identical; only labels differ.
Unconstrained greedy generation starts from BOS and uses fixed caps independent
of each reference: 256 tokens for score, 8 for compact pitch. Valid compact output
must still terminate at exactly four tokens; the cap does not force an answer.
This changes sequence length and the fraction of loss assigned to musical values,
so a difference cannot isolate XML syntax alone from all optimization effects.

## Evaluation and selection

Checkpoint selection uses validation **pitch-correct count first**, validity
second, exact target count third; retain the earliest tied checkpoint. Aggregate
teacher-forced CE is diagnostic only and is not comparable across target formats.
All intermediate and final weights are preserved. No warm-start or early stopping
based on observed success; the fixed bounds govern the run.

Each scheduled checkpoint decodes all validation images. Selected and final
checkpoints additionally decode every training image and swap validation image
features between different pitches at the same placement. Swaps are measured
against recipient and donor labels. Save raw tokens, valid predicted MusicXML,
per-pitch totals, EOS, target exactness, musical equality, full-pitch correctness,
quarter-duration correctness and joint-event correctness. The compact arm's
duration correctness reflects supplied context. Invalid scores are unscorable
and receive no musical success credit; all-image denominators remain explicit.

Single-seed gate: at least 99% pitch/joint correctness and validity, and 95%
musical equality, on full training, new-placement validation and donor-reference
swaps. With 56 images, the 99% thresholds require 56/56. Passing does not
automatically advance the curriculum; the finite appearance test does not
establish composition, scan, handwriting, font or rhythm generalization.

Interpret the arms together: if compact outperforms score under matched image
exposure, the representation/training burden is implicated. If both succeed, the
new taught-pitch/appearance task is learnable under both targets. If both fail,
the comparison does not identify a single cause. Do not compare only against the
older withheld-pitch experiment and attribute the difference to serialization.

## Commands

```sh
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh
.venv/bin/python -m experiments.full_page_omr.training.pitch_target_experiment \
  --dataset experiments/full_page_omr/outputs/pitch_targets_20261106_01 \
  --output experiments/full_page_omr/outputs/pitch_targets_mps_20261106_01 \
  --encoder-weights model.safetensors \
  --encoder-config experiments/full_page_omr/outputs/studio_setup_20261031/encoder/config.json \
  --device mps --seed 7
```

For a new export, use `python -m experiments.full_page_omr.datasets.pitch_target_data
--output <new directory>`. Exports and runs refuse overwrite. Preserve partial
runs; no silent CPU fallback, dataset mutation or automatic retry.

## Setup verification

Tests cover strict compact grammar, exact MusicXML reconstruction for all pitches,
balanced shared-label/disjoint-placement policy, artifact/label tampering,
composition-adapter rejection, same-placement/different-pitch donors, common
musical metrics and pitch-first selection. A tiny random-encoder CPU wiring test
exercises both autoregressive arms with forced-EOS invalid outputs, both decode
caps, matching exposure/order and identical initialization checks. It is not a
learning result. Executed checks and results are recorded in the project diary.

## Executed result — 2026-11-06

MPS run `outputs/pitch_targets_mps_20261106_01/` completed both versions with
exactly **16,800 updates / 300 presentations of each training image**. No time
limit reached. Initial non-encoder weights were restored identically, all 112
frozen image features were shared, and the independently reconstructed shuffled
image-order hashes match. Same vocabulary/model/optimizer/lr, no test scoring.
The process exited successfully. Log:
`/private/tmp/musvit-pitch-target-training-20261106-01.log`.

| Selected checkpoint | Score target | Compact pitch target |
| --- | --- | --- |
| Selected update | 11,200 | 560 |
| Training pitch / joint / exact | 35/56 (62.50%) | 4/56 (7.14%) |
| New-placement pitch / joint / exact | 18/56 (32.14%) | 4/56 (7.14%) |
| Training / validation validity | 56/56 each | 56/56 each |
| Swapped-image correctness against donor | 18/56 | 4/56 |
| Gate | Fail | Fail |

The selected compact version predicts **B5 on every image**. Its accuracy equals
a constant guess on the balanced 14-pitch set; donor-prediction consistency is
therefore trivial. The selected score version varies with the image, but is
still inaccurate on both training and new placements.

Validation trajectory (correct pitch and exact target counts coincide):

| Presentations/image | Update | Score correct / valid | Compact correct / valid |
| --- | --- | --- | --- |
| 10 | 560 | 11/56 / 56/56 | 4/56 / 56/56 |
| 50 | 2800 | 10/56 / 56/56 | 0 successes / 0 valid |
| 100 | 5600 | 9/56 / 56/56 | 0 successes / 0 valid |
| 200 | 11200 | 18/56 / 56/56 | 0 successes / 0 valid |
| 300 | 16800 | 9/56 / 56/56 | 0 successes / 0 valid |

Final score version: training 8/56 and validation 9/56 correct/exact, all outputs
valid. Final compact version: no valid outputs on training/validation/swaps, so
musical values are unscorable and no success credit is earned. Of its 56 final
validation outputs, 17 reached EOS in a malformed stream and 39 hit the fixed
eight-token cap. The strict parser did not repair them or invent pitches; no
MusicXML was exported from invalid predictions. The writer itself passed all
gold-label checks and the audit of every valid predicted export.

Active training-loop times: **139.825 seconds score**, **142.173 seconds compact**.
Shorter targets did not reduce measured training-loop time in this execution.
Validation generation was much faster (roughly 27.5s versus subsecond for 56
images), but the compact outputs were inaccurate or invalid. Different target
lengths and fixed execution order limit conclusions about compute efficiency.
There is no accuracy-based reason to adopt the compact target from this run.

**Interpretation:** shortening the output alone, with this decoder and fixed
optimizer settings, did not improve learning. Neither version mastered even the
training set at the selected/final checkpoints. This does not prove compact
targets are intrinsically unsuitable or that XML generation is easy at full-score
scale: sequence length, content loss weighting and optimization change together,
and one shared learning rate was not separately tuned for each target. This is
one seed on 14 shared labels and four placements per label. It does establish
that serialization length alone has not solved our current training problem.

Recommended next diagnostic: a bounded direct 14-way pitch readout from frozen
features on this same known-label task, removing sequence generation entirely.
Separately investigate optimization stability; any changed-lr comparison must
be specified before running. Neither follow-up has been launched.

Independent CPU audit recomputed **all 1008 saved predictions** and checked all
**672 valid MusicXML exports**, 336 dataset artifact hashes, implementation/input
hashes, checkpoint identities and snapshots, paired targets, per-pitch/total
metrics, selection/tie rules, reconstructed exposures/order, donor/layout pairing,
donor-prediction consistency and all gate decisions. All 112 recorded frozen
feature hashes are distinct. Saved `independent_audit.json` under the run;
script/output `/private/tmp/audit_pitch_target_run_20261106.py`,
`/private/tmp/musvit-pitch-target-run-audit-20261106.json`.
The audit did not rerun GPU inference. Prelaunch full suite: 86 tests, 85 passed,
one sandbox MPS skip, 14.151s; log
`/private/tmp/musvit-pitch-target-full-tests-20261106.log`. Actual MPS training
and cached/full-prefix agreement checks passed for both versions. No production
source changed after launch; documentation whitespace checked after reporting.
