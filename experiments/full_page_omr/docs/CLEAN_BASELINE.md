# Clean held-out page baseline

> Historical report: the MusicXML-target implementation described here was
> retired on 2026-11-14. Commands and relative source links below describe the
> code at Git commit `1b57dfe`, not the current executable pipeline. See the
> [historical index](HISTORY.md) for retrieval and the
> [current pipeline](HUMDRUM_PIPELINE.md) for ongoing work. Results below are
> retained as recorded; this cleanup did not rerun these experiments.


This experiment moves from memorizing one-/two-bar fixtures to recognizing new
complete compositions with four systems per page. It remains a small, deliberately
restricted synthetic baseline, not evidence about degraded scans or handwriting.

## Data and separation

[`clean_page_data.py`](../datasets/clean_page_data.py) generates `clean-page-v1` with master
seed 71: 36 training, six validation and six test pages. Each split contains equal
numbers of horn, piano and drum pages. Horn and drum pages contain 16 bars; piano
pages contain eight bars across two staves with chords and three independent
voices. Pitch walks, rhythms, rests, dynamics, articulations/slurs and drum
instructions vary by composition. Every page has four explicitly broken systems.

This first distribution uses 4/4 and C major; it does not yet include key/meter
changes, repeats/endings, similes, multibar rests, tuplets, pedal, font variation,
scan effects or continuation pages. It is denser than the tiny pilot, while still
substantially simpler than the user's big-band collection. Shared rhythmic choices
and feature distribution across splits are intentional: this measures recognition
of unseen compositions within a common generator, not unseen generator styles.

Seeds are derived in independent split domains. Each generated composition is a
new source family; no transposed or engraved variants are generated. Cross-split
checks reject shared source/family identity, target-file hashes, raster hashes
and a fingerprint of musical event sequences. That fingerprint ignores text,
layout and global diatonic transposition, but cannot detect all partial quotations
or musical transformations. This baseline does not use the older scenario
sampler's reserved feature-pair split recipes; both reserved pairs are absent.

Source MusicXML remains canonical. The fixed 614-token `musvit-score-v1` codec
is unchanged. Export independently validates source/decoded semantics, checks that
every source measure appears on the one rendered page, and records image/source/
target hashes, seed, source family, renderer options/version and code hashes.
The adapter rechecks artifact hashes and source/target semantics. No target is
truncated; the fixed export/training/decoding cap is 8192 tokens.

Baseline render options are explicit in the manifest: Verovio 5.0, A4 proportions,
scale 55, encoded breaks, vertical justification, no header/footer. Text is outlined
with packaged DejaVu Serif/HarfBuzz. Input PNG width is 1400; the model receives
1024-square RGB [0,1] images with bilinear resize, without augmentation.

## Training and evaluation

[`clean_page_experiment.py`](../training/clean_page_experiment.py) uses the same strictly loaded
local MuSViT encoder and width-128, two-layer, four-head decoder as the tiny pilot.
Encoder frozen; raw image features cached once without targets. Adaptor/decoder
start fresh (seed 7), rather than using the pilot checkpoint. AdamW lr 0.001,
weight decay 0, gradient clipping 1, dropout 0, shuffled batch size 1. One next-token
shift includes EOS. Runtime checks compare incremental and full-prefix logits.

The declared bound is 1200 updates or 900 seconds of training, whichever comes
first. Validation teacher-forced cross entropy is measured every 200 updates;
the lowest validation loss selects `best.pt`. Test targets are loaded/scored only
after that selection. `last.pt` and complete configs/logs are also retained.

Teacher-forced loss/next-token accuracy use correct preceding tokens, and are
explicitly **not transcription accuracy**. Final autonomous greedy decoding starts
from BOS with no supplied transcript and no grammar constraints, output repair or
target-length stopping rule. Score all six validation and six test pages plus the
first three training pages (one per instrument), selected before training.

Reports include token edit error (total token edits / total reference tokens),
exact pages, EOS/truncation and codec/semantic validity. Complete valid predictions
also receive event edit error over measure/onset/duration/voice/staff/pitch/chord,
missing/extra measure counts, signature, instruction and playback checks. Invalid
outputs are explicitly structurally unscorable; they are never silently omitted
from the validity/exact/token-error denominators. Raw predictions and any decoded
XML are retained for review. This restricted semantic validator is not full
MusicXML/editor interoperability validation.

## Reproduce on the Mac Studio

From the repository root, after the [local rendering setup](OVERFIT_PILOT.md#mac-studio-rerun--2026-10-31):

```sh
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh

.venv/bin/python -m experiments.full_page_omr.datasets.clean_page_data \
  --output experiments/full_page_omr/outputs/clean_pages_NEW

.venv/bin/python -m experiments.full_page_omr.training.clean_page_experiment \
  --dataset experiments/full_page_omr/outputs/clean_pages_NEW \
  --output experiments/full_page_omr/outputs/clean_baseline_NEW \
  --encoder-weights model.safetensors \
  --encoder-config experiments/full_page_omr/outputs/studio_setup_20261031/encoder/config.json \
  --device mps --steps 1200 --eval-every 200 --max-train-seconds 900
```

Use new export/run directories. MPS needs execution outside the agent sandbox.
Generated data, weights, raw predictions and logs remain ignored.

## Executed artifacts

Dataset: `outputs/clean_pages_v1_20261031_01/`. All 48 pages exported successfully,
with no cross-split collisions and four systems on every page. Token lengths:
train 2997–6408, validation 2881–6208, test 3285–6019. Training set is 12 pages per
instrument; validation and test each have two per instrument. A separate nine-page
probe at `outputs/clean_pages_probe_20261031_01/` was used for renderer inspection;
its sources are from the same recipe/seed domains and are not additional training
data. Inspected one training PNG per instrument before the full export.

Run: `outputs/clean_baseline_mps_v1_20261031_01/` on M4 Max/64 GB. The full 1200
updates completed without hitting the time bound. Training/validation/checkpoint
loop: 94.37 seconds, excluding initialization, image caching, initial teacher
diagnostics and final evaluation. Minimum validation loss selected update 800.

| Autonomous greedy evaluation | Exact | Valid complete scores | Correct EOS | Token edit error |
| --- | --- | --- | --- | --- |
| First three training pages | 0/3 | 0/3 | 0/3 | 164.80% |
| Validation | 0/6 | 0/6 | 0/6 | 170.80% |
| Test | 0/6 | 0/6 | 0/6 | 162.21% |

All 15 predictions reached the fixed 8192-token cap without EOS, degenerating into
repeated closing-element tokens. Independently checked lengths, validity and the
dominant emitted token across all saved predictions. Edit error can exceed 100%
because runaway outputs add more tokens than the reference contains. This is
not a percentage of wrong notes. Structural musical errors are **unscorable for
all 15**, not zero: no complete valid score exists to compare or re-engrave.
The raw summary's sums over the empty valid subset must not be read as evidence
of zero missing measures. Greedy evaluation took 393.05 seconds in total.

| Teacher-forced diagnostic | Initial CE | Selected-checkpoint CE | Next-token accuracy at selected checkpoint |
| --- | --- | --- | --- |
| Train, all 36 pages | 6.43697 | 0.924806 | 71.33% |
| Validation, all six | 6.43721 | 0.940419 | 71.25% |
| Test, all six | Not measured before selection | 0.947605 | 71.00% |

These gold-prefix numbers do not contradict the autonomous failure: supplying
correct preceding tokens prevents errors from accumulating. Initial random-model
autonomous decoding was not run; it would not establish a useful reading baseline.
Peak process RSS was 2,540,716,032 bytes; final sampled MPS driver allocation was
38,021,398,528 bytes, not a GPU peak. Encoder remained frozen. The experiment
finished on MPS without OOM or a CPU fallback.

Post-run diagnostic [`clean_page_conditioning.py`](../diagnostics/clean_page_conditioning.py)
loaded the already selected checkpoint and compared six training pages with the
correct images versus different pages of the same instrument (two per kind).
Teacher-forced CE changed only from 0.917514 to 0.921012 (+0.003498), and accuracy
from 71.341% to 71.281%. This suggests weak within-instrument image conditioning
in this run; it does not prove total image independence. No validation/test
selection or training changes followed this diagnostic. Saved
`conditioning_teacher.json` includes pairs and checkpoint hash. Reproduce with:

```sh
.venv/bin/python -m experiments.full_page_omr.diagnostics.clean_page_conditioning \
  --run experiments/full_page_omr/outputs/clean_baseline_mps_v1_20261031_01
```

The diagnostic refuses an existing output file. Run it only after the main run
finishes; it needs MPS access on this host. Additional saved logs are under
`outputs/studio_setup_20261031/`: `clean_training.log`, `clean_conditioning.log`,
`clean_page_export.log` and `clean_full_tests.log`.

Validation: 68 tests ran, 67 passed/one sandbox MPS unit-test skip. Five new tests
exercise complete dense scores/polyphony, seed domains and transposition/text
variant detection, all collision guards, valid/wrong/invalid score metrics, and
split-aware hash-checked loading/export refusal. The real MPS run exercised
backward, frozen features and cache agreement. The conditioning CLI also executed
successfully on MPS. Inspected one 1024-square horn input after preprocessing.

## Interpretation and next diagnostic

Follow-up execution: [dense-page overfit diagnostic](DENSE_OVERFIT.md). The
original baseline results and test outputs below remain unchanged.
The six-page checks passed with both warm and fresh decoders; the
[longer 36-page development run](LONG_BASELINE.md) now tests increased exposure
with validation selection and test scoring disabled.

This first baseline did not learn to produce usable multi-system scores. Because
even the sampled training pages failed, the result does not isolate a held-out
generalization gap. Low training loss alone is insufficient, and more data or
scan effects are not justified by this result.

Proposed next action: isolate one of these dense training pages and establish
full-sequence overfitting plus image conditioning, using autonomous EOS, validity
and musical fidelity checks. Diagnose output length/grammar, optimization and
decoder capacity there before returning to held-out recognition. Continue using
validation for development; do not tune against the reported test predictions.
