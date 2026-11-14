# Small versus medium decoder — 2026-11-08

> Historical report: the MusicXML-target implementation described here was
> retired on 2026-11-14. Commands and relative source links below describe the
> code at Git commit `1b57dfe`, not the current executable pipeline. See the
> [historical index](HISTORY.md) for retrieval and the
> [current pipeline](HUMDRUM_PIPELINE.md) for ongoing work. Results below are
> retained as recorded; this cleanup did not rerun these experiments.


Authorized bounded comparison; contract recorded before execution.
Existing immutable dataset: `outputs/pitch_targets_20261106_01` (56/56 images,
14 taught pitches with correlated new-placement validation, not repertoire transfer).
Score targets only, same 614-token vocabulary and 157-token labels.
Frozen encoder features extracted once and shared. Fresh seed 7 initialization
per model; different dimensions necessarily mean different initial weights.
Small: 2 layers, width 128, 653798 trainable parameters.
Medium: 4 layers, width 256, 3674982 trainable parameters.
Same AdamW .001/no decay, norm clip 1, batch 1, no dropout, shuffled image order.
Each bounded at 16800 updates/300 presentations or 600 active training seconds;
extraction and evaluation additional. Checkpoints at 560/2800/5600/11200/16800
and any timeout endpoint. Compare common checkpoints if exposure differs.
Selection: validation pitch correctness, validity, exactness, earliest tie.
Selected/final training and swapped-image controls retained. No test scoring.
Single seed and optimizer setting: capacity/optimization interaction unresolved.
This is not a reproduction of the published model or evidence of full-score reading.

Launch uses `training.pitch_target_experiment --capacity-comparison` with existing
encoder weights/config and a new output directory. No prior artifacts overwritten.

## Executed result

Run `outputs/capacity_mps_20261108_01` completed 16800 updates per model,
300 presentations/image, identical order hashes, shared features, no time cap.
Active training: small 139.675s; medium 257.556s. Evaluation/extraction additional.

| Outcome | Small | Medium |
| --- | --- | --- |
| Selected update | 2800 | 560 |
| Selected training correct/exact | 7/56 | 8/56 |
| Selected validation/donor correct/exact | 10/56 | 7/56 |
| Selected validity (each set) | 56/56 | 56/56 |
| Final training correct/exact | 4/56 | 0/56 |
| Final validation/donor correct/exact | 9/56 | 0/56 |
| Final validity (each set) | 56/56 | 0/56 |

Validation correct counts at 560/2800/5600/11200/16800:
small 8/10/5/8/9; medium 7/0/0/0/0. Medium loss rose to about 3.17 by
2800 and stayed there; all later evaluated outputs invalid. Neither passes gates.
Extra capacity did not help at this common learning rate. Cause of collapse
unisolated; no conclusion that medium capacity is unsuitable. Proposed next
step: bounded lower-lr comparison, not launched. User clarified the one-note
question was exploratory, not a direction change.

Each version reseeded immediately before decoder construction, unlike the older
paired run which seeded before encoder construction too; fresh small is not an
exact historical replay. Compare capacities within this run. Root `initial.pt`
and top-level hash describe unused preliminary construction; actual initial
states are `small_initial.pt` and `medium_initial.pt`, hashed in config `versions`.
`initial_state_identical` means restoration within version, not across capacities.

Full prelaunch suite: 86 tests, 85 passed/one sandbox MPS skip. Actual MPS
cached/full-prefix checks passed both models. CPU audit recomputed all 1008 saved
predictions, valid XML exports, summaries/donor totals, checkpoint selection/hashes
and exposures. Dataset integrity and implementation hashes verified. No inference
rerun. Audit `independent_audit.json`, script `/private/tmp/audit_capacity_20261108.py`,
log `/private/tmp/capacity-audit.log`; training `/private/tmp/capacity-training-20261108.log`.
