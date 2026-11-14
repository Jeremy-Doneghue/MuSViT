# Placement comparison — 2026-11-08

> Historical report: the MusicXML-target implementation described here was
> retired on 2026-11-14. Commands and relative source links below describe the
> code at Git commit `1b57dfe`, not the current executable pipeline. See the
> [historical index](HISTORY.md) for retrieval and the
> [current pipeline](HUMDRUM_PIPELINE.md) for ongoing work. Results below are
> retained as recorded; this cleanup did not rerun these experiments.


Authorized contract fixed before launch. Medium 4x256, lr .0001, frozen encoder,
score target, seed 7, same initial tensors restored for each version. Batch 1,
AdamW/no decay, clip 1, no dropout. Source labels/pitches unchanged.

Control: 4 placements/pitch (0,0),(24,0),(0,32),(24,32): 56 images.
Expanded: Cartesian x={0,8,16,24}, y={0,8,24,32}: 224 images, includes control.
Shared fresh validation: (4,4),(20,4),(4,28),(20,28): 56 images. Neither axis
coordinate used for training. Old validation locations may be training here;
old development examples are not a held-out test. This is interpolation within
same translation range, not full-page reading or source-disjoint generalization.
Only 14 independent pitch identities; do not treat variants as independent pieces.

Same 16800 updates: 300 presentations/control image, 75/expanded image, or 600
active seconds per version. Extraction/evaluation extra. Same random seed for
shuffling; sequences differ because training sets differ. Checkpoints at common
560/2800/5600/11200/16800 steps and timeout. At timeout compare common checkpoints.
Select by validation pitch/validity/exactness, earliest tie. Selected/final
training (all examples) and same-placement image swaps retained. No test scoring.
Training-set accuracy differs in difficulty; shared validation is primary comparison.
No automatic extension or curriculum advancement. Single seed only.

## Executed result

Immutable export `outputs/placements_20261108_01`; run
`outputs/placement_mps_20261108_01`. Both completed all 16800 updates, no time cap.
Active seconds control 250.830 / expanded 259.479 (evaluation/extraction extra).
Exact initial state restored before each run, shared cached feature pool and
identical fresh validation. Exposures exactly 300/control image, 75/expanded.

| Metric | Control | Expanded |
| --- | --- | --- |
| Selected update | 5600 | 16800 |
| Selected training exact | 40/56 | 224/224 |
| Selected validation/donor exact | 25/56 (44.64%) | 48/56 (85.71%) |
| Final training exact | 56/56 | 224/224 |
| Final validation/donor exact | 24/56 (42.86%) | 48/56 (85.71%) |

All evaluated scores valid. Pitch/joint correctness equals exactness for this
fixed single-note task. Training gate passes at final for both; appearance and
donor gates fail for both, so no automatic advancement. Expanded selected also
passes training only. Validation counts at 560/2800/5600/11200/16800:
control 4/10/25/24/24, expanded 4/8/31/32/48. Improvement appears at matched steps,
not only through differing selected checkpoints. Eight expanded errors span
seven pitches (B4 two; A5/B5/C4/D5/G4/G5 one each).

This supports placement diversity at fixed updates in this single-seed
interpolation task. It does not establish full notation reading, handwriting,
new source compositions or universal gains. The original 57.14% experiment used
different validation placements; use this within-run control. Training record
order also differs from the historical export, so control is not exact replay.
Next proposed action: bounded second-seed replication before increasing task
complexity; no additional experiment launched.

Verification: dataset load checks all artifact hashes/labels. Setup audit verifies
280 distinct resized model inputs and identical source/image hashes for all
previous images included in expanded training. Full suite 87 tests: 86 passed,
one sandbox MPS skip (16.244s), log `/private/tmp/placement-tests.log`. Actual
MPS cached/full-prefix checks passed both versions. CPU audit recomputed 1344
saved predictions and valid XML exports, summaries, donor totals, selection and
checkpoint hashes, exact exposures. No inference rerun. Implementation hashes
match. Audit saved as `independent_audit.json`; script
`/private/tmp/audit_placement_20261108.py`, log `/private/tmp/placement-audit.log`.

## Authorized seed-19 replication

User approved repeat. Same immutable export, fresh seed 19 for initialization
and image shuffling; both versions share restored initial tensors and validation.
All other settings/bounds/selection unchanged. New run directory
`outputs/placement_seed19_mps_20261108_01`. Compare selected and matched-step
results for both seeds; do not combine correlated placements as independent
compositions. No new data, test scoring, or automatic advancement.

### Seed-19 executed result

Both versions completed 16800 updates, 300/control image and 75/expanded image,
without time cap. Active seconds control 259.928 / expanded 259.049.
Selected control step 5600: training 14/56, validation/donor 13/56 (23.21%),
all valid. Final control: training 33/56 (all valid), validation/donor 10/56 with
55/56 valid. Selected expanded step 11200 (earliest tie) and final step 16800:
training 224/224 exact, validation/donor 48/56 (85.71%), all valid.
Control validation trajectory 4/9/13/10/10; expanded 4/20/46/48/48 at the
five common checkpoints. Overall gates fail; expanded training passes but
appearance/donor remain below threshold. No automatic advancement.

| Seed | Selected control | Selected expanded |
| --- | --- | --- |
| 7 | 25/56 (44.64%) | 48/56 (85.71%) |
| 19 | 13/56 (23.21%) | 48/56 (85.71%) |

Placement benefit replicated at fixed updates. Control optimization varies
substantially. Equal expanded accuracy does not mean identical predictions:
only one of the eight selected validation errors is shared across seeds. Same
validation set reused, not 112 independent examples or repertoire/scan transfer.
Next proposed action: inspect remaining errors by pitch/placement and specify
another bounded generalization diagnostic before adding notation complexity.
No further run launched.

Audit recomputed all 1344 predictions/XML, totals, donor scores, selection and
checkpoint hashes, exposures. All 280 feature hashes and fixed dataset/encoder/
configuration fields match seed 7; initial decoder tensors differ as expected.
Implementation hashes verified; no inference rerun. Audit `independent_audit.json`;
script `/private/tmp/audit_placement_seed19_20261108.py`, log
`/private/tmp/placement-seed19-audit.log`. CLI seed change checked via help,
whitespace and dedicated placement test (1.231s); preceding full suite remains
86 passed/one skip. Actual MPS cached/full-prefix checks passed both versions.
