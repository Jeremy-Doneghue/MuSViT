# Medium decoder lower learning rate — 2026-11-08

> Historical report: the MusicXML-target implementation described here was
> retired on 2026-11-14. Commands and relative source links below describe the
> code at Git commit `1b57dfe`, not the current executable pipeline. See the
> [historical index](HISTORY.md) for retrieval and the
> [current pipeline](HUMDRUM_PIPELINE.md) for ongoing work. Results below are
> retained as recorded; this cleanup did not rerun these experiments.


Authorized comparison: lr .0001 versus completed .001 medium version in
`outputs/capacity_mps_20261108_01`. Same 4 layers/256 width, 3674982 trainable
parameters, frozen encoder, score targets and existing 56/56 all-pitches dataset.
Seed 7, AdamW/no decay, clip 1, batch 1, no dropout. Require exact saved initial
weight tensors and encoder feature hashes to match baseline before training.
Same image order and checkpoint selection. 16800 updates/300 presentations or
600 active training seconds; extraction/evaluation additional. Compare common
checkpoints if capped. Evaluate at 560/2800/5600/11200/16800 and any timeout.
Selected/final training and donor controls. No test scoring or new data.
One seed, fixed budget: smaller lr may need more steps; stability alone is not
recognition. Baseline preserved, fresh output only. No automatic extension.

## Executed result

Completed in `outputs/medium_lr_mps_20261108_01`, 16800 updates/300 presentations,
254.952 active training seconds, no time cap. Selected checkpoint is final.
Training exact/pitch/joint: 56/56; validation and donor: 32/56 (57.14%).
All 56 outputs valid in each control. Training gate passes; appearance/donor
fail, so overall gate fails. No test scoring or automatic advancement.

| Update | lr .001 validation correct | lr .0001 validation correct |
| --- | --- | --- |
| 560 | 7/56 | 4/56 |
| 2800 | 0/56, all invalid | 7/56 |
| 5600 | 0/56, all invalid | 10/56 |
| 11200 | 0/56, all invalid | 28/56 |
| 16800 | 0/56, all invalid | 32/56 |

All lower-lr validation outputs were valid. Previous selected medium training/
validation 8/56 and 7/56; previous final all invalid. This lower-lr run avoids
sustained collapse and masters training within the same exposure budget, but
new-placement generalization remains incomplete. Single seed, fixed simple
pitch task; no full-score or repertoire-transfer claim. No evidence yet about
longer-training plateau or a second-seed replication. Next proposed action:
choose a bounded replication or a separately specified appearance-generalization
comparison retaining lr .0001. No further run launched.

Audit: exact initial tensor equality, all 112 frozen feature hashes, dataset
integrity, identical order and per-image exposures versus prior medium run.
Recomputed all 504 predictions and valid XML exports, totals, donor metrics,
checkpoint selection and hashes. GPU inference not rerun. Saved
`independent_audit.json`; script `/private/tmp/audit_medium_lr_20261108.py`,
log `/private/tmp/medium-lr-audit.log`. Implementation hashes verified.
Full prelaunch suite: 86 tests, 85 passed/one sandbox MPS skip (15.415s).
Actual MPS cached/full-prefix check passed. Root initial metadata caveat from
capacity report also applies: actual initial weights are `medium_initial.pt`.
