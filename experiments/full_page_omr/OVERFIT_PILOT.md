# Clean single-page overfit pilot

This is a bounded in-sample image-to-score experiment using the
[score codec](SCORE_CODEC.md). The examples are complete, deliberately tiny
compositions placed on single pages, not crops of a longer score. No continuation
context is needed. They are a diagnostic, not a realistic full-page benchmark.

## Implementation

- [pilot_data.py](pilot_data.py) exports eight distinct clean pages and implements
  the local batch-size-one dataset adapter. Four horn examples, two piano examples
  with chords/independent voices/pedal, and two drum examples with mixed noteheads,
  independent rhythms and changing text instructions are included.
- Export retains source MusicXML, immutable image/target/source hashes,
  composition identity, page order and actual rendered measure IDs, codec/profile
  fingerprints, renderer/code provenance and original-to-canonical ID mapping.
  Invisible arbitrary title/credit/library metadata is removed from these pilot
  labels. They retain visible instrument labels and notation. All records use
  `overfit_train`; evaluating them is explicitly training-set evaluation.
- Image input matches the existing OMR preprocessing: RGB [0,1] with bilinear
  square resize. No grayscale work, augmentations or token corruption are added.
- [overfit_pilot.py](overfit_pilot.py) strictly loads the `vit.*` encoder tensors
  from local MuSViT/MAE weights, with a ViT configuration recorded in the run.
  It injects that encoder into the existing SMT model; its normal construction
  path is preserved. MAE reconstruction-decoder weights are not OMR decoder weights.
- Frozen encoder features are computed once per actual image in eval mode. They
  contain no target tokens, source IDs or example-index embeddings. The adaptor
  and existing autoregressive decoder are trained with next-token cross entropy:
  inputs are `tokens[:-1]`, labels are `tokens[1:]`, including EOS. The old collator
  and extra label slicing are bypassed. No validation/test transcriptions build
  the fixed 614-token vocabulary.
- Diagnostic decoder: width 128, feed-forward width 256, two layers, four heads,
  dropout disabled. There are 653,798 trainable parameters (adaptor + decoder)
  and 88,793,856 frozen encoder parameters. This is smaller than the old default
  eight-layer, width-256 decoder; no architecture-size comparison is claimed.
- Optimizer: AdamW, learning rate 0.001, weight decay 0, gradient norm clipping 1,
  batch size 1, seed 7, shuffled complete passes through the selected examples.
  Encoder remains frozen throughout; no teacher-forcing input corruption.
- Unconstrained greedy decoding starts from BOS alone, never the gold profile,
  metadata or a partial transcription. Incremental attention caches are checked
  against the existing full-prefix implementation (unit tests and runtime checks).
  Cached arithmetic preserves this decoder's unscaled attention; no attention
  architecture or training-attention behavior is changed.
- Evaluation saves exact token match, edit-distance token error, EOS/truncation,
  codec validity and independently inspected score semantics, plus the raw tokens
  and any valid predicted MusicXML. Stop early only on exact predictions for every
  selected example, otherwise stop at the configured update bound.
- At the end of a multi-example run, cyclically swap image features while keeping
  scoring targets fixed. This is a conditioning control, not held-out evaluation.
  [pilot_review.py](pilot_review.py) re-engraves the actual final prediction XML
  and compares raster output with the original page.

## Reproduce

Each export/run requires a **new** output directory. Generated examples, features,
weights, logs and annotations remain ignored. The root encoder weights are read
only; run checkpoints contain the trainable adaptor/decoder parameters.

```sh
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
MPLCONFIGDIR=/private/tmp/musvit-matplotlib \
.venv/bin/python -m experiments.full_page_omr.overfit_pilot export \
  --output experiments/full_page_omr/outputs/overfit_pages_NEW

.venv/bin/python -m experiments.full_page_omr.overfit_pilot train \
  --dataset experiments/full_page_omr/outputs/overfit_pages_NEW \
  --output experiments/full_page_omr/outputs/overfit_one_NEW \
  --encoder-weights model.safetensors \
  --encoder-config /path/to/the/local/encoder/config.json \
  --device mps --resolution 1024 --limit 1 --steps 1500 --eval-every 100

.venv/bin/python -m experiments.full_page_omr.overfit_pilot train \
  --dataset experiments/full_page_omr/outputs/overfit_pages_NEW \
  --output experiments/full_page_omr/outputs/overfit_eight_NEW \
  --encoder-weights model.safetensors \
  --encoder-config /path/to/the/local/encoder/config.json \
  --device mps --resolution 1024 --limit 8 --steps 4000 --eval-every 200 \
  --start-from experiments/full_page_omr/outputs/overfit_one_NEW/last.pt

DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
MPLCONFIGDIR=/private/tmp/musvit-matplotlib \
.venv/bin/python -m experiments.full_page_omr.pilot_review \
  --dataset experiments/full_page_omr/outputs/overfit_pages_NEW \
  --run experiments/full_page_omr/outputs/overfit_eight_NEW
```

This host has an Apple M4 GPU and a PyTorch build with MPS support. Sandboxed
execution reports MPS unavailable (including a misleading OS-version error on
allocation); an authorized outside-sandbox probe and the training run successfully
use MPS. Do not infer absent GPU support from the sandbox's availability check.
CPU can be selected explicitly on other execution surfaces; there is no silent
CPU fallback in the pilot.

Actual local source weights: root `model.safetensors`, SHA-256
`109bbaf31d9f2184df1b841579e06d25bc58ed6a42a10dd5f4a5d27d01889db2`.
Encoder configuration: cached `carlospm12/LSMT-MAE-Base-1024-16` snapshot
`02a42371b861a68ba99e409480c67e19ad6ca2d2/config.json` under the local Hugging Face
hub cache. All 198 encoder tensor keys load strictly; no download or partial
weight-load fallback is used. Full configuration, file hashes and source-code
hashes are recorded in each run's `config.json`.

## Executed first stage — 2026-10-31

Dataset: `outputs/overfit_pages_v1_20261031_01/`.
One-page run: `outputs/overfit_one_mps_v1_20261031_01/`.

The initial untrained OMR decoder produced no valid/exact score for the first
horn page. At update 200 it produced all 264 tokens exactly, including EOS;
MusicXML decoding and score semantics matched. Loss fell from 6.44542 to
0.00840466. The training/evaluation loop took 8.43 seconds, excluding model
initialization, feature preparation and initial evaluation. Initial greedy
evaluation took 2.68 seconds; final greedy evaluation took 1.20 seconds.

Process peak RSS was 1,195,229,184 bytes. MPS driver allocations sampled at the end
were 3,114,745,856 bytes, **not** a measured GPU peak. Feature-caching times are
host timestamps without an explicit Metal synchronization and should not be
interpreted as isolated GPU encoder benchmarks. Loss `.item()` and greedy token
reads synchronize the training/evaluation loops. The encoder remained frozen.

## Executed eight-page stage — 2026-10-31

Run: `outputs/overfit_eight_mps_v1_20261031_01/`, warm-starting only the adaptor and
OMR decoder from the one-page run's `last.pt`. The frozen encoder and its weights
are the same. The optimizer was newly initialized. No data, vocabulary or source
labels changed between stages.

| Check | Result |
| --- | --- |
| Initial exact predictions after warm start | 1/8 |
| Update 800 | 5/8 exact |
| Updates 1000–1800 | 7/8 exact; a similar piano example received the other's pitches |
| Update 2000 | **8/8 exact tokens, valid scores and identical inspected semantics** |
| Token edit error at update 2000 | 0 for all eight |
| EOS / truncation | All eight reached EOS at the correct length; none truncated |
| Cyclic image-feature swap, scored against original targets | 0/8 exact; all eight remained valid scores |
| Swapped predictions compared with the donor images' targets | 8/8 exact — outputs followed the supplied image |
| Re-engraved actual final predictions | 8/8 matched the original input PNGs pixel-for-pixel at 1400px width |

The configured maximum was 4000 updates; training stopped early at 2000.
Input resolution was 1024 square, target lengths 264–510 tokens including
BOS/profile/EOS. The first sampled cross entropy was 2.88614, the last 0.000628355;
the final 25-update mean was 0.000325966. These are sampled training losses,
not held-out validation losses.

The training/evaluation/control loop took 231.89 seconds (3m52s), including
matched-image decoding checks every 200 updates and the final swapped-image
control. This excludes model initialization, feature preparation (12.48 seconds
of host timestamps) and initial evaluation (10.62 seconds). Final matched-image
greedy decoding took 14.58 seconds for all eight; the swap took 14.51 seconds.
Peak process RSS was 1,283,620,864 bytes. End-of-run MPS driver allocations were
4,217,929,728 bytes, not a GPU peak measurement.

Saved artifacts include `config.json`, `training.jsonl`, `result.json`, the
trainable `last.pt`, and each `eval_NNNNN/`'s predictions/metrics. Final decoded
scores are in `eval_02000/`; swapped predictions are in `eval_02000_swapped/`.
`reengraved/` contains the actual predicted-score SVG/PNG pairs, comparison report
and a review grid. Visually inspected all eight resized inputs and re-engraved
predictions. The one-page result also re-engraved identically.

Validation: 63 tests ran, 62 passed, one MPS-specific unit test skipped in the
sandbox. Actual MPS training, backward passes, feature caching and incremental/
full-prefix checks executed successfully outside the sandbox. The six new pilot
tests cover correct shifts/backward gradients, frozen encoder, cached/full-prefix
logits, EOS/truncation, data identity/visibility and export refusal. Existing
codec/render/model tests continue to pass.

## Mac Studio rerun — 2026-10-31

User requested the same diagnostic after moving to a Mac Studio: Apple M4 Max,
16 CPU cores, 40 GPU cores, 64 GB unified memory, macOS 26.6.2. No model,
training-code, vocabulary or dependency-lock changes were made for this rerun.

The copied `.venv` referenced the previous machine's Python. Preserved it at
`outputs/studio_setup_20261031/previous_machine_venv/` and created a new `.venv`
with `uv sync --locked --python 3.11.11` (119 Python packages, PyTorch 2.9.1).
Downloaded only `config.json` from the original encoder revision after the user
logged into Hugging Face; root weights already existed and matched the SHA-256
above. The configuration is at
`outputs/studio_setup_20261031/encoder/config.json`, SHA-256
`3acc4b8ba1f4a9990263de1494dd6ebbff78ffb861ecf6c6098618bbd8152097`.

Native Cairo and HarfBuzz are also required by the existing renderer. This account
has no admin access or Homebrew. Installed Cairo 1.18.6 and HarfBuzz 15.0.0 plus
their native dependencies using a temporary micromamba executable into
`outputs/studio_setup_20261031/native/`. Python packages remain managed by uv;
no global native installation was required. The exact native package URLs are
saved in `outputs/studio_setup_20261031/native-explicit.txt`. For this checkout,
activate rendering paths from the repository root before reproducing commands:

```sh
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh
```

This sets `PATH`, `DYLD_FALLBACK_LIBRARY_PATH` and `MPLCONFIGDIR`. The older
`/opt/homebrew/lib` examples above apply to the previous host. MPS still needs
execution outside the agent sandbox; the external allocation probe passed.

Fresh dataset: `outputs/overfit_pages_studio_20261031_02/`. The `..._01/` export
stopped when the missing HarfBuzz CLI was discovered and was preserved. Final
export contains the same eight pilot compositions with target lengths
264, 264, 294, 288, 397, 397, 510, 510. Native rendering dependencies differ from
the previous host; prior dataset artifacts are absent here, so cross-host raster
byte identity was not checked.

Rerun results, using the same seed 7, 1024 resolution, frozen encoder, decoder,
optimizer and evaluation intervals as the original commands:

| Stage | Exact predictions | Updates | Training/evaluation loop |
| --- | --- | --- | --- |
| One example | 1/1 | 200 | 5.99 seconds |
| Eight examples | 8/8 | 1000 | 71.42 seconds |

Runs: `outputs/overfit_one_studio_mps_20261031_01/` and
`outputs/overfit_eight_studio_mps_20261031_01/`. The eight-example stage loaded
only the one-example adaptor/decoder checkpoint with a fresh optimizer. Initial
exact count was 1/8, then 0/8 at updates 200 and 400, 2/8 at 600, 3/8 at 800,
and 8/8 at 1000. Sampled loss went from 6.44542 to 0.00766906 in the one-example
stage and 2.93936 to 0.00216271 in the eight-example stage (final 25-update mean
0.00135307). These are training losses, not generalization measurements.

All final outputs reached correct EOS without truncation, had zero token error,
decoded into valid MusicXML and matched inspected semantics. The cyclic swap
gave 0/8 exact against original targets and 8/8 against donor-image targets
(independently checked in `conditioning_check.json`). Actual prediction XML
re-engraved pixel-for-pixel against this host's fresh inputs: 1/1 and 8/8 at
1400px width, recorded in each run's `reengraved/report.json`.

The loop timings exclude initialization, feature caching and initial evaluation;
the eight-example loop includes its final swap check. Initial evaluation took
2.08/6.68 seconds; host-timed feature caching took 0.72/2.17 seconds. Peak process
RSS was 1,204,535,296/1,287,766,016 bytes. Final sampled MPS driver allocations
were 1,501,937,664/2,598,682,624 bytes, not GPU peaks. Both encoders remained
frozen. Numerical trajectories differed across hosts and convergence occurred at
different update counts, so elapsed times are not a controlled GPU speed test.

Validation after native setup: 63 tests ran in 5.39 seconds, 62 passed and the
sandbox MPS unit test skipped. Actual MPS training/backward and incremental-cache
checks passed in both external runs. Log:
`outputs/studio_setup_20261031/tests_with_native.log`. Before HarfBuzz was added,
the initial test discovery failed importing the pilot tests and skipped three
font tests; the complete rerun above supersedes that attempt. No dense-page or
held-out experiment was started.

## Limits

The follow-up [dense-page diagnostic](DENSE_OVERFIT.md) applies this runner to
selected training pages from the clean baseline, with a fixed decoding cap.

The subsequent [clean held-out baseline](CLEAN_BASELINE.md) increased to 8–16 bars
and four systems per page. Its first bounded run failed autonomous transcription
even on sampled training pages; the tiny successes above do not transfer to that
setting automatically.

Success on these pages establishes an in-sample pipeline diagnostic only. It
does not establish handwritten/degraded-scan recognition, unseen notation/text,
realistic dense-page accuracy, model-size adequacy, or generalization. The two
similar piano examples are deliberately useful checks of image conditioning.
This small set is not a held-out baseline or a representative feature distribution.

Multi-page source/context export remains separate work; the complete-score codec
still rejects open fragments. Page 1 of 1 is the only adapter contract here.
Optional decoder checkpoints refer to an external frozen encoder file/hash and
are not standalone full-model releases. Final greedy XML is reviewable, but no
notation-editor interoperability test is implied.
