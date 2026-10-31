# Controlled dense-page edits — 2026-10-31

The [longer baseline](LONG_BASELINE.md) memorized sampled training pages but
failed all validation pages. Its gold-prefix image-swap sensitivity was weak on
validation, and pitch/duration-value accuracy was much lower than aggregate token
accuracy. These follow-ups ask what fine visual distinctions the frozen encoder
and decoder can learn and whether that learning transfers within one composition.
They are not source-disjoint recognition benchmarks or proof about real scans.

## One-note pair — passed

[`dense_contrast.py`](dense_contrast.py) derives new pages from existing training
`train_000_horn` (16 bars/four systems, 3516 tokens). Original base score and image
remain untouched. Change only written C5 to D5 at measure 1, note 2. Both targets
remain complete, valid and semantically round-trippable. Exactly one target token
changes (index 183); images differ in 240 pixels in bbox `[278,82,294,137]`.
The regenerated base matches the parent PNG pixel-for-pixel at width 1400.

Dataset: `outputs/dense_contrast_pages_20261031_01/`.
Run: `outputs/dense_contrast_mps_20261031_01/`. Start from the long baseline's
final adaptor/decoder checkpoint, fresh optimizer. Original frozen encoder,
1024 RGB input, width 128/two layers/four heads, lr 0.001, seed 7, fixed 8192
decoding cap. Bound 2000 updates, evaluate every 500; no target-length stopping.

Initial exact count 1/2. At update 500 (250 presentations/page), **2/2 exact,
valid, semantic-equal and correct EOS**, with zero token error. Swaps gave 0/2
original targets and **2/2 donor targets**, independently checked from saved
arrays. Actual final XML re-engraved pixel-identically for both images.
Teacher CE 0.00000178360/100% accuracy. Loop including evaluations/swap 76.26
seconds, excluding initialization, initial evaluation and caching. Peak process
RSS 1,212,268,544 bytes; final sampled MPS allocation 1,841,709,056 bytes, not peak.

This demonstrates that frozen encoder features retain enough information for
this particular small pitch distinction. It does not prove that they encode all
required notation adequately or that the decoder learned general pitch reading.

## Untrained note changes — failed transfer

Exported a fresh four-page diagnostic dataset:
`outputs/dense_transfer_pages_20261031_01/`, containing the two trained controls
and two untrained variants. Both variants differ from the base by one target
token and localized image changes:

- Same position, untrained C5-to-E5 change: 373 changed pixels, token index 183.
- Different position, measure 1 note 3 A4-to-B4: 349 changed pixels, token index 225.

[`dense_contrast_eval.py`](dense_contrast_eval.py) performed **no training** and
loaded the pair's update-500 checkpoint. Results:
`outputs/dense_transfer_eval_20261031_01/`.

| Input | Exact | Actual output |
| --- | --- | --- |
| Trained base | Yes | Base |
| Trained C5-to-D5 edit | Yes | Trained edited score |
| Untrained C5-to-E5 edit | No | Exact trained C5-to-D5 score |
| Untrained edit at note 3 | No | Exact base score |

All four outputs were valid and stopped at 3516 tokens; both untrained edits
were missed. Saved output arrays exactly matched the indicated memorized scores.
Total decoding 45.61 seconds. This supports image-dependent memorization rather
than transferable reading on these two probes; it does not show the encoder
discards their distinguishing visual information.

## Combining known edits — completed

[`dense_composition.py`](dense_composition.py) exports 12 variants of the same
base into `outputs/dense_composition_pages_20261031_01/`. First five records are
training examples: unchanged base and one edit in each of four systems. The
remaining seven are never supplied to training: all six two-edit combinations
and the four-edit combination. Changes (measure/note numbering is one-based):
1/2 C5→D5, 5/2 D5→E5, 9/2 F5→E5, 13/2 F5→E5.

Each edit changes exactly one pitch token, without changing target length or
other content. Export checks confirm that each combined raster's changed-pixel
mask is exactly the union of its individual edits' masks. All variants remain
in their parent's diagnostic training family; `diagnostic_role` marks the seven
untrained probes, not a new source-disjoint validation split.

Run `outputs/dense_composition_mps_20261031_01/` selects only indices 0–4,
warm-starts the long baseline's final checkpoint (not the one-note-pair result),
and retains the same frozen encoder and optimizer/architecture settings. Bound
2000 updates, evaluation every 1000; at most 400 presentations per page. Queued
evaluation-only scoring of all 12 pages is saved to
`outputs/dense_composition_eval_20261031_01/` after training. No test data used.

Training stopped early at update 1000 (200 presentations per training page):
**5/5 exact controls and 5/5 exact donor-following swaps**, independently verified
from saved arrays. Loop including evaluations/swap: 161.75 seconds; encoder frozen.
Peak process RSS 1,254,719,488 bytes; final sampled MPS allocation 1,875,263,488
bytes, not GPU peak. No architecture or target-format change.

Evaluation-only results: **5/7 untrained combinations exact** (five of six pairs;
the four-edit combination failed). All 12 evaluated pages were valid, reached
correct EOS at 3516 tokens and passed the score validator; only the ten exact outputs matched reference semantics.
Both failures missed only edit 3: target E was emitted as the original F at
token index 1754 (measure 9, note 2). Every other token matched. Independent
comparison is in `independent_token_audit.json`. Total evaluation: 135.44 seconds.
The pair 2+3 reproduced the memorized edit-2 score; the four-edit output retained
edits 1, 2 and 4. Successful combinations were not exact copies of any training
control. No prediction repair or additional training was used.

This establishes some composition of learned local pitch distinctions within a
memorized page. It supports basic architectural capability beyond selecting a
whole memorized score, while leaving source-disjoint reading unestablished. It
also makes more training variation a reasonable next investigation before
attributing the earlier generalization failure solely to the frozen encoder.

The user requested stopping after this run due to credits and availability.
All training/evaluation processes completed; no further experiments were queued.
Final regression suite: 70 tests ran, 69 passed/one sandbox MPS skip. Actual MPS
runs, hash/data/semantic checks, localized-change and combined-mask assertions,
independent token checks, CLI/compilation and whitespace checks passed. Test log:
`/private/tmp/musvit-composition-final-tests.log`. Composition predictions were
not additionally re-engraved; the one-note pair's pixel comparisons are above.

This tests combining learned visual distinctions. Failure would not establish
an architectural inability: the five training examples also create a correlation
that at most one note is changed. Success would still be restricted to these
four binary edits in a memorized composition.

## Reproduction

Activate the local renderer as described in OVERFIT_PILOT.md. Use new output
directories; exports refuse overwrite. Commands for the first pair:

```sh
.venv/bin/python -m experiments.full_page_omr.dense_contrast \
  --dataset experiments/full_page_omr/outputs/clean_pages_v1_20261031_01 \
  --output experiments/full_page_omr/outputs/contrast_pages_NEW
.venv/bin/python -m experiments.full_page_omr.overfit_pilot train \
  --dataset experiments/full_page_omr/outputs/contrast_pages_NEW \
  --output experiments/full_page_omr/outputs/contrast_run_NEW \
  --encoder-weights model.safetensors \
  --encoder-config experiments/full_page_omr/outputs/studio_setup_20261031/encoder/config.json \
  --device mps --limit 2 --max-tokens 8192 --steps 2000 --eval-every 500 \
  --swap-within-kind --start-from experiments/full_page_omr/outputs/clean_long_mps_20261031_01/last.pt
```

For transfer, export again with `dense_contrast --transfer-probes` to a new
directory and run `dense_contrast_eval --run <contrast run> --dataset <probe
dataset> --output <new evaluation directory> --encoder-config <same config>`.
For composition, export with `dense_composition --dataset <parent clean dataset>
--output <new directory>`, train with `--limit 5 --steps 2000 --eval-every 1000`
using the same long-run warm-start, then evaluate all 12 with `dense_contrast_eval`.
Training and evaluation logs are under `outputs/studio_setup_20261031/` with
`dense_contrast_*`, `dense_transfer_*` and `dense_composition_*` prefixes.
