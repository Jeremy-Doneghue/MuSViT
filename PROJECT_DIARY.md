# MuSViT project diary

## Start here

Current objective: build a trustworthy synthetic dataset for fine-tuning OMR on
full-page and multi-page instrumental parts, then establish a small, reproducible
training and evaluation loop. The current generator focuses on single-staff horn
parts. Broader instrumentation is a future extension.

User's end goal (clarified 2026-10-31): transcribe degraded scans of big-band
parts, potentially handwritten, into a digital score that can be re-engraved.
Piano is the main polyphonic case, but not the only one. MusicXML is the current
generator's canonical source and a possible interchange/export format, not a
user-mandated model target or final format. Evaluate bekern and alternatives
against notation fidelity and editable/re-engraveable output rather than assume
either raw MusicXML generation or bekern is required. Handwriting and degraded
real scans are intended evaluation domains; current synthetic engraving and
visually accepted scan effects do not establish performance on them.

The user requested this diary on 2026-10-31 to make new agent sessions easier to
resume. This initial entry reconstructs the state from repository inspection;
it is not a history of when previous features were implemented.

RGB/grayscale changes were discussed and set aside by the user. Do not pursue
them as the next task.

Polyphony is a required output capability (user clarification, 2026-10-31), even
though the current generated examples do not exercise it. The target-format
audit must cover independent voices and simultaneous notes before choosing a
vocabulary. Proposed fixtures should include same-staff voices and multiple
staves. User clarified that piano will be the most common polyphonic material,
but support must extend beyond piano; exact pilot coverage remains open.

Repository scope: difficulty estimation and embedding-distance analysis were
removed on 2026-10-31 with user approval. Keep full-page OMR, staff-level OMR,
symbol detection, synthetic generation, scan degradation and Bar Review.

## Verified current state

| Area | Present | Gap / limitation |
| --- | --- | --- |
| Synthetic composition | Seeded focused, combined, complete, and regression profiles; ordinary passages and feature interactions | A synthetic starting distribution, not validated coverage of real parts |
| Canonical score | MusicXML 4.0, derived MEI, versioned codec and complete single-page pilot export/adapter | Continuation-page context export and multi-page assembly remain absent |
| Rendering and alignment | SVG pages, optional PNG; actual measure-to-page mappings including compressed notation | Page mappings are not yet consumed by training |
| Splits | Separate seed domains and reserved feature combinations; new clean-page baseline audits source/family/event-fingerprint/target/raster separation | Variant pipelines must preserve source families; tiny held-out set is not a representative benchmark |
| Font work | Deterministic coverage sheets and glyph/fallback audits using Verovio's bundled fonts, including Petaluma | Font comparison tools are not a completed dataset augmentation pipeline |
| Scan degradation | Retained light-copy and framed/rotated library-scan Augraphy recipes with visual notebook | Library-scan visually approved; light-copy acceptable; not calibrated or evaluated with OMR; spatial recipe has no exported source coordinate mapping |
| Real transcription | Local Bar Review app exports reviewed crops and MusicXML | No OMR predictions; no assembled full-part export; fidelity needs manual review |
| Training | Tiny pilot and six dense training pages passed on M4/MPS with a frozen encoder; within-instrument image conditioning and re-engraving verified | 36-page baseline failed all 15 autonomous checks; six-page success is memorization, and generalization remains unestablished |
| Target format | User-approved `musvit-score-v1`; fixed 614-token vocabulary, round-trip fixtures and successful pilot learning | Restricted profile; continuation-page context, editor interoperability and exact historical-layout fidelity remain unverified |

Drum acceptance: user clarified that named sound/playback mappings are optional.
Require readable notation and arbitrary text instructions attached to their
passages. Verified standardization is acceptable; otherwise preserve source
noteheads/positions/text. The audit's named-mapping loss is not itself a blocker.

Directory organization (2026-11-04): see the
[full-page workspace guide](experiments/full_page_omr/README.md) for module ownership
and reproduction commands. Current code lives in generation/, representation/,
datasets/, training/ and diagnostics/; reports live in docs/. User subsequently
requested deleting the legacy bekern/Lightning pipeline: its sources, resources,
CLI launcher and source-dependent audit tool are removed. Consult the original
MuSViT repository for that implementation. Existing outputs and weights remain.

Important files:

- [Target notation coverage requirements](experiments/full_page_omr/docs/TARGET_COVERAGE.md)
- [Target-format analysis and recommendation](experiments/full_page_omr/docs/TARGET_FORMAT_ANALYSIS.md)
- [Implemented score codec and fixture guide](experiments/full_page_omr/docs/SCORE_CODEC.md)
- [Executed overfit pilot and reproduction](experiments/full_page_omr/docs/OVERFIT_PILOT.md)
- [Clean held-out baseline, executed failure and next diagnostic](experiments/full_page_omr/docs/CLEAN_BASELINE.md)
- [Dense horn overfit and image-conditioning results](experiments/full_page_omr/docs/DENSE_OVERFIT.md)
- [Longer 36-page development baseline](experiments/full_page_omr/docs/LONG_BASELINE.md)
- [Controlled note edits and combination probes](experiments/full_page_omr/docs/CONTROLLED_EDITS.md)
- [Short-staff transfer experiment setup](experiments/full_page_omr/docs/SHORT_STAFF.md)
- [Synthetic parts guide](experiments/full_page_omr/docs/SYNTHETIC_PARTS.md)
- [Scenario sampler](experiments/full_page_omr/generation/scenarios.py)
- [Generation and conversion](experiments/full_page_omr/generation/generate_parts.py)
- [MusicXML serialization](experiments/full_page_omr/generation/musicxml_score.py)
- [Font coverage guide](experiments/full_page_omr/docs/FONT_COVERAGE.md)
- [Scan degradation guide](experiments/scan_degradation/README.md)
- [Scan degradation notebook](experiments/scan_degradation/scan_degradation.ipynb)
- [Bar Review guide](apps/bar_review/README.md)
- [Current dataset adapter](experiments/full_page_omr/datasets/clean_page_data.py)
- [Current training loop](experiments/full_page_omr/training/clean_page_experiment.py)
- [Encoder/decoder model](experiments/full_page_omr/smt_foundation/modeling_smt.py)

Local artifacts observed on 2026-10-31 (paths updated after relocation;
ignored outputs are not durable repository
history and should be regenerated from recorded recipes when necessary):

- `experiments/full_page_omr/outputs/synthetic_parts_mixture/manifest.json`: seed 0, train split,
  20 examples: 10 focused, 7 combined, 3 complete. Feature counts in this small
  batch do not cover every supported feature; do not treat it as a benchmark.
- `experiments/full_page_omr/outputs/synthetic_parts_regression/manifest.json`: three fixed regression parts.
- `experiments/full_page_omr/outputs/font_coverage/`: font comparison artifacts.
- `experiments/scan_degradation/outputs/`: exploratory clean/light/worn comparison.
  Original root files and `notebook_validation/` use the retired custom simulator;
  `augraphy_validation/` contains the current Augraphy notebook validation figures.
- `data/reference_parts/`: unchanged local PDF/MusicXML real-part references;
  music font resources come from installed Verovio. The downloaded Petaluma
  bundle and preparation code have been removed.
- Older exports are under `experiments/full_page_omr/outputs/archive/`
  (`synthetic_parts_v1` and `synthetic_parts_musicxml`); their names alone do not
  establish compatibility with the current schema.
- Root `model.safetensors` exists. Its presence does not establish that an OMR
  decoder has been trained on the new synthetic data.

## Existing dataset conventions to preserve

- MusicXML is the editable source of truth. MEI, training tokens, raster images,
  and playback expansions are derived products.
- Written notation and playback order are distinct. Repeats, endings, similes,
  multibar rests, and D.S./coda need explicit treatment; do not silently replace
  written abbreviations with their expanded playback in image transcription labels.
- All pages and engraving/degradation variants of one composition stay in one
  split. Source identity must survive the training export.
- Current reserved combinations: validation = meter changes + two-bar simile;
  test = D.S./coda + improvisation slashes. These are experimental split recipes,
  not established benchmark standards.
- Conversion checks and rendering are useful checks, not proof of visual quality
  or complete notation-editor interoperability.

## Proposed next milestone: first trustworthy training pairs

This sequence began as a recommendation from the 2026-10-31 review. The user
subsequently approved and we implemented the restricted codec/fixture prototype
linked below. The larger training and multi-page architecture choices remain open.

1. Define the target contract before scaling generation. Inventory the notation
   currently generated against what the existing `bekern` representation and
   parser can preserve. Use concrete fixtures for repeats/endings, similes,
   multibar rests, chord symbols, slashes, and page-crossing slurs/navigation.
   Record supported, unsupported, and lossy cases. Choose a versioned derived
   token format based on that evidence; do not assume MusicXML-to-`bekern` is lossless.
2. Export a small inspectable page dataset from saved MusicXML and actual layout
   mappings. Each record needs composition/split identity, page order, image path,
   written measure IDs, target tokens, inherited clef/key/meter/transposition
   context, and source/renderer/tokenizer versions or hashes. Define how a
   continuation page obtains context, and label that dependency explicitly.
   Keep compressed notation intact and cross-page references traceable.
3. Verify target encode/decode semantic round trips on the supported subset and
   inspect image/target pairs. Fail on unsupported notation rather than quietly
   dropping it. Report sequence lengths, feature coverage, split overlaps, and
   image dimensions. Fix a deterministic vocabulary from the format or training
   data; do not learn it from validation/test transcriptions.
4. Add a local dataset adapter and establish a tiny-batch overfit experiment
   (suggested starting size: 8-16 clean pages). Use batch size 1 initially: the
   current collate function takes only `images[0]`, so larger batches need a fix.
   Record actual loss, decoded predictions, EOS/truncation behavior, memory and
   time. Start with a frozen encoder as a diagnostic. Do not launch a large run
   until the image/label/model path can learn these examples.
5. Establish held-out synthetic and manually reviewed real-page baselines. Report
   token error plus musical/structural errors such as pitch/duration, signatures,
   missing bars, compressed-rest counts and navigation. Only then compare added
   fonts, spacing and scan effects using the same held-out set.

For multi-page work, the proposed first baseline is page recognition with explicit
part/page identity followed by part assembly and navigation resolution. Keep
cross-page fixtures from the start. This does not demonstrate joint multi-page
reasoning; evaluate assembly and continuity separately before deciding whether
joint page encoding is needed. Do not simply concatenate pages into a larger
image without checking readability and computation.

The tiny overfit diagnostic was reproduced on the user's 64 GB Mac Studio M4 Max
on 2026-10-31: 1/1 at 200 updates (5.99 seconds), then 8/8 at 1000 updates
(71.42 seconds); image conditioning and pixel-identical re-engraving passed.
See the [Mac Studio setup and results](experiments/full_page_omr/docs/OVERFIT_PILOT.md#mac-studio-rerun--2026-10-31)
for the uv environment and project-local native rendering dependencies, installed
without admin access. These timings are training/evaluation loops, not total
process times or controlled cross-host speed comparisons.

The user-approved [first clean held-out baseline](experiments/full_page_omr/docs/CLEAN_BASELINE.md)
has now executed: 36 train/six validation/six test compositions, four systems per
page, 8–16 bars. The bounded 1200-update run selected update 800 by validation
loss, but all three sampled training pages, six validation pages and six test
pages reached the 8192-token cap without EOS or valid scores. This is a failed
dense-page baseline, not a demonstrated generalization gap. A six-training-page
same-instrument image-swap diagnostic barely changed teacher-forced loss,
suggesting weak image conditioning in this run.

The follow-up [dense diagnostic](experiments/full_page_omr/docs/DENSE_OVERFIT.md)
passed: one 3516-token horn page at 1000 updates, then two dense horn pages at
500 additional updates; both swapped outputs followed donor images exactly.
All final scores stopped correctly and re-engraved pixel-for-pixel. The original
encoder stayed frozen. This establishes image-dependent memorization on two
pages, not note-level reading or an explanation of the failed 36-page baseline.

The six-page warm-start diagnostic passed at 2400 updates (400 new presentations
per page): 6/6 exact/valid/EOS and pixel-identical re-engraving, 6/6 swapped
outputs exactly follow donor images within instrument. Dense piano/drum
memorization is now established alongside horn; unseen-page reading is not.

The fresh-decoder six-page comparison also passed at 2400 updates (400
presentations/page): 6/6 exact/valid/EOS, donor-following swaps and identical
re-engraving. Thus the horn warm-start was unnecessary for this seed and subset;
this is still memorization, not a controlled explanation of the 36-page failure.

The [longer 36-page development run](experiments/full_page_omr/docs/LONG_BASELINE.md)
completed 14400 updates (400 presentations/page). Final checkpoint: sampled
training pages 3/3 exact/valid, validation 0/6 valid; all reached EOS. Selected
update-4800 checkpoint: training sample 0/3 valid, validation 0/6 valid. Final
checkpoint now demonstrates a sampled generalization gap. Field diagnostics show
validation pitch-step accuracy about 15% and duration-value accuracy about 51%
with gold prefixes; image swaps barely affect validation CE.

The controlled one-note pair also passed (2/2 exact, swaps and re-engraving at
500 updates), showing that frozen features preserve that small pitch distinction.
Two untrained edits failed transfer: the model reproduced memorized scores.
See [controlled edits](experiments/full_page_omr/docs/CONTROLLED_EDITS.md).

The four-edit composition diagnostic completed: 5/5 trained controls and swaps
passed; 5/7 untrained combinations were exact. The two failures each missed one
pitch edit; all outputs were valid and stopped correctly. This shows limited
composition of learned visual distinctions within a memorized page, not reading
of unseen compositions.

User reauthorized experiments on 2026-11-01. The 180-composition diversity
comparison completed 14400 updates (80 presentations/page), unchanged validation
and architecture. Both selected and final checkpoints produced 0/6 valid
validation scores; final token error 20.827% versus 30.267% previously, selected
31.407% versus 28.027%. Sampled training also failed (0/3 valid), so this includes
underfitting at the fixed update budget. Test scoring remained disabled. See
[diversity baseline](experiments/full_page_omr/docs/DIVERSITY_BASELINE.md).
User-approved constrained decoding is implemented and evaluated on both diversity
checkpoints. All 12 outputs completed the grammar, but 0/12 passed full semantic
validation; selected/final validation token error worsened to 45.280%/23.368%.
Keep it opt-in and distinguish grammar completion from transcription success.
See [constrained decoding](experiments/full_page_omr/docs/CONSTRAINED_DECODING.md).
Longer 180-page training completed 36000 updates/200 presentations per page in
3450.78 training-loop seconds. Both checkpoints still yield 0/6 valid validation
scores. Selected/final unconstrained token error 23.210%/24.397%; constrained
22.870%/36.933%. Sampled training also fails (0/3 valid). Field/swap diagnostics
still suggest weak image conditioning. See DIVERSITY_BASELINE.md for full results.
User approved setup of the short-staff transfer diagnostic. Implementation and
immutable export are ready: 96 training passages, 16 validation families with
three variants each; 459 tokens per passage. See SHORT_STAFF.md for the bounded
9600-update/1800-second recipe, controls and transfer gates. MPS run short_staff_mps_20261101_01 completed 9600 updates/100 presentations
per passage in 106.456 loop seconds. Selected/final: 0/48 valid validation and
0/3 valid sampled training, all EOS; validation token error 3.440%/3.958%.
Selected gold-prefix step/duration accuracy 22.14%/63.02% drops to 13.80%/36.20%
with image swaps, showing some visual use without reliable recognition. Transfer
gate failed. Next proposed action: inspect optimization/spatial feature access
on the short task before scaling or adapting the encoder. Nothing queued.
User requested recording curriculum learning as a next investigation (2026-11-04):
start with one note on a staff, then increase sequence length and musical/layout
complexity. First proposed action is to specify a one-note pitch-recognition
pilot with held-out examples and progression criteria. This is an exploration
candidate alongside longer training and optimization/visual-feature diagnostics;
no curriculum implementation or training run has been authorized by this note.
Do not tune against the reported test outputs. The adapter still supports only
page 1 of 1. Continuation-page
context, cross-page references and assembly remain separate work; do not cut
full-part tokens at page boundaries. Use the upstream repository for any future bekern baseline comparison; preserve
semantic source scores rather than deriving canonical labels from rendering.

The older general bekern entrypoint has been removed at the user's request
(2026-11-04). Retained training commands and defaults are documented in the
full-page workspace guide and individual experiment reports.

## Session log

### 2026-10-31 - Repository review and continuity setup

- User goal: decide what follows synthetic dataset construction and maintain a
  diary for future agent sessions.
- Inspected generator documentation, current output manifests, dataset loaders,
  training configuration, model code, and existing tests.
- Finding: generating validated MusicXML/MEI is ahead of the training integration.
  The current trainer has no input path for these generated parts and expects
  `bekern` targets. No training result on the new parts was established in this review.
- Added this diary, root `AGENTS.md` continuity instructions, and a README link.
- Proposed the target-contract/export/overfit/evaluation sequence above. No
  tokenizer, dataset adapter, architecture, or training behavior changed.
- Validation: `.venv/bin/python -m unittest discover -s tests -v` ran 38 tests:
  37 passed, one MPS integration test skipped because MPS was unavailable in this
  execution environment. CPU model forward/backward/prediction, generator,
  scenario and font tests passed. Verovio emitted compressed-justification
  warnings on some rendered fixtures; this session did not visually review them.
  `git diff --check` passed and all relative links in the new documentation resolved.
  The Bar Review app's separate tests were not run in this review.
- Workspace already contained substantial modified and untracked work before
  this review. Preserve it; no commit or cleanup was performed.
- Next action: audit target-format coverage against the generated notation.

### 2026-10-31 - Remove unrelated inherited experiments

- User selected: remove difficulty and embedding analysis; keep staff OMR and
  detection. These experiments were independent of full-page OMR in the import audit.
- Removed 24 tracked files under `experiments/difficulty/` and
  `experiments/embeddings_test/`, their CLI loaders/registry entries, and README
  instructions. Existing untracked/generated artifacts were preserved.
- Removed direct dependencies `fvcore`, `pandas`, `pdf2image`, and `scipy` after
  checking retained code references. Some packages may remain transitively needed
  by the retained training/image libraries. Matplotlib stays: font coverage uses
  its packaged DejaVu font. Scikit-learn stays for staff-level OMR.
- Recovery: the removed source is present at pre-cleanup revision `b3d314b`
  (`git show b3d314b:experiments/difficulty/README.md`, for example). No archive
  copy was added to the active source tree, and no Git commit was made here.
- The first lockfile refresh needed access to the uv cache outside writable
  roots. Offline resolution then failed because Verovio metadata was not cached
  for all supported platforms/Python versions; a network refresh was requested.
- Validation: `uv lock` completed (136 packages); removed seven no-longer-needed
  packages, including `fvcore` and `pdf2image`. `pandas` and `scipy` remain in
  the lockfile as transitive requirements. The resolver warned that the existing
  `wandb==0.24.0` version is yanked; no dependency upgrade was attempted here.
  `.venv/bin/python -m unittest discover -s tests -v`: 37 passed, one MPS test
  skipped. Existing Verovio spacing and SWIG deprecation warnings remain.
  `.venv/bin/python -m musvit list` lists only the three retained experiments.
  Registry entrypoint paths, direct requirements against lockfile metadata,
  README/diary links, and `git diff --check` passed. A first ad hoc check used
  system Python, which lacks dotenv; rerunning in `.venv` passed.
- The dataset-to-training milestone above remains the next development task.

### 2026-10-31 - Organize outputs and reference resources

- User requested cleanup of root `outputs/` and relocation or removal of example
  parts and fonts. Kept the reference files and complete Petaluma vendor bundle:
  the PDF is used by scan degradation, and fonts are used by coverage checks.
- Moved mixture, regression and font-coverage output folders under
  `experiments/full_page_omr/outputs/`. Moved older `synthetic_parts_v1` and
  `synthetic_parts_musicxml` under that directory's `archive/`; retained them
  because they contain distinct development artifacts, rather than assuming
  they can be regenerated identically with the current code.
- Moved root `outputs/scan_degradation` to `experiments/scan_degradation/outputs/`.
  Root `outputs/` is now removed. Existing full-page training outputs were retained.
- Moved `resources/fonts` to `experiments/full_page_omr/resources/fonts` and
  `resources/exampleparts` to shared `data/reference_parts`. Root `resources/`
  now contains only the logo. Added short resource/data guides and ignored the
  local reference pair; no generated data, scans or annotations were committed.
- Generator CLI defaults now resolve to their own experiment's output directory,
  independent of working directory. Explicit relative overrides still resolve
  from the caller's working directory. Updated usage examples and the font test
  resource path. Petaluma remains opt-in through `--petaluma-dir`.
- All file bytes and symlink targets were verified immediately after each move
  using SHA-256 inventories. Updated path references in the saved local font
  report and scan manifest; preserved image/score/font bytes. Removed Finder
  `.DS_Store` metadata in the affected trees. An ignored relocation report with
  old/new paths and checksum summaries is at
  `experiments/full_page_omr/outputs/relocation_20261031.json`.
- Validation: 37 tests passed, one MPS test skipped; Petaluma checks executed
  successfully from the new location. Verified reference-file hashes, font
  renderer symlinks, coverage HTML links/report paths, scan source hash,
  documentation links, CLI help for all three affected generators, ignore rules,
  and `git diff --check`. Existing Verovio/SWIG warnings remain. No model training
  or new visual-quality assessment was performed.
- Next action remains the training target-format audit described above.

### 2026-10-31 - Scan degradation notebook

- User requested the first visual experiment notebook. Added
  `experiments/scan_degradation/scan_degradation.ipynb`: PDF/page/seed settings,
  editable custom photocopy profile, whole-page previews, matching passage and
  detail crops, review notes, and an explicit export cell disabled by default.
- Refactored the CLI module to expose shared `preview()` and `export_preview()`
  functions. Preview uses temporary raster files and returns arrays plus a
  manifest; export saves that inspected state and refuses existing directories.
  The CLI also now refuses existing outputs before doing processing. The core
  `photocopy()` algorithm and preset parameters were unchanged.
- Added optional `notebooks` dependency group (JupyterLab and ipykernel), refreshed
  `uv.lock`, and installed that group into `.venv`. Launch from the repo root:
  `uv run --group notebooks jupyter lab experiments/scan_degradation/scan_degradation.ipynb`.
  No Jupyter server was left running by this session.
- Notebook source has no execution outputs or embedded reference scan images.
  An executed validation copy and three rendered figures are under ignored
  `experiments/scan_degradation/outputs/notebook_validation/`.
- Validation: notebook schema validated and every cell executed with nbclient
  from the experiment directory using the local reference PDF, page 1, seed 42,
  300 DPI. Inspected all three rendered figures. Two focused regression tests
  passed (seed reproducibility and exact-image/metadata export with overwrite
  refusal). Also executed the notebook export branch in a temporary directory
  from the repository root: saved arrays/settings/crop metadata matched the
  inspected state, repeated export failed, and light/worn results matched the
  pre-existing CLI PNGs pixel-for-pixel. Confirmed source outputs remain cleared.
  `git diff --check` passed.
- Kernel shutdown emitted a sandbox-related psutil process-enumeration error;
  all notebook cells and figure extraction had completed successfully. Existing
  dependency resolver warning about the previously locked yanked W&B version
  remains; it was not upgraded as part of notebook setup.
- Next action remains the target-format audit. The notebook is available for
  tuning scan profiles and recording observations before training experiments.

### 2026-10-31 - Replace custom photocopy simulation with Augraphy

- User prefers library effects over custom image-processing code and specifically
  suggested BadPhotoCopy and the Augraphy example guide:
  https://augraphy.readthedocs.io/en/latest/doc/source/how_augraphy_works.html.
- Added `augraphy>=8.2,<9`, locked/installed Augraphy 8.2.6 (plus Numba and
  llvmlite) using `uv sync --group notebooks`. No fork or library patch added.
- Removed custom noise, toner-loss/spread, blur, resampling and rotation code.
  `bad_photocopy()` directly calls `augraphy.BadPhotoCopy`; preset dictionaries
  contain its documented keyword arguments. The wrapper isolates/restores Python
  and NumPy random states and Augraphy's process-global Numba JIT flag. Presets
  disable JIT for repeatable sequential previews. This is not a thread-safe
  augmentation adapter for concurrent training workers.
- Updated notebook parameters and explanations, documentation links and tests.
  The custom notebook profile now edits Augraphy options rather than the former
  home-grown model. Preview/export workflow and safe output-directory behavior
  remain available. New manifests use schema version 2 and record backend,
  library version, seeds and copied effect parameters.
- BadPhotoCopy is pixel-only: coordinates/dimensions remain unchanged. Removed
  the old rotation/affine metadata from new runs. Previous custom-simulator
  exports and their metadata were preserved and identified as historical in
  the README. They cannot be reproduced using the new backend settings.
- Validation: both focused tests passed, covering fixed-seed output for both
  presets, different-seed variation, original-image preservation, restoration of
  random/JIT state, exact-image/metadata export and overwrite refusal. Executed
  the complete notebook against the 300-DPI reference page, including a temporary
  export check of all four PNG arrays, backend/version/parameter metadata and
  repeated-export refusal. Examined passage/detail figures; stronger profiles
  visibly introduce substantial patterned noise and need tuning against real
  scans before training. No OMR performance or physical realism claim established.
- Executed notebook and three figures saved under ignored
  `experiments/scan_degradation/outputs/augraphy_validation/`; source notebook is
  valid with outputs cleared. `git diff --check` passed. The same sandbox psutil
  kernel-shutdown warning occurred after all notebook cells completed.
- Next action: use the notebook to tune/document candidate Augraphy profiles;
  the main dataset milestone remains the target-format audit above.

### 2026-10-31 - Model scan framing from a real library example

- User supplied a photographed/scanned La Fiesta piano part showing slight
  rotation, paper inset within a larger scan frame, dark irregular page edges
  (especially on the right), and lighter degradation over readable notation.
  Used it as a visual reference only; did not copy it into repository data,
  alter it, transcribe it or claim to infer exact scanner settings.
- Added `LIBRARY_SCAN` and `library_scan()` using direct Augraphy constructors:
  Geometric dark scanner-edge padding, PageBorder, localized right-side
  BadPhotoCopy, then Geometric white padding and -1-degree rotation. This adds
  frame/background variation separately from the pixel-only copying presets.
  No custom noise or geometric rendering algorithm was added.
- `preview(..., scan_profile=...)` optionally adds this variant; CLI exposes
  `--library-scan`. Notebook includes editable kwargs for each stage and the
  library-scan variant in its whole-page/passage/detail comparisons. The preset
  is an approximation for exploration, not calibrated reproduction of the scan.
- New export manifests use schema version 3, backend `augraphy`, per-variant
  effect order, parameter snapshot, seed, actual dimensions and geometry status.
  Pixel-only variants explicitly retain coordinates; library-scan changes them.
  No source-to-output mapping is claimed. Notebook crop/export inspection boxes
  now belong to each variant's viewport rather than being mislabeled as shared
  source coordinates. Spatial training labels will need separate transformation.
- Geometric in installed Augraphy 8.2.6 samples integer rotation angles; the
  recipe fixes -1 degree and expands the canvas. Padding and PageBorder add
  area instead of intentionally cropping written content. Rotation adds the
  library's default corner fill; inspected as part of the scan-frame effect.
- Validation: three focused tests passed, including repeatable library-scan
  output, expanded dimensions, unchanged inputs/parameter dictionaries and
  restored random/JIT settings. Inspected an initial 700-pixel-wide page preview
  and increased the right-hand dark band to better reflect the reference.
  Executed every notebook cell at 300 DPI, including temporary export and checks
  of all saved arrays, actual dimensions, per-variant geometry metadata, viewport
  boxes and overwrite refusal. Inspected the resulting full-resolution scan.
  The recipe keeps notation readable with the requested broad framing features;
  its solid dark band and border detail remain an approximation of the reference.
  Validation notebook, three figures and `library_scan.png` are under ignored
  `experiments/scan_degradation/outputs/library_scan_validation/`. Source notebook
  outputs remain cleared. CLI help and `git diff --check` passed. The known
  sandbox psutil kernel-shutdown warning followed successful cell execution.
- Next action: visually tune the preset against additional real parts while
  keeping the main target-format/training-integration milestone in view.

### 2026-10-31 - Keep visually accepted scan profiles

- User visual feedback: library-scan looks great, light-copy is okay, worn-copy
  and custom have unrealistic noise. Treat this as the current visual selection,
  not a quantitative OMR evaluation or calibrated physical scanner model.
- Removed worn-copy from active preset definitions and removed the custom
  profile/controls from notebook generation. Default notebook comparisons are
  now clean reference, light-copy and library-scan. CLI retains light-copy, with
  library-scan available through its existing flag. Historical outputs remain.
- Kept library-scan parameters intact and assigned a fixed base-seed + 3 offset
  independent of the number of other profiles. The notebook's reviewed example
  stays at seed 45 for base seed 42, including after removing rejected profiles.
  The CLI now uses the same offset for this named recipe.
- Light-copy remains editable in `COPY_PROFILE`; the rejected custom profile is
  no longer silently regenerated. Updated notebook explanations and README with
  this review decision.
- Validation: all three focused tests passed. Executed the complete notebook
  and a temporary export check: only light-copy/library-scan variants were
  generated/exported, and the library-scan array matched the previously reviewed
  full-resolution PNG pixel-for-pixel. Inspected the updated passage comparison.
  Executed notebook and three figures are under ignored
  `experiments/scan_degradation/outputs/accepted_profiles_validation/`.
  Source outputs remain cleared; `git diff --check` passed. The known sandbox
  psutil warning occurred during kernel shutdown after successful execution.
- Next action: continue from the retained recipes if tuning scans, or resume the
  main training-target audit. Do not reintroduce the rejected noise settings as
  default training augmentation without a new visual review.

### 2026-10-31 - Use bundled Petaluma only

- User requested deletion of the downloaded Petaluma font and use of Verovio's
  bundled copy. Removed `experiments/full_page_omr/resources/` (downloaded music,
  script/text fonts, metadata and vendor files, plus its obsolete README).
- Removed `prepare_otf()` and the local-font ZIP/XML preparation implementation,
  `local_petaluma` function argument, `--petaluma-dir` CLI option, local-resource
  linking/license-copy branch, and downloaded-font preparation test.
- Coverage now defaults to bundled Leipzig and Petaluma. Normal prose text
  still uses packaged DejaVu Serif (or an explicit `--text-font-file` override);
  music and embedded SMuFL text use Verovio resources. FontTools with WOFF support
  remains necessary for outlining Verovio's embedded music text, so no dependency
  removal or lockfile change was needed.
- Archived the previous coverage comparison under
  `experiments/full_page_omr/outputs/archive/font_coverage_downloaded_history/`.
  Preserved standalone rendered sheets, preview images, score sources, reports
  and attribution. Deleted its prepared font ZIP/XML/glyph copies and intermediate
  text-font caches. The archive README identifies historical resource paths as
  removed; no claim is made that those resources can still be loaded.
- Generated a fresh bundled-only `outputs/font_coverage/` using
  `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib MPLCONFIGDIR=/private/tmp/musvit-matplotlib .venv/bin/python -m experiments.full_page_omr.generation.font_coverage --png`.
  Both bundled fonts reported no detected fallback glyphs, unexplained outlines,
  missing references or text fallback characters across the 14 specimens.
- Six focused tests passed, including actual rendering/auditing of bundled
  Petaluma. Replaced the PetalumaScript-dependent fallback test with a temporary
  restricted test font derived from packaged DejaVu. Visually inspected the top
  and bottom of the bundled Petaluma coverage sheet. Source paths/options were
  checked for stale download dependencies; documentation updated.
- Retained new local model/paper ignore patterns added in the working tree and
  normalized their comment/newline formatting. A QA image-crop command initially
  used system Python without Pillow; rerunning with `.venv/bin/python` succeeded.
- Next action remains the main target-format audit; font experiments should use
  the renderer's installed resources rather than restoring the removed bundle.

### 2026-10-31 - Require polyphony in the training target contract

- User confirmed the target-contract and tiny-overfit direction, then clarified
  that polyphony must be supported despite its absence from generated examples.
- Agreed requirement: preserve independent voices and simultaneous notation in
  the output representation. No specific tokenizer or encoding was selected.
- Proposed implementation direction: add round-trip fixtures for chords,
  overlapping voices with different rhythms, rests/gaps, voice-specific ties and
  slurs, and multiple staves. Exact fixture scope and instrumentation remain
  proposals. Include polyphonic examples in a subsequent tiny learning check;
  success on single-voice pages alone cannot establish polyphonic capability.
- Code inspection: the MusicXML comparison helper already notes that polyphony
  needs additional checks when added. No generator, decoder, or training code
  changed; no training or round-trip experiment was executed in this exchange.
- Next action: inventory target coverage and add explicit polyphonic fixtures
  alongside representative existing scores before selecting the token format.

### 2026-10-31 - Prioritize piano polyphony and audit existing support

- User clarified that piano is the primary, but not exclusive, polyphonic use
  case and recalled that polyphony was already a MuSViT goal.
- Code inspection confirms an existing grand-staff training path:
  `SyntheticOMRDataset` uses `antoniorv6/grandstaff-ekern`; the legacy
  `VerovioGenerator` reconstructs a two-spine `**kern` header for rendering.
  Its beat loader selects sequences with two spine terminators. These findings
  establish existing two-spine assumptions, not complete polyphony fidelity.
- `parse_kern_file()` retains explicit space/tab/line separator tokens but its
  cleaner removes some interpretations, including explicit staff markers and
  pedal markers. A fidelity audit is still needed before adopting it for the
  required MusicXML output.
- Proposed next action: audit the existing GrandStaff/bekern path first using
  piano chord, independent-voice and multi-staff round-trip fixtures, then check
  non-piano cases. Reuse supported structure rather than assume a new format is
  necessary; do not bake a two-staff limit into the output contract.
- Documentation only; no dataset download, training, or round-trip experiment
  was performed. `git diff --check` passed.

### 2026-10-31 - Clarify re-engraving as the end goal

- User is not committed to MusicXML and questions whether bekern is suitable.
  Desired outcome: degraded, potentially handwritten big-band part scans become
  digital notation that can be re-engraved. Piano remains the primary polyphonic
  use case, with broader polyphony required.
- Distinguish current generator source format from model tokenization and final
  interchange format. MusicXML remains the existing source-of-truth convention;
  this clarification does not authorize replacing existing source scores.
- Proposed selection criterion: reconstruct editable musical/written structure,
  including big-band abbreviations and expressive markings, with explicit
  unsupported cases. Compare existing bekern support and alternative structured
  targets using round-trip and re-engraving fixtures before selecting a format.
- Limitations: no evidence of handwriting recognition or degraded-scan accuracy
  has been established. Tiny clean-example overfit remains a pipeline diagnostic,
  not validation of the end goal. No model or target-format changes were made.
- Next action: build the target coverage table around representative big-band
  notation and piano polyphony, audit bekern against it, and identify missing
  real/handwritten evaluation fixtures. Documentation whitespace check passed.

### 2026-10-31 - Record collection-specific notation coverage

- User supplied common/not-uncommon features from their big-band collection and
  confirmed availability of real evaluation scans. Recorded the complete list in
  [target coverage requirements](experiments/full_page_omr/docs/TARGET_COVERAGE.md),
  including metadata, free-position instructions, percussion, cue passages,
  alternate repeat layouts, unused pre-lined staves and clipped edges.
- User policy: include readable content; no known crossed-out passages. Clipped
  but inferable content is a required case; acceptable inference/uncertainty
  handling has not yet been agreed. Do not treat reconstructed content as observed.
- The checklist separates user requirements from proposed representation and
  evaluation implications. No tokenizer or multi-decoder architecture selected;
  no existing-format coverage or recognition result claimed.
- No scans, annotations or generated data added. Documentation-only change;
  `git diff --check` passed. No model tests were needed or run.
- Next action: audit bekern and export fidelity against this checklist using
  executable fixtures; inspect real alternative-repeat, percussion, instruction
  placement and clipped-edge examples before specifying those encodings.

### 2026-10-31 - Inspect drum and alternative-layout examples

- User supplied Corner Pocket drum and Charmaine second-tenor screenshots.
  Added visual observations and fixture requirements to the target coverage
  guide. No images copied, labels exported, or transcription asserted.
- Drum example visibly combines repeat-measure symbols/count annotations,
  first/second endings across a system boundary, instructions, mixed noteheads
  and simultaneous rhythmic events. Percussion mapping still needs verification.
- User identifies Charmaine's paired staves as first-/second-time alternatives.
  Recorded that semantic interpretation as user-provided; the screenshot alone
  does not expose clear pass labels. Grouped staves must not automatically become
  simultaneous voices or a piano part. Exact navigation needs annotation.
- Next action: audit representation of alternative passages and percussion
  alongside other checklist items; establish verified measure/pass and drum
  mappings when converting these examples into development fixtures. No training
  or format experiments run. `git diff --check` passed.

### 2026-10-31 - Add cross-page evidence for Charmaine alternatives

- User supplied Charmaine page 2 and explained instrument identity, initial
  single-staff passage and changing staff layout as clues to alternative-pass
  interpretation. Page 2 visibly adds first/second ending labels, repeat
  barlines and a return to single-staff notation. Updated the coverage guide.
- Implication: retain whole-part context and changing staff-group roles through
  page recognition and assembly. Non-piano instrument identity is contextual
  evidence, not a sufficient automatic repeat rule. Exact traversal still needs
  annotation; no full transcription or format compatibility claim made.
- No source images copied or model changes made. `git diff --check` passed.
- Next action remains the format audit, with this two-page example as a
  development case for conditional passages and cross-page assembly.

### 2026-10-31 - Execute target-format analysis

- User requested the analysis. Added the linked target-format report with a
  feature coverage table, candidate comparison, source references, evidence
  limits and a concrete proposed codec/fixture/overfit sequence.
- Added `experiments/full_page_omr/diagnostics/audit_target_format.py`: executes unmodified
  parser function bodies extracted via AST, inspects saved repository vocabularies
  and probes conversions using original synthetic micro-scores. No dataset or
  scan transcription is included. Native converters run in subprocesses; JSON
  output refuses existing files.
- Executed 19 parser probes. Demonstrated lost bar numbers, staff/pedal/cue and
  other interpretation rows, collateral clef loss, fixed-header assumptions and
  newline-dependent truncation. Chords, dots and split/join controls survive.
- Restricted Humdrum-token-Humdrum staff/event reconstruction passed for a
  two-staff chord/independent-voice fixture, including staff/layer assignments.
  This does not establish general fidelity. Existing vocab sizes: 181/191/215.
- Verovio 5.0.0-b3f7bc6 direct MusicXML import retained selected piano structures
  and metadata, plus percussion appearance/text. Named percussion-instrument
  mappings were absent from converted MEI. Alternate `musicxml-hum` import
  aborted with a native length_error (isolated return code -6); an earlier
  regression-score attempt also terminated natively. No library patches/upgrades.
- Final diagnostics: `/private/tmp/musvit-target-audit-20261031-03.json`; earlier
  reports `-01`/`-02` remain. Checked final probe values with explicit assertions
  and verified output overwrite refusal. These are temporary diagnostics, not
  dataset exports or a durable benchmark.
- Recommendation, not a selected/implemented target: compact deterministic
  tokens grounded in MusicXML semantics, open text fallback, editable standard
  export and linked source evidence. Keep bekern as a baseline; full Humdrum is
  more capable than the current cleaner, so do not label it inherently unable
  to support polyphony or alternatives. No learning-speed advantage established.
- No training, actual scan transcription, exact Charmaine reconstruction or
  notation-editor acceptance test performed. Current production code unchanged.
- Validation: 28 focused generator/scenario tests passed using
  `.venv/bin/python -m unittest tests.test_generate_parts tests.test_part_scenarios -v`.
  Existing Verovio compressed-justification and SWIG warnings remain. Local
  documentation links, final newlines, whitespace and `git diff --check` passed. An
  initial test invocation used nonexistent `tests.test_scenarios`; the 20
  generator tests passed but that invocation reported an import error. Corrected
  to the actual `tests.test_part_scenarios` module. Initial exploratory reads also
  used nonexistent filenames; subsequent inspection used repository file names.
- Next action: implement the recommended codec and explicit semantic fixtures,
  including polyphony, percussion mapping and conditional passages; verify export
  before adapting the tiny-overfit runner. Do not start model training yet.

### 2026-10-31 - Clarify drum output acceptance

- User clarified that named drum-instrument mappings need not matter if output
  notation is standardized or source text instructions over passages are kept.
- Updated current coverage requirements and analysis to make named sound mappings
  optional. Require readable noteheads/positions, rhythms/voices and arbitrary
  instructions with meaningful attachment/scope. Verify conventions before
  standardizing; preserving source appearance/text is an acceptable initial path.
- The observed conversion loss remains factual, but it is not by itself a format
  rejection criterion. The broader token-format recommendation still rests on
  parser losses, open text, structural fidelity and export checks.
- Documentation only; no code or experiment changes. `git diff --check` passed.
- Next action: proceed with the proposed codec/round-trip fixtures, evaluating
  drums primarily for notation and instruction preservation rather than playback
  instrument identification.

### 2026-10-31 - Implement restricted score codec and round-trip fixtures

- User approved implementing the small codec and fixtures. Added
  `score_codec.py`, `score_semantics.py`, `codec_fixtures.py`, their guide
  `SCORE_CODEC.md`, and `tests/test_score_codec.py` under the existing experiment
  and test directories. Old bekern/training code and model weights unchanged.
- Implemented `musvit-score-v1`: explicit MusicXML 4.0 element/attribute profile,
  encode/decode, canonical optional source IDs with retained mapping, per-part
  exact rational timing normalization, fixed structural/common-value/UTF-8 byte
  vocabulary. 614 tokens; SHA-256
  `319f5494be4d9f9908c94896eddebbd77be66fa3f55059f24db9b6d638d0b5c9`.
  IDs are independent of held-out text and Python hash seed. Unsupported content
  and malformed/truncated/noncanonical predictions fail explicitly.
- Added independent source timing/structure inspection: chord onsets, independent
  voices/staves, cross-staff beams, type/dot/tuplet durations, staff/cursor bounds,
  contiguous ties, paired spans and bounded simple repeat/ending or D.S./coda
  traversal. This is a restricted validator, not full MusicXML schema validation.
- Eight original/generated fixtures cover horn notation and arbitrary Unicode
  text, piano chords/voices/pedal, cross-staff voice, drum appearance and scoped
  instructions without named sounds, normalized conditional passages, and existing
  seed-7 repeat/endings/D.S. regression scores with abbreviations/harmony/slashes.
  Actual Charmaine and Corner Pocket scans were not transcribed or copied.
- Executed semantic and token round trips, independently expected onsets/spans/
  routes, and rendering. Final artifacts:
  `experiments/full_page_omr/outputs/codec_validation_v1_20261031_03/`, generated by
  `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib MPLCONFIGDIR=/private/tmp/musvit-matplotlib .venv/bin/python -m experiments.full_page_omr.representation.codec_fixtures --output experiments/full_page_omr/outputs/codec_validation_v1_20261031_03 --png`.
  All 16 source/decoded page pairs matched pixel-for-pixel at 900 pixels wide.
  Visually inspected decoded previews across all 16 pages. Tiny fixture token
  counts: 610–1090; 24-bar regression scores: 4938–5018. These are not a page-length
  benchmark. Reports retain hashes, vocab, source/decoded XML, semantic summaries,
  tokens/ID maps and SVG/PNG pairs; all generated outputs remain ignored.
- Rendering exposed Verovio 5.0 sensitivity to `sound` attribute order: sorted
  time-only before tocoda was misclassified. XML serialization now emits navigation
  attributes first while token attributes remain sorted; a real conversion
  regression test covers this. Reused existing text outlining/overflow handling
  for accurate previews. A within-ending page break produced an empty page in
  Verovio; final alternative fixtures break between branches, and the horn tests
  cross-page slur/tie continuity. Exact historical and within-ending pagination
  remain unverified. Earlier `-01`/`-02` attempts were preserved, not overwritten.
- Final validation: `MPLCONFIGDIR=/private/tmp/musvit-matplotlib .venv/bin/python -m unittest discover -s tests -v`
  ran 57 tests: 56 passed, one MPS test skipped (unavailable). Seventeen codec
  tests passed, including open text, malformed streams, failure cases, explicit
  cue/offset preservation, optional named instruments and overwrite refusal.
  Documentation links, vocab/report fingerprint, all page comparisons, whitespace
  and `git diff --check` passed. Existing SWIG warnings remain. Earlier full-suite
  execution before final additions also passed; its Matplotlib cache fallback
  warning was avoided in the final run with MPLCONFIGDIR.
- Limitations: complete-score codec only; no page-context assembler or dataset
  adapter, editor import, constrained model decoding, handwriting recognition or
  training. Original underlying notes/rests under abbreviations are retained;
  page export must address that redundancy and context explicitly.
- Exact next action: implement page-target export/context and source composition
  identity checks, then connect the local dataset adapter for a clean tiny overfit
  experiment. Do not treat codec success as demonstrated OMR performance.

### 2026-10-31 - Run one-page and eight-page overfit experiments

- User authorized proceeding from codec checks to a tiny overfit experiment,
  starting with one complete single-page score and expanding to eight if it
  succeeded. Added pilot export/adapter, bounded runner, prediction re-engraving
  helper, six tests and `OVERFIT_PILOT.md`. No real scans or annotations used.
- Added optional encoder injection to the existing SMT model constructor, retaining
  its default loading path. Loaded all 198 local `vit.*` tensors strictly into a
  no-pooling ViT; the MAE reconstruction decoder is not reused as the OMR decoder.
  Source: root `model.safetensors`, SHA-256
  `109bbaf31d9f2184df1b841579e06d25bc58ed6a42a10dd5f4a5d27d01889db2`;
  encoder config from cached base snapshot `02a42371b861a68ba99e409480c67e19ad6ca2d2`.
- Clarified MPS availability in response to user question: arm64/Apple M4 supports
  Metal; PyTorch 2.9.1 has MPS built. Sandboxed is_available() returned false and
  allocation gave a misleading OS-version error. Authorized outside-sandbox
  probe returned true and allocated a tensor; actual training used MPS there.
- Exported eight distinct complete pages to
  `experiments/full_page_omr/outputs/overfit_pages_v1_20261031_01/`: four horn,
  two piano, two drum examples, each one or two bars. Removed invisible arbitrary
  metadata from pilot targets; retained visible instrument names, dynamics,
  rehearsal marks, drum heads/instructions, piano chords/voices/pedal. Image,
  source and target hashes, composition IDs, actual rendered measures, page/split
  identity, codec version/hash and source-ID maps are recorded. No overwrite.
- Used fixed 614-token codec, plain RGB [0,1], 1024-square bilinear resize,
  batch size 1, no augmentation/token corruption/dropout. Decoder width 128,
  feed-forward 256, two layers/four heads; 653,798 trainable parameters and
  88,793,856 frozen encoder parameters. AdamW lr 0.001, no weight decay, clipping
  1, seed 7. Cached raw image encoder features without targets. Correct direct
  next-token shift bypasses the old collator and extra label slicing. Incremental
  greedy cache was checked against existing full-prefix logits in tests and MPS.
- One-page run `outputs/overfit_one_mps_v1_20261031_01/`: 200 updates, 1/1 exact
  including EOS, valid MusicXML and matching semantics; CE 6.44542 -> 0.00840466.
  Training/evaluation loop 8.43 seconds; process peak RSS 1,195,229,184 bytes;
  sampled final MPS driver allocation 3,114,745,856 bytes (not a GPU peak).
- Eight-page run `outputs/overfit_eight_mps_v1_20261031_01/`: warm-started only
  adaptor/decoder from the one-page `last.pt`, fresh optimizer; max 4000 updates,
  evaluate every 200, stopped at 2000 with 8/8 exact tokens, valid MusicXML,
  identical inspected semantics, zero token edit error and correct EOS/no
  truncation. CE first/last sampled 2.88614/0.000628355; final 25-update mean
  0.000325966. Target lengths 264–510 tokens. Intermediate 7/8 plateau confused
  the two similar piano transpositions; both were distinguished by update 2000.
- Eight-page loop 231.89 seconds including matched and swapped decoding checks,
  excluding initialization/cache/initial eval; initial eval 10.62 seconds. Feature
  cache host time 12.48 seconds is not an isolated synchronized GPU benchmark.
  Process peak RSS 1,283,620,864 bytes; final MPS driver allocation 4,217,929,728
  bytes, not a GPU peak. Encoder remained frozen in both runs. Complete configs,
  source/weight hashes, logs, predictions, metrics and partial trainable checkpoints
  are in their run directories; original model weights were not written.
- Image-conditioning control: cyclic feature swap gave 0/8 exact against original
  labels and 8/8 exact against donor-image labels. Outputs followed images.
  Re-engraved the actual saved final predictions: all eight and the single-page
  prediction matched original input PNGs pixel-for-pixel at 1400px width. Visually
  inspected all eight resized inputs and final re-engraved predictions. Review
  artifacts/reports are in each run's `reengraved/` directory.
- Validation: full `unittest discover -s tests -v` with local Cairo/Matplotlib
  environment ran 63 tests: 62 passed, one MPS unit test skipped in sandbox.
  Actual MPS training/backward/cache checks passed outside it. Existing SWIG
  warnings remain. CLI/help, hashes, docs/links and `git diff --check` checked.
- Limitations: these are sparse one-/two-bar compositions, not realistic dense
  pages; no held-out generalization, real/degraded/handwritten recognition,
  continuation-page assembly or notation-editor interoperability was tested.
  Small diagnostic decoder differs from the old default. No large run launched.
- Exact next action: build a source-disjoint clean synthetic evaluation set with
  more realistic single-page density, keep source families/variants together,
  and report recognition/structural errors before adding fonts or scan effects.

### 2026-10-31 - Reproduce overfit diagnostic on Mac Studio

- User requested rerunning the last experiment before increasing scale on the
  new Mac Studio M4 Max (16 CPU/40 GPU cores, 64 GB, macOS 26.6.2).
- Copied `.venv` pointed at the previous user's Python. Preserved it under
  `experiments/full_page_omr/outputs/studio_setup_20261031/previous_machine_venv/`.
  User installed uv; `uv sync --locked --python 3.11.11` created a fresh `.venv`
  with 119 Python packages including PyTorch 2.9.1. No lockfile changes.
- No admin/Homebrew access. Installed native Cairo 1.18.6 and HarfBuzz 15.0.0
  locally using temporary micromamba into `outputs/studio_setup_20261031/native/`
  under the full-page experiment. Python packages remain uv-managed. Saved exact
  native package URLs and an `activate_rendering.sh` helper alongside that native
  directory. No credentials copied into project artifacts or documentation.
- Historical Hugging Face config download initially returned HTTP 401; after
  user login, downloaded the exact recorded revision's config through the hub
  client to `outputs/studio_setup_20261031/encoder/config.json`. Root encoder
  weights matched the original SHA-256. No weight download or replacement needed.
- External probe confirmed MPS allocation. Exported eight new pages to
  `outputs/overfit_pages_studio_20261031_02/`; preserved incomplete `_01` export
  from discovery of missing HarfBuzz. Prior host's pilot exports were absent;
  no cross-host image-byte comparison claimed. Target lengths match the report.
- Executed original bounded recipe: seed 7, 1024, frozen encoder, width-128
  two-layer decoder, batch size 1, lr 0.001; one stage max 1500/every 100,
  eight stage max 4000/every 200, warm-start only adaptor/decoder from one stage.
  New runs `outputs/overfit_one_studio_mps_20261031_01/` and
  `outputs/overfit_eight_studio_mps_20261031_01/` succeeded at 200 and 1000 updates.
  Training/evaluation/control loops took 5.99 and 71.42 seconds, excluding startup,
  caching and initial evaluation. Different numerical trajectory/update count
  means these are not controlled GPU speed measurements.
- All final outputs exact including EOS, zero token error, valid XML and matching
  inspected semantics. Cyclic swap: 0/8 against original, independently verified
  8/8 against donor-image targets. Actual saved prediction XML re-engraved exactly
  against fresh inputs (1/1 and 8/8). Saved checks, reports and checkpoints in
  new ignored runs; original weights and prior outputs preserved.
- Validation: final full suite ran 63 tests, 62 passed/one sandbox MPS skip;
  actual external MPS training/backward/cache checks passed. Before native setup
  completed, initial suite had one import error and four skips; final complete
  rerun supersedes it. Full logs, native spec and configs remain ignored. Updated
  `OVERFIT_PILOT.md` with environment, results and measurement limits. No training
  code changed; this still establishes only sparse in-sample memorization.
- Exact next action: build the source-disjoint clean synthetic baseline with
  realistic single-page density described above; no larger run started here.

### 2026-10-31 - Start source-disjoint clean page baseline

- User approved trying denser held-out pages. Added `clean_page_data.py`,
  `clean_page_experiment.py`, `CLEAN_BASELINE.md` and five focused tests; extended
  the pilot adapter to support explicit train/validation/test splits while retaining
  its default overfit contract. Prior uncommitted diary/report work preserved.
- Exported `experiments/full_page_omr/outputs/clean_pages_v1_20261031_01/`, seed 71:
  36 train/six validation/six test, equally divided among horn/piano/drums. All 48
  complete pages have four systems (16 horn/drum bars or eight piano bars);
  target lengths 2881–6408. Source/family/fingerprint/target/raster collision
  checks, source/target semantic round trips and visible measure checks passed.
  Inspected one training PNG per instrument in the separate nine-page probe.
- This first baseline intentionally restricts notation to 4/4, C major and a
  small shared feature distribution; no reserved scenario feature pairs, repeats,
  key changes or scan effects. It is a step toward realistic pages, not full
  collection coverage. No generated artifacts added to version control.
- Executed 1200 updates, seed 7, fresh width-128/two-layer decoder/adaptor,
  frozen original encoder, 1024 RGB inputs, AdamW lr 0.001, fixed 8192-token
  cap. Training took 94.37 seconds; minimum validation teacher loss selected
  update 800. At this intermediate observation, all three sampled training-page
  greedy outputs reached the cap without EOS and were invalid. This does not
  demonstrate recognition; validation/test autonomous scoring is still running.
- Run: `outputs/clean_baseline_mps_v1_20261031_01/`; shell log:
  `outputs/studio_setup_20261031/clean_training.log` (both under full-page OMR).
  Tests: 68 ran, 67 passed/one sandbox MPS skip. Actual MPS training/backward
  and cached/full-prefix checks executed. Full test log is alongside the shell log.
- Exact resume action if interrupted: inspect this run's `result.json` and
  training log/process before launching anything else; finish recording all held-out
  metrics in `CLEAN_BASELINE.md`. Do not overwrite/retrain this run or tune against
  its test set. A completion entry will record final evaluation and next action.

### 2026-10-31 - Complete first clean held-out baseline

- Finished the run documented in the preceding start entry. All 15 autonomous
  predictions failed: training sample 0/3 exact/valid/EOS, validation 0/6, test
  0/6. Each hit 8192 tokens and degenerated into repeated closing-element tokens.
  Independently checked saved predictions and final summaries. No outputs could
  be structurally scored or re-engraved; empty valid-subset count sums are not
  evidence of zero musical errors.
- Token edit error: training sample 164.80%, validation 170.80%, test 162.21%;
  these can exceed 100% because of inserted runaway tokens and are not note-error
  percentages. Autonomous evaluation took 393.05 seconds, after the 94.37-second
  training loop. No time cap hit, OOM, or CPU fallback. Peak process RSS
  2,540,716,032 bytes; final sampled MPS driver allocation 38,021,398,528 bytes,
  not a measured GPU peak. Original encoder remained frozen and unchanged.
- Selected update-800 teacher CE / next-token accuracy: train 0.924806 / 71.33%,
  validation 0.940419 / 71.25%, test 0.947605 / 71.00%. Correct preceding tokens
  were supplied for these diagnostics; they do not establish transcription quality.
- Added and executed `clean_page_conditioning.py` after checkpoint selection and
  all test scoring, using only the first six training pages. Within-instrument
  image swaps changed teacher CE from 0.917514 to 0.921012 (+0.003498), accuracy
  71.341% to 71.281%. Inference: weak conditioning in this particular control;
  not proof of complete image independence. No training/selection changes followed
  test results. Saved pairs and checkpoint hash in `conditioning_teacher.json`.
- Updated current state and `CLEAN_BASELINE.md` with complete configs, results,
  code/CLI links, limitations and interpretation; linked it from the tiny pilot.
  Full suite passed 67 tests with one sandbox MPS skip; real GPU training,
  cached/full-prefix agreement and conditioning CLI passed. Documentation links
  and whitespace checked. No code/data commit, scan effects or larger run.
- Proposed exact next action: run a one-dense-training-page overfit diagnostic,
  resolve output-length/grammar/optimization/capacity and image-conditioning
  failures there, then revisit held-out recognition using validation for selection.
  The user has approved/executed this first baseline; this next diagnostic remains
  a proposal rather than a claim of progress or an agreed architecture change.

### 2026-10-31 - Dense sequence and image-conditioning diagnostics

- Continued from the failed clean baseline and encoder question. Reused the
  existing training split; no dataset export or validation/test tuning. Preserved
  prior uncommitted work and all previous artifacts.
- Extended `overfit_pilot.py` with explicit training-split indices, a fixed token
  cap and separate teacher metrics. Updated `pilot_review.py` to use evaluated
  record names and manifest rendering settings. Architecture/weights unchanged.
- Executed on MPS with seed 7, original frozen encoder, width-128/two-layer
  decoder, lr 0.001, 1024 inputs and fixed 8192 decoding cap. One-page bound
  3000/every 500; two-page bound 4000/every 500, warm-start adaptor/decoder only.
- `outputs/dense_one_mps_20261031_01/`: training index 0, 3516 tokens, exact valid
  score/EOS at update 1000, 71.62-second loop. At 500 it stopped but was invalid.
- `outputs/dense_two_mps_20261031_01/`: indices 0/3, 3516/3561 tokens, 2/2 exact
  valid scores/EOS at 500 additional updates, 71.32-second loop including swaps.
  Swapped outputs matched donor transcripts 2/2, original labels 0/2; checked
  saved arrays independently. Both encoders remained frozen. See
  [DENSE_OVERFIT.md](experiments/full_page_omr/docs/DENSE_OVERFIT.md) for full evidence,
  timings, limits, reproduction and paths (all outputs under full-page OMR).
- Re-engraved actual final XML: one-page 1/1 and two-page 2/2 pixel-identical.
  Visually inspected the reconstructed first horn page. Full suite 67 passed,
  one sandbox MPS skip; real GPU training/cache checks passed. Rendering, CLI,
  compilation and whitespace checks passed. No commit or encoder adaptation.
- Interpretation: long sequence memorization and image-dependent selection can
  work with this encoder. Dataset size, per-page exposure and warm-start curriculum
  differ from the failed baseline; this does not isolate its cause or establish
  note-level reading/generalization. Explained image swapping at user request.
- Proposed exact next action: bounded six-page training-only overfit, indices
  0–5, two examples per instrument, frozen encoder initially; measure autonomous
  validity/EOS and within-instrument swaps while recording per-page exposure.

### 2026-10-31 - Start authorized six-page diagnostic

- User approved the bounded six-page training-only overfit. Started MPS run
  `experiments/full_page_omr/outputs/dense_six_mps_20261031_01/`, reusing clean
  training indices 0–5, lengths 3516/3652/5880/3561/3706/6311. No new data export.
- Fixed bound 6000 updates/every 1200, at most 1000 new presentations per page;
  warm-start two-page adaptor/decoder with fresh AdamW optimizer, frozen encoder,
  unchanged width 128/two layers, seed 7, lr 0.001, 1024 input, 8192 token cap.
- Added within-instrument donor selection `[3,4,5,0,1,2]`, donor exactness and
  per-page presentation counts to the runner. Freed training logits/loss after
  each step. No architecture, attention, data or optimizer changes.
- Full suite: 69 ran, 68 passed and one sandbox MPS skip. Added a test that swaps
  preserve instrument, change every image, cover each donor and reject singleton
  groups. Log `/private/tmp/musvit-six-tests.log`; whitespace check passed.
- Exact resume action: inspect `result.json` and
  `outputs/studio_setup_20261031/dense_six_training.log` under full-page OMR,
  finish/save independent swap verification and prediction re-engraving, then
  record final results. No success or failure result is claimed in this entry.

### 2026-10-31 - Preserve partial run and retry MPS memory management

- User authorized continued follow-up experiments based on results and ongoing
  diary updates. No additional permission is needed to choose the next diagnostic.
- Six-page `_01` initial evaluation took 295.31 seconds: only the two horn pages
  were exact/valid. Observed substantial system memory compression and swap;
  inference slows as variable-sized K/V tensors leave unused MPS allocations.
  This is a suspected allocator-pressure contribution, not a controlled timing
  attribution. Sent SIGINT to this run only. Contrary to the initial intention
  to stop before training, evaluation finished while diagnosing and at least 200
  updates executed before interruption (last logged update 200, no checkpoint).
  All partial output/log files remain intact; no final-result claim for `_01`.
- Added release of unused MPS cache before each page and every 256 nonterminal
  decoding steps, plus per-page progress logging. Live tensors, attention math,
  model and optimizer are unchanged. Seven focused tests passed; real MPS retry
  will exercise allocator calls. This change is recorded in the run config/hash.
- Started fresh `_02` with exactly the same bound/seed/warm-start/data and log
  `outputs/studio_setup_20261031/dense_six_training_02.log`. Exact next action:
  finish this run, compare initial token arrays against `_01`, then verify final
  donor matching/re-engraving and decide the next experiment from evidence.

### 2026-10-31 - Complete six-page overfit and start fresh-decoder comparison

- `_02` completed at update 2400, 400 new presentations/page: all six horn/piano/
  drum pages exact, valid, semantically identical and correct EOS. At update
  1200 none was exact/valid despite 97.735% teacher next-token accuracy.
- Final teacher CE 0.000249847/100% accuracy. Within-instrument swaps matched
  donor targets 6/6, original targets 0/6; independently checked saved arrays.
  Actual saved XML re-engraved pixel-identically for all six. No repair/grammar
  masks, target-length stopping, encoder fine-tuning or held-out scoring.
- Loop including evaluations/swap: 436.66 seconds; initial evaluation 112.74
  seconds excluded. Peak RSS 1,263,353,856 bytes; final sampled MPS allocation
  3,555,688,448 bytes, not GPU peak. All six initial token arrays exactly matched
  interrupted `_01`. Cache release materially reduced observed memory pressure;
  timing is not a controlled allocator benchmark.
- Reports/checkpoints are under `outputs/dense_six_mps_20261031_02/` (full-page
  OMR), including independent `conditioning_check.json`, cache equivalence and
  `reengraved/report.json`. See DENSE_OVERFIT.md for reproduction and limits.
- Under user's continued-work authorization, started fresh-decoder comparison
  `outputs/dense_six_fresh_mps_20261031_01/`: identical six pages, seed 7, frozen
  encoder, optimizer/architecture, 6000 bound and 1200 interval, no warm-start.
  Log `outputs/studio_setup_20261031/dense_six_fresh_training.log`.
- Exact next action: finish and verify the fresh run; compare convergence and
  donor fidelity before deciding how to revisit the 36-page baseline. A single
  seed comparison cannot establish a general curriculum advantage.

### 2026-10-31 - Queue longer 36-page development run

- User will be away about an hour and requested approval for a longer run now.
  Requested/received GPU execution approval for a queued bounded 36-page run.
  Queue script is ignored at `outputs/studio_setup_20261031/run_long_after_six.py`
  under full-page OMR. It waits at most 30 minutes for the fresh-six result and
  launches only if all six predictions and all six donor matches pass.
- Planned run `outputs/clean_long_mps_20261031_01/`: same 36 training/six
  validation pages, fresh decoder, frozen encoder, seed 7, original lr/model/
  resolution/token cap. Bound 14400 updates (400 presentations/page), 1800-second
  training-loop limit, validation every 200 as in original baseline. No test
  target loading/scoring. New `--skip-test` and `--evaluate-last` flags keep
  validation selection and final-checkpoint learning diagnostics separate.
- Added per-page exposure to the clean runner's report; both selected and last
  checkpoint evaluate the same first three training pages and six validation
  pages. Full suite after changes: 69 ran, 68 passed/one sandbox MPS skip, log
  `/private/tmp/musvit-long-full-tests.log`; CLI/help and whitespace checked.
- Exact next action: finish fresh-six verification; watch queued baseline log
  `outputs/studio_setup_20261031/clean_long_training.log`, then record results
  for each checkpoint separately. Do not infer that the queued run has started
  until its config/log exists. Preserve interrupted/earlier artifacts.

### 2026-10-31 - Fresh six-page success; longer baseline started

- Fresh six-page run completed at update 2400, 400 presentations/page: 6/6 exact,
  valid, semantic-equal, correct EOS, within-instrument donor matches and
  pixel-identical re-engraving. Independently checked saved swapped arrays;
  reports at `outputs/dense_six_fresh_mps_20261031_01/` under full-page OMR.
- At 1200 all six outputs reached cap despite 98.696% teacher accuracy. At 2400
  teacher CE 0.000320018, 100% accuracy. Loop 506.55 seconds including evaluations/
  swaps, excluding initial eval 74.90 seconds. Peak RSS 1,263,779,840 bytes;
  final sampled MPS allocation 3,564,077,056 bytes, not GPU peak. Encoder frozen.
- Both warm-start and fresh runs first passed at the 2400 evaluation checkpoint;
  exact convergence could have occurred earlier between checks. This one-seed
  result shows the curriculum is unnecessary here, not equal convergence speed
  or broad encoder adequacy. Visually inspected warm-run piano/drum re-engraving.
- The approved queue started `outputs/clean_long_mps_20261031_01/`; training
  updates observed in log. Declared recipe and command in LONG_BASELINE.md.
- Exact next action: monitor the 14400-update/1800-second bound, then distinguish
  training and validation behavior at each checkpoint; leave tests untouched.

### 2026-10-31 - Complete longer baseline and analyze field errors

- Long run completed 14400 updates/400 presentations per page in 1099.43 seconds
  of training/validation/checkpoint work; no time cap hit. Selected update 4800.
  Final checkpoint training sample 3/3 exact/valid/EOS; validation 0/6 valid,
  6/6 EOS, 30.267% token edit error. Selected checkpoint training 0/3 valid,
  validation 0/6 valid with 28.027% token error; all stopped. Test untouched.
- Final train gold-prefix accuracy 100% across all 36 does not establish all 36
  autonomous predictions. Selected/final validation CE 0.339914/0.663299;
  accuracy 92.355%/92.525%. Details, timings, memory, saved curves and limitations
  recorded in LONG_BASELINE.md. Original frozen encoder unchanged.
- Added `clean_page_diagnostics.py` and a field-role test. CPU post-run analysis
  verifies inputs/checkpoints and evaluates first six train/all six validation
  pages; CPU validation CE agrees with MPS within 0.000001. Selected/final train
  swap CE increase +0.070325/+0.172425; validation -0.002672/+0.004292. Pitch-step
  accuracy only 15.38%/14.57%; duration-value accuracy 50.89%/51.06% on validation.
  These are gold-prefix field tokens, not autonomous note accuracy.
- First-divergence audit found musical-value/dynamics/instruction errors and
  one early piano canonical-divisions error (2 predicted vs 1). Only one of 36
  training targets uses divisions 1; others use 2. Minimal divisions depend on
  whole-part rhythms. No codec/target change; this does not explain all failures.
- Added `dense_contrast.py`: derives two pages from training horn 0, changes only
  measure 1 note 2 from C5 to D5. Exactly one target-token difference (index 183),
  240 raster pixels in bbox [278,82,294,137]; regenerated base matches parent
  pixels. Export `outputs/dense_contrast_pages_20261031_01/` is new, immutable.
  Extended pilot exporter to accept explicit scores/render settings and recorded
  XML-ID seed; existing default export preserved. Review helper respects seed.
- Started authorized bounded contrast run `outputs/dense_contrast_mps_20261031_01/`,
  warm-start final long-run adaptor/decoder, fresh optimizer, seed 7, frozen
  encoder, unchanged lr 0.001/width 128/two layers/8192 cap, 2000/every 500.
  Log `outputs/studio_setup_20261031/dense_contrast_training.log`.
- Focused tests after diagnostics/export changes: 13 passed, including role
  separation and existing export/gradient/cache tests. Export assertions checked
  one-token difference, source semantics and localized raster change. Exact next
  action: finish contrast run, independently verify changed-token and swap results,
  re-engrave valid predictions, and record what it does/does not isolate.

### 2026-10-31 - One-note contrast passes; unseen edits fail; test combinations

- Controlled pair completed at 500 updates (250 presentations/page): 2/2 exact,
  valid, semantic-equal/EOS and pixel-identical re-engraving. Swapped tokens
  independently matched donors 2/2. Loop 76.26 seconds, frozen encoder unchanged.
  This demonstrates preserved information for this local pitch distinction.
- New immutable transfer export contains trained controls and two untrained edits:
  C5→E5 at the same position and A4→B4 at another position. Exactly one changed
  target token each; 373/349 localized raster pixels. Evaluation-only run
  `outputs/dense_transfer_eval_20261031_01/` reproduced both trained controls,
  but unseen-pitch output exactly matched the memorized D5 score and unseen-
  position output exactly matched base. All valid/EOS; no transfer learning.
- Added evaluation-only `dense_contrast_eval.py` (checkpoint/data/encoder identity
  checks); then generalized known-output reporting to all trained control names.
  Details and reproduction recorded in CONTROLLED_EDITS.md. Full suite before
  the subsequent composition helper: 70 ran, 69 passed/one sandbox MPS skip.
- Started the next authorized probe: `dense_composition.py` exports base plus four
  individual edits (one per system) as five training records and seven untrained
  combinations (six pairs plus all four). Every combined image's difference mask
  exactly equals the union of individual masks; target differences equal active
  edit count, other tokens unchanged. No original validation/test targets used.
- Dataset `outputs/dense_composition_pages_20261031_01/`, training run
  `outputs/dense_composition_mps_20261031_01/`, evaluation-only run queued at
  `outputs/dense_composition_eval_20261031_01/` (all full-page OMR). Train first
  five records only, original frozen encoder, fresh optimizer from final long
  decoder, seed 7/lr 0.001/width 128/two layers/8192 cap, bound 2000/every 1000.
- Limitation declared before scoring: training at most one edit creates a
  correlation that could hinder combination transfer; failure would not prove
  an architectural inability. Exact next action: verify trained controls and
  donor swaps, score the seven untrained combinations, document each separately.

### 2026-10-31 - Complete composition check and stop at user's request

- User clarified the purpose of overfit diagnostics and need for more data.
  Explained that overfit validates basic pipeline/learning capability, not
  architecture optimality or generalization; more varied training is likely
  necessary but not a guaranteed solution. User then explicitly requested ending
  after the current run due to credits and inability to approve more work.
- Finished only the already-running composition experiment and its queued
  evaluation. Training stopped at update 1000/200 presentations per page:
  5/5 exact/valid/EOS, 5/5 donor-following swaps independently verified. Loop
  161.75 seconds; original frozen encoder unchanged.
- Evaluation-only: 5/7 untrained combinations exact, plus all five controls.
  All 12 valid/EOS at 3516 tokens. Pair 2+3 and all-four each missed only edit 3,
  emitting original F instead of E at index 1754 (measure 9 note 2). Other
  tokens identical; independent audit saved in evaluation directory. Successful
  combinations did not exactly match any training control. Eval 135.44 seconds.
- Evidence now includes limited composition of learned local changes, beyond
  whole-score lookup, but only in a memorized page. Sparse training correlations
  remain a confound; no source-disjoint reading capability is established.
  Details/artifacts/reproduction and evidence limits in CONTROLLED_EDITS.md.
- Final regression suite: 70 ran, 69 passed/one sandbox MPS skip; actual GPU
  runs and data/hash/semantic/local-raster/combination-mask/token checks passed.
  CLI/compilation and whitespace checked. No generated data or weights committed;
  original uncommitted work preserved. No extra composition re-engraving claimed.
- Stopped with all runs complete and no queued follow-up. No 180-page or other
  expanded dataset/run was created. Exact next action, only after user returns
  and reauthorizes: review results, then plan controlled data-diversity scaling
  with fixed validation. Do not resume GPU experiments automatically.

### 2026-11-01 - Reauthorize experiments and start diversity comparison

- User explicitly authorized experiments to continue. Reviewed the longer baseline,
  controlled-edit summary and existing exporter/trainer. Workspace initially clean.
- Declared the fixed-update-budget recipe in DIVERSITY_BASELINE.md before training:
  180 compositions versus 36, same architecture/frozen encoder/seed 7, 14400 updates
  or 1800 training-loop seconds, validation every 200, selected and final checkpoint
  evaluation; test scoring disabled. Exposure is 80 versus 400 presentations/page
  if all updates complete, so this does not isolate diversity from repetition.
- Exported new immutable `outputs/clean_pages_180_20261101_01/` under full-page OMR,
  master seed 71, 60 examples per instrument, target lengths 2997–6632. All pages
  have four systems. Semantic round trips and cross-split collision checks passed.
  Independently checked 576 artifact hashes; all 48 original records match source,
  target, raster, family and musical-fingerprint hashes. Saved expansion_audit.json.
- Started GPU run `outputs/clean_diversity180_mps_20261101_01/` with --skip-test
  --evaluate-last; log `/private/tmp/musvit-diversity180-training-20261101.log`.
  No training success or final metrics claimed yet. No architecture/code change.
- Initial attempt interrupted after last logged update 950 (checkpoint at 800)
  following observed host memory compression and slower updates. Partial artifacts
  preserved. This is a suspected allocator contribution, not controlled attribution.
  Added unused MPS-cache release before encoder/teacher pages and every 25 training
  steps; live tensors/math unchanged. Six focused regression tests passed before
  and after. Started fresh retry `_02`, same data/seed/bounds, log
  `/private/tmp/musvit-diversity180-training-retry-20261101.log`.
- Exact next action: finish bounded run, independently audit saved autonomous
  metrics, compare selected and final checkpoints with LONG_BASELINE.md, then
  record field/image-conditioning diagnostics and limitations as appropriate.

### 2026-11-01 - Complete diversity experiment and assess grammar constraints

- Fresh retry `_02` completed 14400 updates, exactly 80 presentations/page,
  training loop 1240.17 seconds, no time cap or test scoring. Frozen encoder.
  Selected update 11200. All artifacts under full-page OMR outputs.
- Selected: training sample 0/3 exact/valid, validation 0/6 exact/valid,
  validation token error 31.407%. Final: training sample 0/3 exact/valid,
  validation 0/6 exact/valid, validation token error 20.827%. All 18 reached EOS
  without token-cap termination. Independently recomputed every saved prediction
  metric and verified per-page exposure; saved independent_audit.json.
- Selected/final validation gold-prefix CE 0.0779173/0.0818730; improved from
  the 36-page run, but neither produces usable scores. Final sampled training
  token error 17.765%, so this includes training underfitting, not merely a
  demonstrated generalization gap. No invalid-output structural count treated
  as zero musical error; no valid predictions available to re-engrave.
- Executed CPU field/image-swap diagnostics for both checkpoints with hash checks.
  Validation pitch-step accuracy 23.89%/23.48%, duration-value 61.88%/60.64%.
  Validation swap CE change -0.000462/+0.001201; train +0.005124/+0.002749.
  Suggests weak image conditioning on this control; not proof of independence.
- Full regression suite: 70 ran, 69 passed/one sandbox MPS skip. Actual GPU
  training and runtime full-prefix/cache agreement passed. Peak process RSS
  7,513,096,192 bytes; final sampled MPS allocation 3,874,471,936 bytes, not peak.
  Whitespace checks passed. No generated data/weights committed; no commit made.
- User asked about gold prefixes, autonomous decoding and potential grammar
  enforcement. Explained their distinction and proposed same-checkpoint constrained
  decoding comparison. Actual errors include malformed nesting/placement and
  semantic duration/voice-position inconsistencies. Grammar can improve structure
  but cannot guarantee visual pitch/rhythm fidelity. No decoder change yet.
- Exact next proposed action: implement codec/profile-only incremental constraints
  and compare constrained/unconstrained decoding on the same saved checkpoint and
  six validation pages, no retraining or test use, no gold length/content leakage.
  Report syntactic and musical validity separately alongside token/musical errors.
  All experiment/diagnostic processes complete; no further run queued.

### 2026-11-01 - Implement incremental grammar constraints

- User explicitly requested implementation. Preserved earlier diversity work.
  Added constrained_decoding.py: profile-driven parser and opt-in cached greedy
  token masking, required fields, child/attribute legality/order, scalar domains,
  canonical literal/byte distinction and UTF-8/XML character checks. No training,
  target-derived rules, repairs, forced closure or default decoder behavior change.
- Factored REQUIRED/REPEATABLE/UNORDERED into shared codec constants, preserving
  vocabulary and validator behavior. Full semantic checks remain unchanged;
  measure timing, references, voice overlap and visual fidelity are not enforced
  by this initial grammar. Completion and codec validity must remain separate.
- Added constrained_experiment.py, checking input/checkpoint hashes and recomputing
  saved baseline metrics. Evaluation-only on both diversity checkpoints and the
  same six validation pages, fixed 8192 cap. No test loading/checkpoint selection.
  Run outputs/constrained_diversity180_20261101_01/ under full-page OMR; log
  /private/tmp/musvit-constrained-eval-20261101.log. Results pending.
- Six new tests cover all fixtures and dense horn/piano/drum prefixes, illegal
  nesting/order/required fields/attributes, scalar enums and Unicode, controlled
  logit masking and unchanged legal outputs, caps and no-finite-token failure.
  Full suite: 76 tests, 75 passed and one sandbox MPS skip. CLI help passed.
- Exact next action: finish evaluation, independently replay/audit saved outputs,
  document constrained/unconstrained validity and token metrics separately.

### 2026-11-01 - Complete constrained decoding evaluation

- Both checkpoints completed six fixed validation pages on MPS. All 12 outputs
  reached EOS and completed the grammar; zero full-valid or exact scores. Selected
  token error 31.407% → 45.280%; final 20.827% → 23.368%. Interventions 11/12
  respectively. These constraints did not improve recognition in this comparison.
- Independently replayed all 12 token streams, reconstructed and validated XML
  profile trees/local fields, and recomputed prediction metrics. Audit saved under
  outputs/constrained_diversity180_20261101_01/independent_audit.json. Original
  unconstrained baseline metrics were also recomputed. Remaining failures are
  timing/type disagreements, backup before bar start, and measure under/overfill.
  No valid outputs to structurally score or re-engrave; no zero-error claims.
- CONSTRAINED_DECODING.md records reproduction, limits, exact results and checks.
  76 tests ran, 75 passed/one sandbox MPS skip. Real GPU inference, CLI/compilation
  and whitespace checks passed. No training, test access or checkpoint selection.
  Earlier uncommitted work preserved; generated outputs/weights remain ignored.
- All processes complete, nothing queued. Exact next proposed action: a bounded
  longer-training comparison on the existing 180 pages, retaining both decoding
  modes and fixed validation. Timing constraints are a separate possible follow-up;
  grammar completion alone does not establish visual music recognition.

### 2026-11-01 - Start bounded longer training on 180 pages

- User emphasized learning relationships between meter, duration and bar fill with
  more training/data. Continued under existing experiment authorization and GPU
  approval. Explained current 4/4-only data cannot establish meter generalization.
- Started fresh-decoder comparison on the same immutable 180 pages, seed 7,
  unchanged frozen encoder/lr/model/resolution/cap, validation every 200. Bound
  36000 updates or 3600 training-loop seconds, test disabled, both selected and
  final checkpoints evaluated. Full completion gives 200 presentations/page.
- Run outputs/clean_diversity180_long_mps_20261101_01/ under full-page OMR;
  training log outputs/studio_setup_20261031/diversity_long_training_20261101.log.
  Ignored orchestrator run_diversity_long_20261101.py in that setup directory
  launches constrained validation comparisons only after successful training,
  then best/last CPU field and image-swap diagnostics. All outputs are new.
- No training code/data change or new regression testing needed for this recipe;
  previous 76-test suite remains the latest check. No final results claimed.
- Exact next action: monitor training result.json and queued comparisons/diagnostics,
  independently recompute predictions/exposure and record checkpoint-separated
  results. Do not launch another run or broaden data before reviewing this one.

### 2026-11-01 - Verify completed longer 180-page experiment

- User requested completion status. Training and all queued evaluations/diagnostics
  have finished. Completed 36000 updates, 200 presentations/page, 3450.78 seconds,
  no time cap hit. Selected update 27600; encoder frozen, test scoring disabled.
- Selected/final training sample 0/3 valid and validation 0/6 valid/exact. Validation
  unconstrained token error 23.210%/24.397%; constrained 22.870%/36.933%, also 0/6
  valid each. All 30 outputs reached EOS. All 12 constrained outputs grammar-complete.
  No complete valid scores to structurally score/re-engrave. Independently recomputed
  all 30 prediction metrics and checked exposures/run contract; saved run audit.
- Gold-prefix validation pitch-step accuracy 27.13%/25.91%, duration-value
  65.07%/64.54%. Validation image-swap CE change -0.003995/-0.002085. Training
  swaps +0.003169/+0.004962. Suggests weak visual conditioning on this control;
  not proof of complete image independence. Full evidence in DIVERSITY_BASELINE.md.
- Longer training did not consistently improve autonomous recognition versus the
  shorter run; sampled training remains unsuccessful. More-data potential remains
  open, but more compute on this recipe is not yet a demonstrated solution.
- Documentation-only completion review; no new source change/test run or training.
  Preserve all artifacts/uncommitted work. Exact next proposed action: design a
  bounded visual pitch/rhythm recognition diagnostic using unseen controlled
  examples before another longer run. No further experiment queued.

### 2026-11-01 - Review direction after diversity experiments

- User requested interpretation and next-step advice, including whether to
  reconsider the direction. Reviewed DIVERSITY_BASELINE.md, LONG_BASELINE.md,
  CONTROLLED_EDITS.md and the diagnostic/model construction code. This was
  inspection of recorded evidence, not a new independent experiment audit.
- Recommendation (proposed, not an agreed architecture change): pause further
  scaling of the unchanged full-page recipe and establish held-out visual
  pitch/rhythm recognition on short, clean staff passages. Preserve the editable
  score contract, generator, split discipline and existing artifacts.
- Proposed diagnostic: independent composition families, balanced pitch/rhythm
  coverage and varied positions; short autonomous outputs; matched versus
  swapped images, training-prior baselines, full pitch and duration accuracy.
  Report field-specific swap effects because aggregate CE dilutes musical fields.
  Keep source-family variants in one split. Start with the existing frozen encoder;
  only then compare bounded encoder adaptation if transfer remains poor.
- Proposed decision: successful short-passage transfer motivates system-to-page
  curriculum; persistent failure motivates visual-feature/training-path diagnosis.
  A compact event target is a possible controlled follow-up, not approval to
  replace musvit-score-v1. Retain paired staves/voices in later piano coverage.
- External context checked: the original full-page SMT research and official
  implementation describe system pretraining and curriculum learning:
  https://arxiv.org/abs/2405.12105 and https://github.com/antoniorv6/SMT.
  This supports investigating curriculum, not a claim it will solve our task.
- Limitations: 0 valid pages is a strict whole-score outcome; current gold-prefix
  pitch-step metrics are not full note accuracy, and weak aggregate swap effects
  do not prove image independence or identify a faulty encoder. Existing six-page
  validation is development evidence, not a representative real-scan benchmark.
- No source changes, training, test-set scoring or new tests. Exact next proposed
  action: specify/export a bounded source-disjoint short-staff recognition pilot
  with explicit transfer criteria before launching another full-page run.

### 2026-11-01 - Set up short-staff transfer experiment

- User requested setup of the proposed experiment. Added short_staff_data.py,
  short_staff_experiment.py, SHORT_STAFF.md and tests/test_short_staff.py; extended
  the shared adapter's accepted recipe list without changing existing recipes.
  Existing uncommitted work and exports preserved.
- Fixed seed 113 export outputs/short_staff_20261101_01/: 96 independent training
  passages, 16 validation families with base/pitch/rhythm variants (48 records).
  Two bars, one staff, eight natural-pitch notes, fixed treble/C major/4/4;
  eighth/eighth/quarter/half permutations per bar. All targets 459 tokens.
- Source-family variants remain together. Cross-split collision guards and full
  semantic round trips passed; all renders contain both bars on one system.
  Independent setup audit verified 432 source/target/raster hashes. Visually
  inspected one validation raster. Renderer emits a harmless missing-encoded-break
  warning; system count and visible measure checks passed for every export.
- Runner reuses the unchanged frozen-encoder trainer: seed 7, 1024 RGB,
  width 128/two layers, lr .001, fixed cap 1536, 9600 updates or 1800 loop seconds,
  validation every 400; test disabled; selected/final checkpoints kept separate.
  Adds field-specific and autonomous family-disjoint swaps, valid-only full-pitch/
  duration/event metrics, edit-family exactness and training marginal priors.
  Invalid musical scores remain unscorable. Heuristic transfer gates recorded
  before training. Follow-up architecture changes remain proposals.
- Checks: 79 tests, 78 passed/one sandbox MPS skip; includes one-update CPU
  train/evaluate integration with tiny random encoder and forced EOS, not evidence
  of recognition. CLI help passed. Export audit saved setup_audit.json; test log
  /private/tmp/musvit-short-staff-tests.log. No production model training executed.
- Limitations: only 16 independent validation families; fixed eight-note structure,
  fixed rhythm multiset and staff position. No real scans or polyphony claim.
  Prior full-pitch accuracy 8.854%, duration 50%, with reference event slots supplied.
- Exact next action: run the MPS command in SHORT_STAFF.md, then inspect both
  checkpoint reports and controls before deciding on curriculum or adaptation.
  No process queued; no generated datasets/weights added to commits.

### 2026-11-01 - Launch short-staff recognition run

- User explicitly requested running the prepared experiment. Sandbox MPS probe
  returned unavailable; launched with approved GPU access outside the sandbox.
- Run outputs/short_staff_mps_20261101_01/, unchanged exported dataset and
  preregistered defaults (9600 updates/1800 loop seconds, seed 7, encoder frozen).
  Log /private/tmp/musvit-short-staff-training-20261101.log. Wrapper queues both
  checkpoint controls after training. No test scoring or additional experiments.
- Exact next action: monitor completion, independently audit saved predictions,
  report base/edited-family transfer, musical coverage and image conditioning,
  and update SHORT_STAFF.md. No result claimed at launch.

### 2026-11-01 - Complete and audit short-staff experiment

- Bounded run and all controls completed successfully. 9600 updates, exactly
  100 presentations/page, 106.456 training-loop seconds; selected update 3200.
  Frozen encoder, test scoring disabled, no recipe/source changes.
- Selected/final training samples 0/3 valid; validation 0/48 valid/exact, including
  0/16 for each variant. Validation token error 3.440%/3.958%. All 198 matched,
  swapped and training-sample outputs reached EOS without cap termination.
  Invalid scores have no autonomous musical accuracy or re-engraving result.
- Selected gold-prefix step/octave/duration accuracy 22.14/62.24/63.02%; swapped
  13.80/44.53/36.20%. Final matched 17.97/52.86/50.26%. Separate field values,
  not joint-note/full-pitch accuracy. Selected checkpoint shows visual sensitivity.
- Both checkpoints' swaps reproduce the donor image's own prediction 48/48;
  none is an exact donor reference. Recipient output changes 48/48 selected,
  47/48 final. Image-dependent output does not establish correct recognition.
- Recomputed 198 saved prediction metrics, checked exposure/run contract,
  checkpoint/input hashes and family-disjoint donor mapping. Audit stored under
  outputs/short_staff_mps_20261101_01/independent_audit.json. Gold-prefix metrics
  are executed GPU diagnostics, not independently rerun. Full results and limits
  in SHORT_STAFF.md; no new tests since the 79-test setup suite. GPU backward and
  runtime cache/full-prefix agreement passed; process exited zero.
- Transfer gate failed and sampled training also fails; no clean generalization
  gap claim. Exact next proposed action: inspect optimization and spatial visual
  feature access on this short task, then choose a controlled ablation. No further
  run or encoder adaptation launched. Existing artifacts/uncommitted work preserved.

### 2026-11-04 - Review delayed-generalisation hypothesis

- User asked where the latest experiment ended and whether longer training could
  reveal delayed generalisation. Reviewed SHORT_STAFF.md, saved run result and
  training/validation logs, and shared optimizer/checkpoint code. No new training
  or independent prediction audit performed; existing uncommitted work preserved.
- Latest run remains 9600 updates/100 presentations per passage, selected at 3200;
  sampled training 0/3 valid and validation 0/48 valid at both checkpoints.
  Validation CE fluctuates after the selected checkpoint and ends at .08514
  versus .07298 selected. These observations do not rule out later improvement,
  but do not establish the training-mastery stage of classical grokking.
- External primary sources reviewed: https://arxiv.org/abs/2201.02177 and
  https://proceedings.mlr.press/v235/humayun24a.html. Delayed generalisation is
  plausible in principle; those results do not predict it for this OMR recipe.
- Proposed, not agreed: bounded longer short-staff control on unchanged data and
  architecture, with intermediate autonomous training/validation and musical-field
  measurements; separately compare lower learning rate and local visual probes.
  Training mastery followed by delayed held-out improvement would support the
  hypothesis. Persistent training failure motivates optimization/feature diagnosis.
- Code inspection: constant lr .001, AdamW with weight_decay=0; saved checkpoints
  omit optimizer/RNG state, so loading weights would not be exact continuation.
  Exact next proposed action: specify the bounded comparison and checkpoint/metric
  requirements before execution. No experiment launched or queued; no tests run
  for this documentation-only review.

### 2026-11-04 - Record curriculum learning as a next investigation

- User requested adding the discussed curriculum-learning idea to the diary as
  something to explore next. Recorded in the current-state section and here;
  no experiment, dataset export or architecture change executed.
- Proposed progression: one note on a staff with varied pitch and fixed duration;
  then vary duration; then two to four notes, complete bars, multiple bars,
  systems and pages; later introduce polyphony, notation features and scan effects.
  This isolates where recognition first fails on the current eight-note task.
- Preserve realistic staff context and note scale, valid score labels, existing
  target format and source-family split discipline. Vary one difficulty at a time
  initially, retain some easier examples as difficulty rises, and advance using
  held-out musical accuracy rather than training memorization or aggregate token
  accuracy. Exact thresholds and data recipes remain to be specified.
- Curriculum benefits remain a hypothesis for this model. Eventually compare
  against a mixed-complexity training baseline with comparable compute. Relevant
  OMR precedent: https://arxiv.org/abs/2405.12105 uses curriculum learning with
  synthetic data; this does not establish success for our recipe.
- Exact next proposed action: design a bounded one-note pitch-recognition pilot
  and its held-out transfer gates before implementation/execution. Longer-training,
  learning-rate and local-feature investigations remain candidates. No run queued.
- Validation: documentation-only edit; checked placement and whitespace. Existing
  uncommitted work preserved; no source tests required.

### 2026-11-04 - Organize full-page OMR code and reports

- User requested inspecting clutter, ownership and possible dead code, and
  organizing experiments/full_page_omr. Mapped imports, standalone entrypoints,
  source-hash lookups and resource paths before moving files. Preserved existing
  modified/untracked work, datasets, weights and saved runs; no training launched.
- Grouped code into generation/, representation/, datasets/, training/ and
  diagnostics/. Isolated the original bekern/Lightning pipeline and its bundled
  resources/configs/vocabularies under legacy/. Shared smt_foundation/, runtime.py
  and the root CLI entrypoint remain. Moved experiment reports into docs/.
- Added the full-page README with directory ownership, current training dependency
  map, commands/reports, legacy status and migration notes. Updated repository
  callers, tests, report commands and Markdown links to the new locations.
  Historical path references were relocated; historical results remain unchanged.
- Updated source-provenance lookups, default generator output paths and legacy
  resource resolution. Root CLI still uses the experiment root for weights/logs;
  short config paths resolve into legacy/config. Made the launch import lazy so
  inspecting config resolution does not load native rendering dependencies.
- Dead-code finding: removed only the unreferenced data_augmentation/_globals.py
  placeholder containing literal `_globals.py`. Actual shared settings remain in
  legacy/_globals.py. Older overfit_pilot and pilot_data modules are still shared
  by current experiments; legacy code and completed experiments remain retained.
  This is not a proof that every function in retained modules has live callers.
- Verification: with the existing native rendering activation, 79 tests ran,
  78 passed/one sandbox MPS skip. All 17 argparse entrypoint help checks passed;
  short/full config lookup, legacy parser/vocabulary probes and isolated MusicXML
  conversion passed. All internal import destinations and Markdown file links
  resolved. Verified 77 relocated non-Python resources byte-for-byte against Git.
  Whitespace checks passed. Test log: /private/tmp/musvit-organize-tests.log.
- Environment limitations: an initial test attempt without native rendering
  activation failed on Cairo loading; activated suite passes. A full legacy-stack
  import remains blocked by missing MagickWand in this environment; legacy GPU
  training was not run. runpy help checks emitted harmless warnings from reusing
  imported modules within a single check process.
- Compatibility: flat module paths have changed; there are no wrapper modules.
  Ignored historical scripts were preserved and require equivalent import updates
  before rerun. Original recorded artifact/source hashes remain untouched; future
  exports/runs record the reorganized code. No commit or staging performed.
- Exact next action: use the directory guide to choose the next experiment;
  curriculum learning from one-note examples remains proposed, not executed.

### 2026-11-04 - Delete the legacy full-page pipeline

- User explicitly requested deleting the legacy pipeline rather than retaining a
  local baseline, since the original fork source remains available upstream.
  Deleted legacy/ (bekern data/training code, renderer/augmentation, configs,
  vocabularies and bundled textures), the full-page CLI entrypoint, and runtime.py
  which had no remaining production callers. Removed its runtime-only test;
  retained the shared model integration tests and all current experiments.
- Removed the musvit full-page-omr registry entry. Current full-page experiments
  continue through dedicated Python module commands; staff OMR and detection
  remain available through musvit. Removed audit_target_format.py because its
  parser/vocabulary probes depended on deleted sources. Historical target-format
  findings remain documented, explicitly marked historical with an upstream link.
- Dropped legacy-only dependencies names, wand and wonderwords from pyproject.toml
  and uv.lock. An initial offline resolver attempt lacked cached Verovio metadata;
  pruned only the three removed packages/references from the existing lock, then
  `uv lock --check --offline` passed (203 packages), without changing other pins.
- Updated repository/workspace guides, installation requirements, current-state
  diary links and launcher package description. Older diary entries remain intact.
  Upstream reference: https://github.com/OMR-PRAIG-UA-ES/MuSViT.
- Validation: activated rendering environment; 78 tests ran, 77 passed/one sandbox
  MPS skip. Log /private/tmp/musvit-remove-legacy-tests.log. CLI list contains only
  staff-level-omr and object-detection. Internal import targets and Markdown file
  links resolve; no retained code references removed modules. Whitespace checked.
- Existing uncommitted reorganization/current experiment work, model weights,
  saved datasets, outputs and historical run artifacts preserved. No training,
  commit or environment sync performed. Exact next action: choose/design the
  next current experiment; one-note curriculum remains proposed, not executed.

### Entry template

For each future session record: date and objective; concrete changes and paths;
decisions with reasons; commands/configuration/seeds and measured results;
limitations or blockers; and the exact next action. Link long experiment reports
instead of accumulating raw logs here. Update the current state when it changes.
