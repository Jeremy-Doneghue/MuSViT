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
| Splits | Separate seed domains and reserved feature combinations | Need source-level split checks when adding variants and training exports |
| Font work | Deterministic coverage sheets and glyph/fallback audits using Verovio's bundled fonts, including Petaluma | Font comparison tools are not a completed dataset augmentation pipeline |
| Scan degradation | Retained light-copy and framed/rotated library-scan Augraphy recipes with visual notebook | Library-scan visually approved; light-copy acceptable; not calibrated or evaluated with OMR; spatial recipe has no exported source coordinate mapping |
| Real transcription | Local Bar Review app exports reviewed crops and MusicXML | No OMR predictions; no assembled full-part export; fidelity needs manual review |
| Training | Local pretrained MuSViT encoder plus smaller existing decoder overfit 1/1 then 8/8 complete clean pilot pages on M4/MPS; image-swap control and re-engraving checks passed | Tiny in-sample memorization only; no held-out, dense-page, degraded/handwritten or multi-page performance demonstrated |
| Target format | User-approved `musvit-score-v1`; fixed 614-token vocabulary, round-trip fixtures and successful pilot learning | Restricted profile; continuation-page context, editor interoperability and exact historical-layout fidelity remain unverified |

Drum acceptance: user clarified that named sound/playback mappings are optional.
Require readable notation and arbitrary text instructions attached to their
passages. Verified standardization is acceptable; otherwise preserve source
noteheads/positions/text. The audit's named-mapping loss is not itself a blocker.

Important files:

- [Target notation coverage requirements](experiments/full_page_omr/TARGET_COVERAGE.md)
- [Target-format analysis and recommendation](experiments/full_page_omr/TARGET_FORMAT_ANALYSIS.md)
- [Implemented score codec and fixture guide](experiments/full_page_omr/SCORE_CODEC.md)
- [Executed overfit pilot and reproduction](experiments/full_page_omr/OVERFIT_PILOT.md)
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

Immediate next action: establish a source-disjoint held-out clean synthetic
baseline, increasing notation density toward realistic single-page parts before
scaling training or adding scan degradation. The user-approved
[tiny overfit pilot](experiments/full_page_omr/OVERFIT_PILOT.md) succeeded on eight
self-contained pages. Its adapter only supports page 1 of 1. Continuation-page
context, cross-page references and assembly remain separate work; do not cut
full-part tokens at page boundaries. Retain bekern as a baseline and preserve
semantic source scores rather than deriving canonical labels from rendering.

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
  [target coverage requirements](experiments/full_page_omr/TARGET_COVERAGE.md),
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
- Added `experiments/full_page_omr/audit_target_format.py`: executes unmodified
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
  `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib MPLCONFIGDIR=/private/tmp/musvit-matplotlib .venv/bin/python -m experiments.full_page_omr.codec_fixtures --output experiments/full_page_omr/outputs/codec_validation_v1_20261031_03 --png`.
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

### Entry template

For each future session record: date and objective; concrete changes and paths;
decisions with reasons; commands/configuration/seeds and measured results;
limitations or blockers; and the exact next action. Link long experiment reports
instead of accumulating raw logs here. Update the current state when it changes.
