# Dense-page learning diagnostic — 2026-10-31

Follow-up to the failed [clean baseline](CLEAN_BASELINE.md), using only its
training split. The question is whether long-sequence memorization and image
conditioning can succeed with the existing frozen encoder before changing it.

After the six-page checks, the [longer baseline](LONG_BASELINE.md) established
a sampled generalization gap. [Controlled one-note and composition probes](CONTROLLED_EDITS.md)
then tested fine visual distinctions and transfer within one dense score.

## Six-page extension — passed

User authorized this extension after the one-/two-page results below. Run:
`outputs/dense_six_mps_20261031_02/`; process log:
`outputs/studio_setup_20261031/dense_six_training_02.log`.

Reuse training indices 0–5 from the same immutable clean dataset: two pages per
instrument. Warm-start adaptor/decoder from `dense_two_mps_20261031_01/last.pt`,
fresh optimizer; retain frozen encoder, seed 7, 1024 input, width 128/two layers,
lr 0.001 and fixed 8192-token cap. Bound: 6000 updates, evaluate every 1200,
stop early only when all six predictions are exact. This permits 1000 new
presentations per page; the inherited checkpoint previously saw horn index 0
1250 times and index 3 250 times, and neither piano nor drum page.

The preserved `_01` attempt took 295.31 seconds for initial decoding (2/6
exact/valid, both horn) amid heavy system memory compression/swap. It was
interrupted after at least 200 updates, before the first training checkpoint.
The `_02` retry releases unused MPS cache before pages and every 256 decoding
steps, preserving live tensors and numerical operations. Both attempts start
from the same two-page checkpoint; `_02` does not resume the interrupted weights.

At update 1200 (200 new presentations/page), no score was exact or valid;
five reached EOS and one drum output hit the cap. At update 2400 (400 new
presentations/page), **6/6 were exact, valid and semantically identical**, all
with correct EOS and zero token error. Teacher CE fell from 0.0717311 at 1200
to 0.000249847 at 2400; next-token accuracy rose from 97.735% to 100%.
The initial cache-management equivalence check matched every token in all six
predictions between `_01` and `_02` (`initial_cache_equivalence.json`).

The final within-instrument swap passed **6/6 exact donor transcripts**, and
0/6 original transcripts; independent saved-array checks are in
`conditioning_check.json`. All six actual final XML predictions re-engraved
pixel-for-pixel (`reengraved/report.json`). The encoder remained frozen.
Loop including evaluations/swap: 436.66 seconds; initial evaluation 112.74
seconds excluded. Peak process RSS 1,263,353,856 bytes; final sampled MPS driver
allocation 3,555,688,448 bytes, not a GPU peak. The interrupted attempt and retry
are not a controlled performance benchmark.

The user authorized ongoing follow-ups. Fresh-decoder comparison (completed): `outputs/dense_six_fresh_mps_20261031_01/`, identical recipe and bounds
but omit `--start-from`. At update 1200 all six hit the cap; at 2400 (400 presentations/page), all six
were exact/valid/semantic-equal with correct EOS. Swaps followed donors 6/6 and
actual predictions re-engraved identically 6/6; saved arrays independently checked.
Final teacher CE 0.000320018, accuracy 100%. Loop 506.55 seconds, initial eval
74.90 seconds excluded; peak RSS 1,263,779,840 bytes; final sampled MPS allocation
3,564,077,056 bytes, not a peak. Both fresh and warm runs first passed at the
2400 checkpoint; their precise convergence steps between checks are unknown.
The horn curriculum was unnecessary for this seed/subset. Neither run establishes
unseen-page reading. The approved [longer baseline](LONG_BASELINE.md) now tests
400 presentations/page on the original 36 training pages without test scoring. Log:
`outputs/studio_setup_20261031/dense_six_fresh_training.log`.

Within-instrument donor mapping is `[3, 4, 5, 0, 1, 2]`. Record both exactness
against original labels and exactness against donor labels. Per-page exposure is
logged and stored in the result. No validation/test scoring or encoder adaptation.

```sh
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh
.venv/bin/python -m experiments.full_page_omr.overfit_pilot train \
  --dataset experiments/full_page_omr/outputs/clean_pages_v1_20261031_01 \
  --output experiments/full_page_omr/outputs/dense_six_NEW \
  --encoder-weights model.safetensors \
  --encoder-config experiments/full_page_omr/outputs/studio_setup_20261031/encoder/config.json \
  --device mps --split train --indices 0 1 2 3 4 5 --max-tokens 8192 \
  --steps 6000 --eval-every 1200 --swap-within-kind \
  --start-from experiments/full_page_omr/outputs/dense_two_mps_20261031_01/last.pt
```

## Recipe

Reuse `outputs/clean_pages_v1_20261031_01/` without modifying or exporting data.
Select training index 0 (`train_000_horn`, 3516 tokens), then indices 0 and 3
(`train_003_horn`, 3561 tokens). Both are 16-bar/four-system horn pages from the
same generator, with different music; these are not a controlled single-note
contrast pair. No validation/test transcripts are loaded for training or scoring.

Same local encoder weights, 1024 RGB inputs, frozen feature caching, 614-token
vocabulary, width-128/two-layer/four-head decoder, AdamW lr 0.001, no weight decay,
clipping 1, batch size 1, no dropout/augmentation, seed 7. Unconstrained greedy
decoding begins with BOS alone and uses a fixed 8192-token cap, independent of
either target's length. Correct EOS, exact tokens, validity and semantics are
required for early stopping; no grammar masks or output repairs.

The one-page stage starts fresh, bounded at 3000 updates/evaluation every 500.
The two-page stage warm-starts its adaptor/decoder from the one-page checkpoint
with a fresh optimizer, bounded at 4000 updates/evaluation every 500. Encoder
weights stay frozen in both stages. The two-page swap supplies B's cached image
features while scoring against A, and vice versa. Compare the saved output also
with the donor image's transcript: image use should make it follow the donor.
This can establish image-dependent memorization, not note-level reading or
generalization to unseen pages.

## One-page result

Run: `outputs/dense_one_mps_20261031_01/` on M4 Max/MPS.

- Update 500: reached EOS at 3516 tokens, but invalid; token edit error 3.612%.
  Gold-prefix CE 0.046299, next-token accuracy 98.862%.
- Update 1000: **1/1 exact**, valid score, identical inspected semantics, correct
  EOS, no truncation. Gold-prefix CE 0.000257600, next-token accuracy 100%.
- Actual saved prediction re-engraved pixel-for-pixel against the input at
  1400px width; visually inspected the reconstructed four-system page.
- Training/evaluation loop 71.62 seconds, excluding initialization, image caching
  and initial evaluation (8.43 seconds). Peak process RSS 1,199,325,184 bytes;
  final sampled MPS driver allocation 8,007,335,936 bytes, not a GPU peak.

This rules out an absolute inability of this decoder to memorize this long
sequence and stop. A single example cannot establish image conditioning.

## Two-page result and interpretation

Run: `outputs/dense_two_mps_20261031_01/`. At 500 additional updates, **2/2
exact**, valid and semantically identical, correct EOS and no truncation. Token
error was zero for both. Gold-prefix CE 0.000616884, next-token accuracy 100%.
Both actual predictions re-engraved pixel-for-pixel at 1400px width.

Swapped images gave 0/2 exact against the original labels and **2/2 exact against
the donor-image labels**, independently verified from saved token arrays in
`conditioning_check.json`. Both swapped outputs remained valid. Thus the frozen
encoder's features distinguish these two pages sufficiently for the decoder to
select their full memorized transcripts. This does not establish that individual
notes are being read or that the encoder is adequate for harder material.

Training/evaluation/control loop: 71.32 seconds, including the final swap
(22.83 seconds), excluding initialization, caching and initial evaluation
(22.34 seconds). Peak process RSS 1,218,740,224 bytes; final sampled MPS driver
allocation 12,671,942,656 bytes, not a GPU peak. Encoder remained frozen.

The 36-page baseline received only 33–34 presentations per training page across
1200 updates; the selected update-800 checkpoint received 22–23. This diagnostic
used 1000 presentations of one page, followed by 250 presentations of each of
two pages with a warm start. Training exposure, curriculum and dataset size are
confounded: this is evidence to investigate optimization/exposure before blaming
the encoder, not a controlled explanation of the baseline failure.

This two-page result motivated the now-completed six-page training-only overfit (indices 0–5,
two pages per instrument), reporting presentations per page, autonomous EOS,
validity and within-instrument swaps. Keep the encoder fixed initially. The six-page results above now establish dense piano/drum memorization.
Generalization, degraded scans and handwriting remain unestablished; encoder
fine-tuning has not been performed.

Validation: full suite 68 tests ran, 67 passed and one sandbox MPS test skipped;
actual MPS backward/frozen-encoder and incremental/full-prefix checks passed in
both experiments. Rendering checks executed with the updated review helper.
CLI help, Python compilation and whitespace checks passed. Test log:
`/private/tmp/musvit-dense-tests.log`.

## Reproduce commands

Use fresh run directories; the existing dataset is read-only.

```sh
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh

.venv/bin/python -m experiments.full_page_omr.overfit_pilot train \
  --dataset experiments/full_page_omr/outputs/clean_pages_v1_20261031_01 \
  --output experiments/full_page_omr/outputs/dense_one_NEW \
  --encoder-weights model.safetensors \
  --encoder-config experiments/full_page_omr/outputs/studio_setup_20261031/encoder/config.json \
  --device mps --split train --indices 0 --max-tokens 8192 \
  --steps 3000 --eval-every 500

.venv/bin/python -m experiments.full_page_omr.overfit_pilot train \
  --dataset experiments/full_page_omr/outputs/clean_pages_v1_20261031_01 \
  --output experiments/full_page_omr/outputs/dense_two_NEW \
  --encoder-weights model.safetensors \
  --encoder-config experiments/full_page_omr/outputs/studio_setup_20261031/encoder/config.json \
  --device mps --split train --indices 0 3 --max-tokens 8192 \
  --steps 4000 --eval-every 500 \
  --start-from experiments/full_page_omr/outputs/dense_one_NEW/last.pt
```

`overfit_pilot.py` now accepts explicit training-split indices and a fixed token
cap, records selected names, and saves teacher diagnostics separately from greedy
metrics. `pilot_review.py` selects records by the actual evaluated names and uses
the dataset's rendering options for dense pages. Existing tiny-pilot defaults
remain available. Saved configs contain source/data/weight hashes; checkpoints
contain only adaptor/decoder state and refer to the unchanged external encoder.
