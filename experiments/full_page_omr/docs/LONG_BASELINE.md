# Longer clean-page development baseline — 2026-10-31

> Historical report: the MusicXML-target implementation described here was
> retired on 2026-11-14. Commands and relative source links below describe the
> code at Git commit `1b57dfe`, not the current executable pipeline. See the
> [historical index](HISTORY.md) for retrieval and the
> [current pipeline](HUMDRUM_PIPELINE.md) for ongoing work. Results below are
> retained as recorded; this cleanup did not rerun these experiments.


After the [six-page diagnostic](DENSE_OVERFIT.md) learned all three instruments
with a frozen encoder, test greater exposure on the original 36 training pages.
This follows the user's authorization to continue diagnostics and explicit GPU
approval before being away for about an hour.

## Declared recipe

Dataset remains `outputs/clean_pages_v1_20261031_01/`. Fresh adaptor/decoder,
original frozen encoder, width 128/two layers/four heads, 1024 RGB inputs,
614-token vocabulary, AdamW lr 0.001, no weight decay, clipping 1, batch size 1,
no augmentation/dropout, seed 7. Same training-page shuffle and validation-loss
checkpoint selection as the [original baseline](CLEAN_BASELINE.md).

Increase the update cap from 1200 to **14400** (400 presentations per page).
Training/validation/checkpoint loop limit: 1800 seconds; final autonomous scoring
is additional. Validation every 200 updates, preserving the original selection
interval. All targets remain complete; greedy decoding from BOS uses a fixed
8192-token cap with no repairs or grammar masks. Shared decoder code now releases
unused MPS allocations every 256 nonterminal greedy steps; it does not change
attention arithmetic or live tensors. Six-page before/after initial token arrays
matched exactly for this allocator change.

The original run's failed test predictions are not used to select parameters.
This is a development run: **test targets are neither loaded nor scored**.
Evaluate both the minimum-validation-loss checkpoint and the final checkpoint
on the same three preselected training pages (indices 0–2, one per instrument)
and all six validation pages. These checkpoints must be reported separately:
training success at one checkpoint cannot be compared with held-out failure at
another to claim a generalization gap. The final-checkpoint diagnostic does not
change selection. Sampled training-page success does not establish all 36 passed.

Run: `outputs/clean_long_mps_20261031_01/`. Process log:
`outputs/studio_setup_20261031/clean_long_training.log`. It was queued to start
only after the fresh six-page run passed exact transcription and donor-image
matching; inspect its config/log/result to distinguish queued/running/completed.

## Executed result

All 14400 updates completed (400 presentations per training page), without
reaching the 1800-second limit. Training/validation/checkpoint loop: 1099.43
seconds. Minimum validation CE selected update 4800. Original encoder remained
frozen; test targets were not loaded or scored.

| Checkpoint | Training sample exact / valid | Validation exact / valid | Validation EOS | Validation token edit error |
| --- | --- | --- | --- | --- |
| Selected, update 4800 | 0/3 / 0/3 | 0/6 / 0/6 | 6/6 | 28.027% |
| Final, update 14400 | 3/3 / 3/3 | 0/6 / 0/6 | 6/6 | 30.267% |

All sampled training outputs reached EOS too. Final training token error was
zero; selected-checkpoint training sample token error was 11.902%. None of the
18 autonomous outputs hit the cap. Invalid outputs are structurally unscorable;
empty valid-subset error sums do not imply zero musical errors. This establishes
a generalization gap for the **final checkpoint's sampled pages**, unlike the
original 1200-update failure. It does not establish autonomous success on all
36 training pages.

Teacher-forced metrics (gold prefixes, not transcription accuracy):

| Checkpoint | All 36 train CE / accuracy | Six validation CE / accuracy |
| --- | --- | --- |
| Selected | 0.0104493 / 99.763% | 0.339914 / 92.355% |
| Final | 0.00000118262 / 100% | 0.663299 / 92.525% |

Peak process RSS: 2,678,128,640 bytes. Final sampled MPS driver allocation:
4,208,820,224 bytes, not GPU peak. Timings exclude initialization/caching and
final autonomous scoring. Selected training/validation decoding took 43.01/88.40
seconds. The ignored run directory includes standalone `learning_curve.png` and
`learning_curve.pdf`, generated from saved logs; curves explicitly distinguish
gold-prefix loss from transcription accuracy.

## Post-run diagnostics

[`clean_page_diagnostics.py`](../diagnostics/clean_page_diagnostics.py) checks the first six
training pages and all six validation pages, with same-instrument image swaps,
and groups next-token errors by their **reference** field. Executed on CPU with
both saved checkpoints; aggregate validation CE agrees with the MPS evaluation
to within 0.000001. CPU/MPS final accuracy differed by one token out of 25259.
Input/checkpoint hashes checked; no test pages, updates or checkpoint selection.

| Gold-prefix diagnostic | Selected | Final |
| --- | --- | --- |
| Train image-swap CE increase, first six pages | +0.070325 | +0.172425 |
| Validation image-swap CE change | -0.002672 | +0.004292 |
| Validation pitch-step token accuracy (247 tokens) | 15.38% | 14.57% |
| Validation duration-value accuracy (564 tokens) | 50.89% | 51.06% |

Most overall token accuracy comes from predictable structure. The model's image
conditioning on this control is stronger in-sample than on unseen compositions.
These are token/field measurements with correct prefixes, not note accuracy or
proof that the encoder discards notation detail. Both encoder adequacy and the
decoder's ability to learn visual reading remain questions.

Saved `first_divergence_audit.json` records the first autonomous mismatch on each
page. Errors include dynamics, pitches and drum instructions. One piano page
first misses canonical `divisions` (predicts 2, reference 1). Inspection of the
unchanged codec confirms it chooses minimal divisions from the whole part:
35/36 training pages use 2, one piano training page uses 1; validation has one
piano page using 1. This is a target-distribution complication, not a sufficient
explanation of the many pitch/duration errors. No codec change was made.

Next executed diagnostic: a controlled pair derived from training horn page 0,
changing only written C5 to D5 at measure 1, note 2. Targets differ at exactly one
token; raster differs at 240 pixels in a 16-by-55 bounding box. The run starts
from the final checkpoint, retains the frozen encoder, and asks whether it can
learn that small image-dependent distinction. This remains memorization, not a
generalization test. See [dense diagnostics](DENSE_OVERFIT.md).

## Reproduce commands

```sh
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh
.venv/bin/python -m experiments.full_page_omr.training.clean_page_experiment \
  --dataset experiments/full_page_omr/outputs/clean_pages_v1_20261031_01 \
  --output experiments/full_page_omr/outputs/clean_long_NEW \
  --encoder-weights model.safetensors \
  --encoder-config experiments/full_page_omr/outputs/studio_setup_20261031/encoder/config.json \
  --device mps --steps 14400 --eval-every 200 --max-train-seconds 1800 \
  --skip-test --evaluate-last
```

Use a new run directory. Existing exports, predictions and checkpoints remain
intact. `--skip-test` and `--evaluate-last` are opt-in; original CLI defaults
retain test scoring after checkpoint selection. Reports record per-page exposure.
