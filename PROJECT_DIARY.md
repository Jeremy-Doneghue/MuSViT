# MuSViT project diary

## Start here

Current objective: build a trustworthy synthetic dataset for fine-tuning OMR on
full-page and multi-page instrumental parts, then establish a small, reproducible
training and evaluation loop. The current generator focuses on single-staff horn
parts. Broader instrumentation is a future extension.

The user requested this diary on 2026-10-31 to make new agent sessions easier to
resume. This initial entry reconstructs the state from repository inspection;
it is not a history of when previous features were implemented.

RGB/grayscale changes were discussed and set aside by the user. Do not pursue
them as the next task.

Repository scope: difficulty estimation and embedding-distance analysis were
removed on 2026-10-31 with user approval. Keep full-page OMR, staff-level OMR,
symbol detection, synthetic generation, scan degradation and Bar Review.

## Verified current state

| Area | Present | Gap / limitation |
| --- | --- | --- |
| Synthetic composition | Seeded focused, combined, complete, and regression profiles; ordinary passages and feature interactions | A synthetic starting distribution, not validated coverage of real parts |
| Canonical score | MusicXML 4.0, with derived MEI and conversion checks | No derived training targets for the new parts |
| Rendering and alignment | SVG pages, optional PNG; actual measure-to-page mappings including compressed notation | Page mappings are not yet consumed by training |
| Splits | Separate seed domains and reserved feature combinations | Need source-level split checks when adding variants and training exports |
| Font work | Deterministic coverage sheets and glyph/fallback audits using Verovio's bundled fonts, including Petaluma | Font comparison tools are not a completed dataset augmentation pipeline |
| Scan degradation | Retained light-copy and framed/rotated library-scan Augraphy recipes with visual notebook | Library-scan visually approved; light-copy acceptable; not calibrated or evaluated with OMR; spatial recipe has no exported source coordinate mapping |
| Real transcription | Local Bar Review app exports reviewed crops and MusicXML | No OMR predictions; no assembled full-part export; fidelity needs manual review |
| Training | Existing MuSViT encoder plus autoregressive decoder; CPU integration check | Existing loaders consume other datasets and `bekern`; no loader for generated MusicXML parts; no demonstrated multi-page OMR path |

Important files:

- [Synthetic parts guide](experiments/full_page_omr/SYNTHETIC_PARTS.md)
- [Scenario sampler](experiments/full_page_omr/scenarios.py)
- [Generation and conversion](experiments/full_page_omr/generate_parts.py)
- [MusicXML serialization](experiments/full_page_omr/musicxml_score.py)
- [Font coverage guide](experiments/full_page_omr/FONT_COVERAGE.md)
- [Scan degradation guide](experiments/scan_degradation/README.md)
- [Scan degradation notebook](experiments/scan_degradation/scan_degradation.ipynb)
- [Bar Review guide](apps/bar_review/README.md)
- [Current datasets and token parsing](experiments/full_page_omr/data.py)
- [Training entrypoint](experiments/full_page_omr/finetune.py)
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

This is a recommendation from the 2026-10-31 review, not an implemented or
user-approved choice of tokenizer or multi-page architecture.

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

Immediate next action: write the target-format coverage table and executable
round-trip fixtures for a small representative selection of existing scores.

Other training details to revisit before a pilot: the current entrypoint defaults
to older `carlospm12/LSMT-MAE-Base-1024-16` weights, hard-codes a maximum target
length of 7512, and validates every 3500 epochs. Select and record explicit weights,
check target lengths, and use a useful validation interval for the small pilot.

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
  `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib MPLCONFIGDIR=/private/tmp/musvit-matplotlib .venv/bin/python -m experiments.full_page_omr.font_coverage --png`.
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

### Entry template

For each future session record: date and objective; concrete changes and paths;
decisions with reasons; commands/configuration/seeds and measured results;
limitations or blockers; and the exact next action. Link long experiment reports
instead of accumulating raw logs here. Update the current state when it changes.
