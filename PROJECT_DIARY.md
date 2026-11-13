# MuSViT project diary

This is the session handoff: current state, standing decisions and next actions.
Detailed recipes, artifact paths and audits belong in the linked experiment reports.
Condensed at the user's request on 2026-11-04; the full earlier diary is available
in Git at `d1d4f3c:PROJECT_DIARY.md`. No historical experiments were rerun for this summary.

## Goal and standing decisions

Transcribe degraded scans of big-band instrumental parts, potentially handwritten,
into editable digital notation that can be re-engraved. Piano is the main
polyphonic case, but other instruments, independent voices and staff arrangements
must be supported. Current synthetic engraving results do not establish real-scan
or handwriting recognition.

- **2026-11-14 direction:** normalized Humdrum centered on **kern is the selected
  next model-target direction. First milestone includes pitched parts, piano,
  percussion, common dynamics and performance text; supported content should be
  transcribed with omissions flagged for review. See the
  [scope and initial conversion audit](experiments/full_page_omr/docs/HUMDRUM_SCOPE.md).
  Humdrum is now also the canonical source for new Curriculum Lab previews;
  Verovio derives SVG, MEI and raster images directly. MusicXML is optional at
  import/editor-export boundaries. See the [implemented preview pipeline](experiments/full_page_omr/docs/HUMDRUM_PIPELINE.md).
  Imported-score normalization and the new tokenizer/training adapter remain
  pending; existing datasets/checkpoints need no compatibility work.
- Earlier MusicXML-tree experiments remain historical tools. Their implemented restricted target is
  `musvit-score-v1` (614 fixed tokens); see the [codec contract](experiments/full_page_omr/docs/SCORE_CODEC.md).
  On 2026-11-06 the user also approved a diagnostic four-token pitch target,
  paired against the current target on the same all-pitches-taught images. It is
  restricted to the fixed one-note task, with MusicXML context supplied by code;
  it does not replace the full-score contract.
- Preserve written notation separately from playback expansion: repeats/endings,
  similes, multibar rests, D.S./coda, chord symbols and slashes carry meaning.
  Unsupported notation must fail explicitly rather than disappear from labels.
  User clarification (2026-11-06): codec restrictions are early-stage simplifications,
  not a permanent coverage boundary. Broader/full MusicXML acceptance is acceptable
  if restrictions hinder useful data or notation coverage. No replacement codec has
  been selected or implemented; distinguish preserving XML from validated musical
  interpretation and renderer support.
- Polyphony, text/instruction attachment and changing staff roles are required.
  Paired staves may be alternative repeat passages rather than simultaneous voices;
  instrument identity alone is insufficient to decide. Named drum playback mappings
  are optional; readable noteheads/positions, rhythms, voices and scoped text are
  required. Standardization needs verified conventions.
- Include readable content. Clipped but inferable notation is a required case;
  reconstruction/uncertainty policy remains open. Do not label inference as observation.
  The complete collection checklist and supplied-example observations are in
  [target coverage](experiments/full_page_omr/docs/TARGET_COVERAGE.md).
- Keep every page and engraving/degradation variant of a source composition in
  one split. Preserve source/family identity and provenance; never overwrite exports
  or tune against reported test outputs. Fixed vocabulary must not depend on held-out data.
- RGB/grayscale work was set aside by the user; it is not the next investigation.
- Full-page OMR, staff OMR, detection, synthetic generation, scan degradation and
  Bar Review remain in scope. Difficulty/embedding experiments and the legacy
  bekern/Lightning pipeline were removed. Consult the
  [original repository](https://github.com/OMR-PRAIG-UA-ES/MuSViT) for the latter.

## Current state

**2026-11-14 direct Humdrum curriculum pipeline:** user selected canonical
Humdrum sources and targets, optional MusicXML boundaries, and kern in the source
viewer. New Curriculum Lab previews now generate Humdrum directly for all eight
examples and render that exact source through Verovio to SVG/MEI/raster. No
MusicXML conversion, old codec/pilot exporter or ML dataset imports in this path.
Desktop/web text views display `source.krn`; previews, ZIPs and portable projects
retain it plus derived SVG/MEI. Native tests cover eight examples, three fonts,
pedal/text/percussion/cross-staff checks, deterministic replay, source reuse and
portable asset restoration. Full app suite: 70 passed in 15.500s; JS syntax and
whitespace checks pass. Headless native screenshots inspected. See the
[implemented pipeline](experiments/full_page_omr/docs/HUMDRUM_PIPELINE.md).
Limit: generated-source conventions only; arbitrary Humdrum normalization and a
new training tokenizer/adapter remain pending. Earlier MusicXML trainers are not
Humdrum trainers. Exact next action for the app: restart desktop/regenerate a
synthetic preview to inspect kern; for modeling: extend scoped-notation checks,
then define the Humdrum tokenizer/adapter before a fresh training export.

**2026-11-14 selected Humdrum scope and first smoke probes:** user approved the
kern-based direction and chose dynamics/performance text plus percussion alongside
pitched parts/piano from the first milestone, with supported content transcribed
and omissions flagged. Added [scope contract](experiments/full_page_omr/docs/HUMDRUM_SCOPE.md)
and isolated `diagnostics.humdrum_scope_audit`. Verovio 5.0.0 converts/reimports
horn, piano and drum fixtures without native failure. This is not fidelity
acceptance: horn instructions are not found in reimported MEI text, horn glissando
and piano pedal elements are absent, while drum instruction strings are found.
No normalizer/tokenizer/editor-export path or training change implemented.
Exact next action: isolate text, pedal and glissando conversion gaps with minimal
fixtures and select/repair a converter before freezing target conventions.

**2026-11-14 reference controls and faster panning:** resolution/zoom/Fit controls
now sit inside Source / Reference, above its image; Compare retains shared controls.
Drag panning caches a reduced page below 100% and uses fast viewport copies,
skips identical redraws and refreshes only visible image panes. Quick second
presses also start a drag. Local 75%-zoom headless trace: median frame 8.41→0.577ms,
p95 8.80→0.642ms (180 measured frames each; layout also changed, not an isolated
cache ablation or native latency guarantee). All 67 app tests passed; normal and
minimum-size screenshots inspected. Native Cocoa drag smoothness unmeasured.
Exact next action: restart desktop and try dragging a zoomed reference; new source
or zoom incurs one initial cache build, later drags reuse it.

**2026-11-14 Curriculum MusicXML inspector:** Curriculum now shows the rendered
reference beside a resizable, read-only MusicXML pane with monospaced text, line
numbers, vertical/Shift-horizontal scrolling and Top reset. Reads the exact source
artifact of the displayed preview; pending controls do not change its ownership.
Saved project XML restores through existing bundled assets; scan/no-preview states
show explanatory placeholders. Other workspaces retain their image/recipe views.
All 65 app tests passed, including new source binding/project restoration and
layout/scroll checks at normal/minimum window sizes. Real one-note engraving
headless screenshot inspected; native window interaction not repeated. No codec,
training, dataset or project schema change. Exact next action: restart the desktop,
generate or reopen a synthetic preview in Curriculum and inspect its source.

**2026-11-13 MusicXML normalization policy and executed audit:** user selected
retaining MusicXML, normalizing ambiguous features and considering explicit
omissions; clarified that existing datasets/checkpoints are disposable at this
early stage. This supersedes the earlier proposed Humdrum-first audit below.
Added [normalization policy](experiments/full_page_omr/docs/NORMALIZATION_POLICY.md)
covering canonical timing/divisions, chord/voice/direction ordering, defaults/IDs,
preserved notation and proposed named omissions. Added a renderer-free paired
codec audit: 15 cases, 9 satisfied, 6 normalization gaps, no lost distinctions or
probe errors; all token round trips/idempotence checks passed. Existing codec and
constrained-decoding suites: 23 tests passed. Production normalization is unchanged;
this completes policy/audit work, not its implementation. Exact next action:
apply exact timing/default/declaration cleanup directly to the current codec,
then event-based ordering with independent onset/span checks and rendering review.
No migration/version-compatibility work is required by the user.

**2026-11-13 Transcoda review (proposal, no implementation decision):** user
raised returning to **kern/bekern. Review supports prioritizing a compact,
normalized Humdrum target audit before a large training export, while retaining
MusicXML sources/interchange. Transcoda does not compare against our codec, and
its normalization includes target-content removal as well as canonical ordering.
Its note-focused contract strips text/dynamics and reports omitted courtesy
accidentals; that contract does not satisfy our complete-part requirements.
The historical bekern audit found implementation losses, not proof that Humdrum
cannot express the required notation. No codec replacement or pipeline restoration
was selected/implemented. Proposed next action: inspect Transcoda conversion and
normalization on our existing coverage fixtures, measure target lengths and
round-trip losses (including written pitch/transposition), then specify a bounded
comparison if coverage is adequate. This is a proposed refinement of the earlier
full-model-first sequence, not an agreed change to it.

**2026-11-08 reference-focused Curriculum and editable stages:** Curriculum now
hides the degradation sidebar/augmented column and shows a single reference
viewport beside the stage/source editor. Scan Recipe retains degradation editing
and paired views; Compare retains all levels. User selected full stage management:
Add/Duplicate/Remove/Move up/down (1–32 stages), unique editable names, descriptions,
learning focus/mix notes and supported source-type selection are implemented.
Stable stage identities are separate from backend generator IDs. Projects now
save as schema v2 with the complete curriculum plan/selection; old v1 projects
open with default stages. Mix notes are planning text, not a training scheduler.
All 63 app tests pass; normal/minimum-size geometry and screenshot inspected.
Native UI interaction was not repeated. Next action: restart desktop, customize
the stage list in Curriculum and Save project to retain the full plan.

**2026-11-08 desktop footer layout:** status and progress now share one footer
row, with progress aligned right at 30% of the available row width. All 11
desktop tests pass; visible-progress geometry checked at 1520×960 and 1060×760,
and headless screenshot visually inspected. Next action: restart desktop to use
the compact footer.

**2026-11-08 desktop File menu and shortcuts:** the workbench header now has
File → Open project, Save project, Save project as, Import/Export recipe and
Export preview ZIP. Command+S (Ctrl+S elsewhere) and the Save toolbar button
atomically update the current opened/saved `.musvitlab` without a browser,
retaining `.project-backups/`; untitled projects request a filename. Save As
(Command+Shift+S) always opens the browser and switches the current path only
after success. Open is Command+O; preview ZIP export is Command+Shift+E.
All 60 app tests pass, including actual menu clicks/shortcut events, current-path
updates, Save As/Open transitions and failed-write preservation. Headless menu
layout inspected; live Cocoa key delivery was not re-tested. Exact next action:
restart desktop, open/save a project, then use Command+S for in-place updates.

**2026-11-08 desktop code organization:** `desktop.py` now delegates initial
layout, reusable widgets, preview jobs, project actions and BUI-independent file
storage to five focused `desktop_*` modules. The coordinator retains live session
state, editing/view callbacks and resource lifetime; entry point and callback API
are preserved. See [desktop code navigation](apps/bar_review/README.md#desktop-code-navigation)
for module ownership and threading constraints. All 57 app tests pass after the
refactor; initial headless renders of all four workspaces are pixel-identical to
the pre-refactor version. Native Cocoa interaction was not repeated in this
session. Next action: continue workbench development using the module guide;
restart the desktop to load the refactor.

**2026-11-08 whole-project Curriculum Lab:** desktop Save/Open now operate on one
portable `.musvitlab` project, replacing the main individual-recipe save flow.
Projects contain up to eight independent named/ordered degradation levels,
recipes/ranges/seeds/manual values, exact current preview assets/manifests,
curriculum/source choices and workspace/view/region/theme/panel state. Defaults
are editable Clean/Mild/Moderate/Heavy exploratory starters. Compare shows source
and every level side by side; Generate all levels runs the common selected source
through each recipe on the warm worker. Stale/missing previews are indicated.
Real-scan projects embed the selected page; no annotation DB is created/changed.
Old v1/v2 recipe JSON can be imported into the selected level. Project updates are
atomic with `.project-backups/`; preview ZIPs still export only the selected
displayed preview. All 57 app tests passed, including portable restoration into an
empty data directory, pending edits versus displayed previews, bounds, layout,
scan restoration, hash/collision checks and level switching during rendering.
Native Cocoa Generate-all/Compare/Save/Open round trip restored exact full state
without re-rendering. See [desktop workflow](apps/bar_review/README.md#desktop-curriculum-lab-bui).
Exact next action: restart desktop, edit/add levels, open Compare and Generate all
levels, then Save project to retain the complete lab workspace.

**2026-11-08 recipe update persistence:** recipe Save now atomically updates an
existing chosen JSON instead of rejecting it, preserving prior bytes in sibling
`.recipe-backups/`. This fixes reloading an unchanged older file after an attempted
save. Save/Open remember the current recipe path and show it in status. Range
checkboxes and exact bounds passed a native existing-file Save/Open round trip;
all 11 desktop tests passed, including backup and failed-write preservation.
Preview ZIP exports remain exclusive-create. Restart desktop, then save the ranged
recipe to its existing filename and reopen it.

**2026-11-08 editable ranged preview sliders:** ranged numeric sliders now remain
editable within Min/Max and synchronize to the completed preview's chosen value.
Editing sets an exact preview override for Generate while preserving the saved
range; New sample clears overrides and resumes seeded sampling. Stale jobs do not
overwrite newer control edits. Requests/manifests record overrides for replay;
saved recipes retain the sampling distribution. All 49 app tests and a native
drag/manual-value/resampling/export check passed. Restart desktop to load it.

**2026-11-08 ranged recipe values:** every desktop numeric effect control now
supports optional Range/Min/Max. Rotation starts at −3°…+3°; fixed black/white
thresholds can use an integer interval. Each property samples uniformly from a
stable recipe-seed/step-ID/property stream; same seed replays, New sample advances
the seed and generates again. Exports retain bounds and actual sampled/backend
values. Ranged recipe JSON uses version 2; fixed version 1 files remain supported.
All 47 app tests and a native three-preview sampling/replay/export check passed.
Restart desktop and enable Range beside the desired numeric property.

**2026-11-08 file-dialog crash fixed:** Save/Open/Export now use non-blocking BUI
browser windows on the existing event loop. Reproduced the reported SIGABRT in
native Cocoa: closing blocking `filebrowser.ask()` returned to an invalid/
prematurely freed autorelease pool. The replacement survived close/Cancel,
save/reopen/export and parent-window shutdown in native macOS tests; all eight
desktop tests passed. Correction to earlier backend notes: sandboxed probes used
Tk because native availability was restricted there; outside the sandbox this
same wheel reports native Cocoa support and was tested with it. Restart the
desktop, then retry closing or cancelling Save Recipe.

**2026-11-08 resizable desktop regions:** draggable borders now resize either
sidebar and the source/augmented viewport split. Borders highlight on hover and
show a horizontal resize cursor; dragging clamps neighboring areas to usable
minimum widths. Double-click resets the sidebar layout or equal image widths.
Proportions survive workspace switches within the session and scale with the
window; hidden areas hide their dividers. Seven desktop tests and a live region
drag/redraw/workspace check passed. Restart the desktop to use the controls.

**2026-11-08 unified image viewports:** desktop source/augmented images now zoom
and pan directly, replacing separate page/detail sections and X/Y sliders.
Controls: Fit, 25–400%, −/+, wheel vertical pan, Shift+wheel horizontal pan,
Ctrl+wheel zoom, drag and arrow-key pan. Link views toggles synchronized relative
centers; resize/workspace changes redraw automatically. Only visible pixels are
drawn from cached source pages. Six desktop tests and a live zoom/scroll/resize
check passed; screenshots inspected. Restart the desktop to use the viewer.

**2026-11-08 Add Effect menu:** desktop effect insertion now uses a single
Blender-style Add Effect button opening categorized BUI submenus. Selecting an
effect appends it immediately; typing searches all categories, Escape dismisses,
and the button disables at 12 steps. Removed the separate effect dropdown.
All six desktop tests passed with actual popup search/selection, plus manual
headless checks of submenu insertion, dismissal, all 17 entries and stack limit.
Restart the desktop to load this UI change.

**2026-11-08 warm desktop worker:** the desktop now starts one persistent preview
process when its window opens, preloads engraving/Augraphy dependencies once and
submits serial jobs to that process's main thread. The existing GUI executor
thread handles IPC; native faults remain outside the UI process. Crashes,
connection failures and 120-second job timeouts retire the process; the next
preview automatically starts a replacement. Closing the app stops idle/active
workers. All 41 app tests passed, including cross-font replay in one process,
one-shot output equivalence and lifecycle failures. Live GUI warmup/repeated
light-copy previews/cleanup passed: 0.57s then 0.32s, same PID. Separate horn-page
benchmark after 1.64s warmup: light-copy 0.44s new source/0.22s reused, bound-copy
0.79s reused. These are local measurements, not a guarantee for the user's machine
or recipe. The user's reported ~10s startup is now paid once per desktop session
or worker restart. Web still uses fresh workers. Exact next action: restart the
desktop, wait for "Preview worker ready", then compare consecutive previews of
the user's slow recipe.

**2026-11-08 earlier preview optimizations:** progress now shows the active
phase/ordered effect and elapsed wall time. Clean/Pillow/OpenCV-only recipes skip
Augraphy imports, the desktop reuses hash-verified synthetic source engravings
within a session when inputs/code/dependency versions match, and detail panning
uses cached pages/in-memory crops. Manifests record phase and per-effect timings.
Matched single-run horn-page checks: clean 2.07→0.90s (0.14s reused source),
light-copy 2.19→1.38s reused source, bound-copy 2.74→2.12s reused source; all
image/MusicXML hashes matched. All 37 tests and a two-preview live-window
progress/reuse check passed. Those timings used fresh crash-isolated workers;
the current persistent desktop process supersedes that repeated-startup design.
Web gets conditional imports/timings, but progress and source selection reuse
are desktop-only.

**2026-11-08 desktop application:** a Python/BUI desktop Curriculum Lab now
shares the existing backend and catalogs. See
[desktop workflow](apps/bar_review/README.md#desktop-curriculum-lab-bui).
Blender-style top workspaces (Curriculum, Scan Recipe, Compare, Manifest),
collapsible/reorderable effect panels, native/model image comparison, pixel detail
inspection, recipe JSON save/load and immutable ZIP export are implemented.
Run `apps/bar_review/launch_curriculum.command` on this Mac, or install with
`uv sync --extra desktop` and run `.venv/bin/python apps/bar_review/desktop.py`.
The tested BUI 0.4.1 wheel uses its Tk window host here, with BUI-rendered Blender
components; no GPU claim or bundled/signed application. Direct RGBA image buffers
avoid a reproduced native crash in the wheel's asynchronous macOS image wake.
All 34 app tests passed; a live-window isolated Petaluma/rotation/DPI/bilevel
preview, workspace switching, export and clean close passed after that workaround.
Existing annotations/scans are read-only to this frontend; import scans through
Bar Review and refresh the desktop collection. Next action: open the desktop
launcher and review representative notation/scans and recipe orders for calibration.

**2026-11-08 application update:** added a local Curriculum Lab to
[Bar Review](apps/bar_review/README.md#curriculum-lab), reachable at
`/curriculum.html`. Five proposed stages, eight synthetic example types, imported
scan pages, real Augraphy controls, seeded previews, native/1024 comparison,
zoom/detail crops and immutable recipe/image ZIP exports are implemented. Uses
existing generators and accepted profile foundations; modified effects still need
legibility/calibration review. Preview artifacts are separate from reviewed pairs
and training data. App tests and HTTP smoke checks passed; browser interaction
QA remains unexecuted. SSH forwarding now accepts a different client-side
loopback port while retaining same-origin POST checks; restart the server to
load this fix. Preview rendering now uses a fresh subprocess per request after a
reported Verovio font-load/native abort; worker failures return JSON without
terminating the server. Nineteen app tests and four repeated cross-font worker
previews passed. Lab rotation now uses 2× supersampled bicubic/Lanczos sampling
instead of Augraphy's nearest-neighbour path. The lab now supports ordered
recipes: add/reorder/disable/remove scanner edge, PageBorder, framing,
BindingsAndFasteners, BadPhotoCopy, InkBleed and antialiased rotation, with per-step
controls and stable seeds. Scan resolution is now an additional ordered step:
explicit assumed canvas width and target DPI, reduced-pixel or restored-size
output, and source-resolution limits recorded. Black & white scan is also an
ordered effect with fixed/Otsu/adaptive thresholds and true 1-bit native PNG
export when last active; final model preprocessing remains RGB. Added DirtyDrum,
DirtyRollers, DirtyScreen, LinesDegradation, LowInkPeriodicLines,
LowInkRandomLines, Markup and SubtleNoise with per-effect controls. All 28 app tests pass; an isolated composite preview
was generated and visually inspected. Restart the server and reload the page to
load the new catalog/UI. Next action for the app: open the lab, compare representative
notation and real development scans, and select reviewed profiles for the first
curriculum export. Full-model preset/training work remains pending separately.

**2026-11-08 current direction:** user selected moving toward the full-size
paper-based OMR model and designing the curriculum/dataset for real sheet-music
scans, especially Augraphy appearance variation. See the new
[curriculum and dataset design](experiments/full_page_omr/docs/CURRICULUM_DATASET.md).
This supersedes the earlier priority of further one-note diagnostics. The move is
an engineering decision, not an isolated measured capacity benefit: replicated
placement diversity is the strongest recent finding. Proposed model is the
existing Base encoder plus upstream eight-layer/256-width decoder defaults;
feed-forward width and dropout also differ from our pilot factory. No model code
or training changed yet. Next action: explicit full-model preset and bounded
integration check, alongside a grouped real-scan calibration inventory and
reviewed augmentation contact sheets at actual model resolution. Sampling mixes,
counts and progression gates in the design remain proposals.

Latest completed run: seed-19 [placement replication](experiments/full_page_omr/docs/PLACEMENT_COMPARISON.md),
`outputs/placement_seed19_mps_20261108_01`. Same data/features/medium model/lr
.0001/bounds, new initialization and shuffle seed. Selected control 13/56
validation (23.21%); expanded 48/56 (85.71%), matching seed 7 expanded result.
Expanded selected/final training 224/224, all valid; selected update 11200,
final 16800. Control selected training 14/56; final training 33/56, validation
10/56 with 55/56 valid. Both completed 16800 updates; active 259.928/259.049s,
no cap. Placement benefit repeated, but only one of eight selected expanded
errors is shared across seeds. Same validation set, not independent datasets.
All 1344 predictions audited; all 280 feature hashes match seed 7. Appearance/
donor gates still fail. Next proposed action: inspect remaining error patterns
and specify bounded generalization diagnostic; no further run queued.

Previous run details retained below:

Previous result: [placement comparison](experiments/full_page_omr/docs/PLACEMENT_COMPARISON.md),
`outputs/placement_mps_20261108_01`. Same medium 4x256/lr .0001/initial weights,
frozen features, shared fresh validation, 16800 updates each. Four-placement
control selected 25/56 (44.64%) validation exact; sixteen-placement expanded
selected/final 48/56 (85.71%). Final training exact 56/56 and 224/224.
All outputs valid. Exposures 300/control image vs 75/expanded image; active times
250.830s/259.479s, no cap. Donor correctness matches validation. All 1344 saved
predictions audited. Supports placement variety in this single-seed task; eight
validation errors remain, appearance/donor gates fail. No test scoring or advance.
Next proposed action: bounded second-seed replication before adding complexity;
no further run queued. Previous 57.14% used different validation placements.

Previous experiments retained below:

Previous experiment: [medium lower learning rate](experiments/full_page_omr/docs/MEDIUM_LOWER_LR.md),
`outputs/medium_lr_mps_20261108_01`. Medium 4x256 at lr .0001 completed
16800 updates/300 presentations in 254.952 active seconds. Exact initial tensors,
112 feature hashes, image order/exposures match prior lr .001 medium run.
Selected=final: training 56/56 exact; new-placement validation/donor 32/56
(57.14%); all outputs valid. Validation correct trajectory 4/7/10/28/32 at
560/2800/5600/11200/16800. Sustained collapse avoided; training gate passes,
appearance/donor gates fail. All 504 saved predictions audited. No test scoring.
Single seed/simple pitch task; proposed next step is a bounded replication or
appearance-generalization comparison at .0001, neither launched.

Previous result retained below:

Previous result: [capacity comparison](experiments/full_page_omr/docs/CAPACITY_COMPARISON.md),
`outputs/capacity_mps_20261108_01`. Matched 16800 updates/order, score targets,
frozen features. Selected small training/validation 7/56 and 10/56; medium 8/56
and 7/56. Medium collapsed by 2800; later outputs invalid. Small final training/
validation 4/56 and 9/56, valid. Neither passed. Active times 139.675s/257.556s,
no cap. All 1008 predictions audited. Extra capacity did not help at lr .001.
Proposed next step: bounded lower-lr comparison; no further run launched.
User clarified the one-note question was not a requested change.

Previous experiment retained for context:

The preceding experiment is the [paired score/compact-pitch comparison](experiments/full_page_omr/docs/PITCH_TARGETS.md)
in `outputs/pitch_targets_mps_20261106_01/`. All 14 natural pitches C4–B5 taught;
56 training / 56 new-placement validation images, four correlated placements per
pitch per split. Shared sources/labels are intentional in this finite appearance
diagnostic; no composition-family isolation claim. Same cached frozen encoder
features, identical initial decoder state/model/vocabulary (614 tokens), seed 7,
image order and AdamW lr .001/no decay. Score target 157 tokens, pitch target four.
Both completed 16,800 updates / 300 presentations per training image, no time cap
hit; active training times 139.825s score / 142.173s compact, diagnostics additional.
Selection used validation pitch correctness, then validity/exactness, earliest tie.
Both versions failed the training/appearance/donor gate; no test scoring.

| Selected checkpoint outcome | Score target | Compact pitch target |
| --- | --- | --- |
| Selected update | 11200 | 560 |
| Training pitch / joint / exact | 35/56 (62.50%) | 4/56 (7.14%) |
| New-placement pitch / joint / exact | 18/56 (32.14%) | 4/56 (7.14%) |
| Training / validation validity | 56/56 each | 56/56 each |
| Swapped-image donor correctness | 18/56 | 4/56 |

The selected compact version predicts B5 everywhere (a constant-guess baseline).
Final score: training 8/56, validation 9/56 correct/exact, all outputs valid.
Final compact: all training/validation/swap outputs invalid, musically unscorable;
17/56 validation outputs reached EOS malformed, 39 hit the eight-token cap.
Gold compact labels export to exactly matching source MusicXML; all 672 valid
predicted exports passed audit. No parser repair or fabricated pitches.

Shorter output did not improve this matched run and did not reduce active training
time. Neither selected/final version mastered training. This does not establish
that compact targets are intrinsically unsuitable: loss allocation and sequence
length change together, and the common lr was not tuned separately. Next proposed
diagnostic is a bounded direct 14-way choice from frozen features, removing
sequence generation; optimization stability remains a separate candidate. No
further run is queued. Use "versions" with the user rather than unexplained "arms".

The [preceding longer one-note run](experiments/full_page_omr/docs/ONE_NOTE.md#executed-longer-run-result--2026-11-06)
on a different withheld-pitch dataset did achieve 80/80 training exact at 16k/24k,
with 0/32 unseen-pitch transfer, then collapsed near 28k. That establishes finite
memorization capacity but is not a controlled target-format comparison with this
new dataset. Its 8k weights did not exactly replay the first run despite seed 7;
cause unisolated. Earlier results/limits remain in the evidence table and reports.

Other retained capabilities and limits:

| Area | Established | Still missing / unverified |
| --- | --- | --- |
| Synthetic scores | Seeded horn scenarios, MusicXML/MEI, rendered measure/page alignment | Representative real-part coverage; broad instrumentation |
| Codec | Semantic/token round trips, polyphonic/percussion fixtures, re-engraving checks | Editor interoperability and complete collection coverage |
| Page export | Complete single-page examples with provenance and split checks | Continuation-page context, cross-page references and part assembly |
| Fonts | Verovio bundled-font coverage/fallback tools, including Petaluma | Integrated dataset font augmentation |
| Scan effects | Augraphy light-copy and framed/rotated library-scan recipes | OMR evaluation, calibration and geometry mapping for spatial labels |
| Bar Review | Reviewed crops and MusicXML export | OMR predictions, assembled full-part export and fidelity review |

## Proposed next investigations

The active design is [curriculum and dataset](experiments/full_page_omr/docs/CURRICULUM_DATASET.md).
The dated proposals below are retained history, superseded where they conflict
with the current direction above; they are not a queue of pending runs.

**2026-11-08 budget steering:** user prefers exploring a medium local pilot over
an expensive full reproduction. Proposed four layers/width 256 versus two/128,
using the existing all-notes appearance dataset and full score target first.
Keep encoder, labels, optimizer, image order and evaluation fixed; fresh small
control plus medium run, up to 16,800 updates or 600 active training seconds each.
This budget excludes extraction/evaluation and is not a total wall-clock promise.
Compare common reached checkpoints if capped. This is a capacity comparison at
one optimizer setting, not a paper reproduction; no training launched yet.


**2026-11-08 recommendation revision:** prioritize an audit against the published
full-page OMR recipe before selecting a replacement model. The paper reports
16.4% frozen-encoder and 10.9% fine-tuned average SER; our modified small-decoder,
restricted-target diagnostics are not a reproduction. Qwen remains a comparison
candidate, not an evidence-backed superior choice. Exact proposed next action:
compare original bekern data/tokenization, decoder, curriculum, optimizer and
selection settings with our implementation and specify a bounded reproduction.
No training or restoration of the removed pipeline has been authorized/launched.

**Next recommended diagnostic: direct choice among the 14 taught pitches.** The
paired output-target comparison is complete and failed. Specify a bounded small
readout from frozen features on the same known-label appearance task, preserving
spatial staff context, reporting training fit and new-placement accuracy separately.
It should remove autoregressive sequence generation rather than merely shorten
it. A failed linear readout would only establish failure of that readout; include
appropriate controls before drawing encoder conclusions. A separate controlled
learning-rate/stability comparison remains an alternative. Neither is launched.

User-reported pretrained baseline (2026-11-06): ChatGPT identified one uploaded
example as written G5 and additionally inferred Horn-in-F concert C5. The exact
image/model/prompt were not supplied here and the note identification has not
been independently verified. This motivates a fixed-sample pretrained vision-
language baseline alongside local readout diagnostics, before more custom training.
ChatGPT's already-trained image-to-language behavior is not equivalent to our
frozen visual encoder plus newly initialized decoder trained on 56 examples.
Do not infer its exact training data or internal mechanism from one response.
Inspecting the local G5 fixture confirms part-name "Horn" and no `transpose`
element; Horn-in-F is added context, not explicitly encoded in this pilot. Our
target is written G5; sounding-pitch conversion is separate. A broader baseline
must fix model, prompt and written-versus-sounding convention and measure actual
accuracy over balanced pitches/placements and representative passages. No API
call, new benchmark or image upload is authorized by this discussion.

The design notes below explain the completed [comparison](experiments/full_page_omr/docs/PITCH_TARGETS.md).
They are not instructions to repeat it or advance the curriculum automatically.

**Design basis: all pitches taught, new renderings held out.**
The user questioned withholding notes when a musician normally practices the full
note range, then asked for an independent recommendation. The recommended change
is based on task design and the observed 16k/24k training mastery: teach all 14
natural pitches C4–B5 at fixed duration/clef, with balanced examples, then measure
those same labels on new renderings/placements. Initially vary a controlled
appearance factor rather than adding multiple musical difficulties. A finite
one-note same-label rendering assessment explicitly differs from composition-
family-disjoint validation; preserve the old exports/results and document this
diagnostic policy before implementation. Do not disguise render copies as new
independent compositions. At the next sequence stage, all individual pitches
remain represented in training while complete held-out note sequences/families
test compositional transfer. Unseen absolute pitches can remain a separate later
rule-inference test, rather than the initial advancement requirement.

Initially proposed keeping the current encoder/decoder/codec for the all-notes comparison; propose
checkpoint selection on held-out-render pitch accuracy/validity, with fixed bounds
and snapshots declared before running, instead of aggregate token CE alone.
Treat the observed late collapse as a separate stability problem: preserve the
mastered snapshots and specify any lower/decaying-lr comparison independently.
This revised design was subsequently authorized and implemented in the paired
comparison. Its measured results are now summarized above; no new run is queued.

Output-burden clarification (2026-11-06): the user questioned jointly learning
notation recognition and MusicXML generation. Local code inspection confirms the
pretrained component is the image encoder; the small adaptor/decoder is freshly
initialized and predicts restricted MusicXML-tree tokens, which the codec writes
as XML. One note requires 157 output tokens, mostly constant structure. Existing
exact in-sample outputs establish capacity for this restricted target; valid but
wrong held-out outputs do not establish accurate reading or general MusicXML
coverage. Serialization burden may affect learning, but has not been isolated as
the cause of the held-out failure.

Completed experiment design: use one fixed all-notes-taught dataset and rendering
assessment for two matched versions, current score-token
target versus a compact pitch target, retaining the same frozen encoder and
decoder architecture/width/layers rather than also switching to a classifier.
Match image presentations, seed/optimizer settings and musical evaluation; report
runtime because target lengths differ. A deterministic writer can serialize the
compact pitch plus the task's explicitly fixed clef/meter/duration/staff context
into MusicXML. Fixed context is supplied by the experiment, not recognized.
When rhythm/voices/notation vary later, their information must become explicit
predicted fields/relations; a pitch list is not a complete big-band score format.
This tests output representation separately from the revised pitch-support split.
Do not compare a new compact/all-notes run only against the old withheld-pitch run
and attribute differences to representation. The paired diagnostic is now executed;
the compact representation has not replaced the general score codec.

**Other candidates: unseen-position readout and training-stability diagnostics.**
The longer one-note pilot mastered training at 16k/24k while failing held-out pitch
transfer, then regressed. A local pitch-feature probe can examine how accessible
staff position is without autoregressive decoding, distinguishing training fit
from unseen-position regression. Separately, a controlled lower/decaying-lr run
could investigate late instability; its cause has not been proved. Encoder
adaptation remains a later comparison, not an established fix. Specify probe or
comparison inputs, held-out task and compute bound before execution. Seed-19
replication is unrun; no further experiment is queued. See the
[one-note report](experiments/full_page_omr/docs/ONE_NOTE.md) for all executed results.
The wider curriculum below remains proposed and should not yet advance.

2026-11-06 clarification after reviewing the
[MuSViT paper, appendix A.9.1](https://arxiv.org/html/2606.31811v1#A9.SS1): frozen
encoder OMR succeeds in the authors' setup, supporting an expectation that useful
pitch information exists. Our failure does not establish an encoder deficiency.
First verify local checkpoint provenance against the intended published release:
the pilot setup report records a configuration from
`carlospm12/LSMT-MAE-Base-1024-16` and a hashed root weight file, while the current
release is `PRAIG/musvit`. Subsequent checksum check: the user reported MD5
`d4e67487e3b93d600609c5926e7e6b25` for their PRAIG download; our root weight file
matches that MD5 exactly and still matches the SHA-256 recorded in the pilot.
This resolves the weight-file mismatch concern against the user's download;
the older configuration identifier alone does not imply different weights.
Local code inspection confirms a strict
ViT weight load, unmasked ordered patch outputs, and 1024 RGB [0,1] preprocessing
consistent with the current model-card example; no new inference experiment ran.

Proposed probe design: bypass the 768-to-128 adaptor and autoregressive decoder,
retain the spatial encoder patches covering a fixed whole-staff region (not a
pitch-dependent note-centred crop), and fit a direct linear pitch readout. Report
training separability and same-pitch rendering robustness separately from unseen
pitch-position transfer. A classifier cannot evaluate a pitch class never used
to train its output: use ordinal staff-position regression for the existing
four-pitch holdout. Layout-only holdouts inside the training partition are an
explicit diagnostic of repeated targets, not source-disjoint validation. Include
label-shuffle/constant controls; a failed linear probe only rules out that readout,
not all information in the encoder. Strong raw-feature results would direct the
next check toward the adaptor, attention/decoding and optimization. This remains
a proposal; no new datasets, probes or weight downloads are authorized by discussion.

- Start with one note on a staff: vary pitch with fixed duration, then vary
  duration; progress to a few notes, complete bars, systems and pages. Add
  polyphony, notation features and degradation in later stages.
- Preserve realistic note scale/staff context, valid score labels and source-family
  splits. Vary one difficulty at a time initially and retain some easier examples.
  Advance on unseen-example musical accuracy, not training memorization or aggregate
  token accuracy. Eventually compare against a mixed-complexity baseline at comparable compute.
- The purpose is to locate the first recognition failure before further full-page
  scaling. A local pitch/rhythm feature probe and a lower-learning-rate comparison
  remain candidates; encoder adaptation and a compact event target are proposals,
  not selected changes to the architecture or score contract.

2026-11-06 initial recommendation (wider curriculum remains proposed; finite
pilot now executed above): defer broad PDMX training and a full-codec rewrite
until basic unseen-example reading works.
Use clean, realistic-scale staff contexts: one-note pitch discrimination, then
duration discrimination with pitch fixed, then joint pitch/duration combinations,
short sequences/complete bars, multiple bars/systems, polyphony and pages. Treat
this as a diagnostic ladder first; later compare curriculum against mixed training
at matched compute. Retain easier examples as stages advance. Use valid complete
scores (e.g. explicit pickups for short examples), balanced labels and separately
reported held-out content combinations and engraving/layout variations. Do not
confound first learning a symbol class with compositional generalization.

Provisional advancement gates: at least 99% joint pitch/duration event accuracy,
95% exact autonomous passage transcription and 99% semantic validity over at
least 100 held-out source families, with image-swap controls and replication under
a second training seed. These are suggested engineering thresholds, not research
results; fix the sample design and per-stage update cap before running. If the
one-note task fails, use a pitch/rhythm probe on the same encoder features and a
controlled lower-learning-rate comparison to distinguish feature accessibility
from sequence-decoding/optimization trouble. Consider encoder adaptation only
as a subsequent controlled comparison. Keep codec/model changes separate from
the first diagnostic. Introduce a curated simple PDMX subset once short-passage
transfer works, increasing musical and visual complexity separately. Real-scan
evaluation remains necessary. The initial proposed action was to specify the
one-note dataset, held-out splits, metrics and compute bound; the finite pitch
pilot above has now executed with its narrower evaluation claims and failed its gate.

**Longer training / delayed generalisation remains open.** The 40k one-note run
established training-set mastery at 16k/24k, but held-out pitch remained wrong and
training collapsed around 28k. A stable longer post-mastery window remains
untested. This does not predict delayed improvement; distinguish it from simply
running an unstable optimization longer. Short-staff training/mastery remains a
separate question. Saved checkpoints omit optimizer/RNG state, so loading weights
would not give an exact continuation.
Research context: [grokking](https://arxiv.org/abs/2201.02177),
[image-task evidence](https://proceedings.mlr.press/v235/humayun24a.html), and
[OMR curriculum learning](https://arxiv.org/abs/2405.12105); none predicts success here.

The authorized longer comparison and the subsequent all-notes-taught paired-target
comparison are complete. No experiment is running or queued. Direct readout
and controlled learning-rate comparisons remain alternatives, using the saved
16k/24k training mastery and held-out failures as evidence. The wrapper's
explicit extended mode retains the original default bounds and saves fixed-step
snapshots; it does not authorize automatic extensions, replication or curriculum
advancement. Preserve the current immutable export and all completed runs.
Longer systems/pages should follow evidence of short-passage transfer. Multi-page
recognition/context and assembly remain separate work; do not cut complete-score
tokens at page boundaries or assume concatenated page images solve continuity.

**Additional resource candidate (reviewed 2026-11-06): [PDMX](https://github.com/pnlong/PDMX/).**
The [Zenodo v9 release](https://zenodo.org/records/15571083) documents over 250K
MuseScore-derived scores, with MXL and corresponding PDF exports where available.
This could supply varied musical content for re-rendering/degradation and expose
codec coverage gaps. It does not establish recognition of historical scans or
handwriting, and representative big-band part coverage has not been measured.
The authors report conflicting license metadata for 12.29% of scores and recommend
`no_license_conflict`; their `all_valid` flag identifies available associated exports,
not compatibility with our codec. Metadata also includes deduplication groups.

Proposed first action if pursuing PDMX: audit a small, fixed sample from the
intersection of `no_license_conflict`, `all_valid` and `deduplicated`, stratified
across single-staff instruments, piano and percussion. Preserve original MXL and
provenance; inventory unsupported notation before defining any explicit import
normalization. Our codec rejects engraving coordinates and other common MusicXML
features, so direct compatibility is unverified. Compare source-PDF and imported
render semantics, including written repeats, voices and text. Group related
compositions/arrangements before splitting; the deduplicated subset alone does
not establish our family-isolation requirement. No download, importer, codec
change or training run is approved or queued by this resource review. One-note
transfer failure and late instability favor feature/optimization probes before PDMX.

## Experiment evidence to retain

All learning results below used a frozen encoder. These are development diagnostics,
not a representative real-scan benchmark. Exactness, EOS, grammar completion,
semantic validity and visual recognition are different outcomes. Invalid scores
remain musically unscorable; an empty valid subset does not imply zero musical error.

| Experiment | Main result and interpretation | Detailed report |
| --- | --- | --- |
| Tiny overfit, 2026-10-31 | One/eight sparse pages learned exactly; image swaps and pixel-identical re-engraving passed. Mac Studio reproduction passed. Pipeline/memorization check only. | [Pilot](experiments/full_page_omr/docs/OVERFIT_PILOT.md) |
| First 36-page baseline, 1200 updates | All 3 training samples, 6 validation and 6 test pages hit the token cap without valid scores/EOS. Training failure, not an established generalization gap. | [Clean baseline](experiments/full_page_omr/docs/CLEAN_BASELINE.md) |
| Dense overfit | One/two horn pages and six horn/piano/drum pages learned exactly; donor-following swaps and re-engraving passed. Fresh six-page decoder also passed, so warm-start was unnecessary for that seed/subset. | [Dense overfit](experiments/full_page_omr/docs/DENSE_OVERFIT.md) |
| Longer 36-page run, 14400 updates | Final sampled training 3/3 exact/valid, validation 0/6 valid. Selected checkpoint failed sampled training too. Demonstrates a sampled generalization gap at the final checkpoint. | [Long baseline](experiments/full_page_omr/docs/LONG_BASELINE.md) |
| Controlled edits | Trained one-note contrast passed; two unseen edits failed. Five trained edit controls passed; 5/7 unseen combinations exact. Limited composition within a memorized page, not unseen-score reading. | [Controlled edits](experiments/full_page_omr/docs/CONTROLLED_EDITS.md) |
| 180-page diversity, 14400 / 36000 updates | Both runs/checkpoints: sampled training 0/3 valid, validation 0/6 valid. Longer training did not consistently improve recognition. Includes underfitting, not just held-out failure. | [Diversity](experiments/full_page_omr/docs/DIVERSITY_BASELINE.md) |
| Constrained decoding | Initial comparison: all 12 grammar-complete, none semantically valid; token errors worsened. Later comparisons also produced no valid scores. Remains opt-in. | [Constraints](experiments/full_page_omr/docs/CONSTRAINED_DECODING.md), [longer results](experiments/full_page_omr/docs/DIVERSITY_BASELINE.md) |
| Short staff, 2026-11-01 | 0/48 valid validation and 0/3 valid sampled training at selected/final checkpoints; image sensitivity without reliable recognition. | [Short staff](experiments/full_page_omr/docs/SHORT_STAFF.md) |
| One note, 8k updates, 2026-11-06 | All outputs valid; full training pitch/exact 8/80 selected and 15/80 final; held-out and donor-reference pitch/exact 0/32 at both. Training recognition failure on finite pitch support. | [One note](experiments/full_page_omr/docs/ONE_NOTE.md) |
| One note, 40k updates, 2026-11-06 | Training exact 80/80 at 16k/24k, held-out pitch/exact 0/32; late loss spike and all final outputs invalid. Fresh seed-7 run does not exactly replay the original 8k weights. | [Longer one note](experiments/full_page_omr/docs/ONE_NOTE.md#executed-longer-run-result--2026-11-06) |
| All-notes paired targets, 2026-11-06 | Same images/features/initialization/order, 16,800 updates each. Selected score training/validation 35/56 and 18/56 correct; compact 4/56 each, predicting B5. Both gates fail; compact final predictions malformed. Latest result, summarized above. | [Paired targets](experiments/full_page_omr/docs/PITCH_TARGETS.md) |

The initial test set was scored in the first clean baseline; subsequent development
runs disabled test scoring. Use validation for development and preserve the test boundary.

## Workspace and supporting tools

Use the [full-page directory guide](experiments/full_page_omr/README.md) for module
ownership and commands. Current code is grouped into generation/, representation/,
datasets/, training/ and diagnostics/, with shared smt_foundation/ and reports in
docs/. `training/overfit_pilot.py` and `datasets/pilot_data.py` still provide shared
helpers; their historical names do not make them dead code. Full-page experiments
use Python module entrypoints; `musvit` lists only staff OMR and detection.

- [Synthetic parts](experiments/full_page_omr/docs/SYNTHETIC_PARTS.md): generator,
  provenance and scenario-specific split recipes. Reserved feature pairs in that
  sampler are not universal settings for the later clean-page/short-staff datasets.
- [Font tools](experiments/full_page_omr/docs/FONT_COVERAGE.md): use Verovio's bundled
  fonts, not the removed downloaded Petaluma bundle.
- [Scan degradation](experiments/scan_degradation/README.md) and its
  [notebook](experiments/scan_degradation/scan_degradation.ipynb): library-scan visually
  accepted, light-copy acceptable. Rejected worn/custom noise should not return as
  defaults without new review. Geometry-changing library-scan has no coordinate
  mapping; the random/JIT-state wrapper is not for concurrent threads.
- [Bar Review](apps/bar_review/README.md): local transcription review and export.
- [Historical target audit](experiments/full_page_omr/docs/TARGET_FORMAT_ANALYSIS.md):
  evidence behind the codec decision; the legacy parser/audit script is removed.

Generated data, reference scans, annotations, credentials and model weights stay
out of documentation/commits. Local artifacts live under each experiment's
outputs/; older full-page exports are under outputs/archive/. Shared real references
are in `data/reference_parts/`. Preserve immutable exports and recorded hashes;
old source/module paths in historical scripts may need migration before rerunning.

Local Mac Studio rendering setup and encoder config are under
`experiments/full_page_omr/outputs/studio_setup_20261031/`; installation/reproduction
is documented in the [pilot report](experiments/full_page_omr/docs/OVERFIT_PILOT.md#mac-studio-rerun--2026-10-31).
For the existing local setup:

```sh
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh
.venv/bin/python -m unittest discover -s tests -v
```

Latest regression check (paired-target setup, 2026-11-06): 86 tests ran, 85 passed
and one sandbox MPS check skipped, in 14.151s. New tests cover paired labels,
strict compact parsing/MusicXML export, explicit appearance-policy checks,
tampering, musical selection and both versions' CPU wiring. Retained tests include
extended bounds, snapshot evaluation and equal CPU final weights with/without saving.
The earlier dedicated suite also passed family-consistency/extra-note assertions.
Independent export audit
verified 336 artifact hashes, semantic round trips, grouped splits, matched-layout
donors and 112 distinct 1024 RGB inputs. These were setup checks; the subsequent
production MPS run and its independent prediction audit are recorded above/below.

Earlier regression check (legacy deletion, 2026-11-04): 78 tests ran,
77 passed/one sandbox MPS skip. Actual earlier MPS training/backward/cache checks
passed outside the sandbox. `uv lock --check --offline`, CLI registry, internal
imports and documentation links passed after deletion. These are recorded checks,
not new executions during diary condensation.

## Condensed session history

- **2026-10-31 — Requirements and representation:** established the re-engraving,
  polyphony and big-band notation contract; inspected supplied drum/alternative-pass
  examples without claiming transcription. Audited the original cleaned bekern path,
  then implemented the approved restricted codec and round-trip/re-engraving fixtures.
  Codec fidelity is distinct from recognition quality.
- **2026-10-31 — Tools and training:** retained accepted Augraphy profiles and bundled
  fonts; organized local artifacts. Tiny/dense overfit diagnostics passed, while the
  first held-out baseline failed. Longer training and controlled edits established
  memorization, a sampled generalization gap and limited local edit composition.
  Detailed results are in the experiment table; completed run-start/retry logs are
  omitted here.
- **2026-11-01 — Generalisation diagnostics:** diversity, additional updates and
  grammar constraints did not produce valid unseen scores. Short-staff transfer
  was implemented and executed; its failure shifted the proposed next work toward
  basic recognition/optimization diagnostics rather than full-page scaling.
- **2026-11-04 — Review and cleanup:** discussed delayed generalisation and recorded
  one-note curriculum learning as a candidate. Organized full-page code and reports,
  then deleted the legacy pipeline at the user's request, including its launcher,
  source-dependent audit and legacy-only dependencies (`names`, `wand`, `wonderwords`).
  Current experiments, shared model code and saved artifacts remain. User committed
  these changes before requesting this diary review.
- **2026-11-04 — Diary condensation:** replaced the 1529-line diary with this handoff,
  removing superseded milestones, launch/monitor instructions, temporary setup errors,
  repeated checks and duplicate report detail. Preserved standing requirements,
  key results/limits and unexecuted proposals; full prior text remains in Git.
  Documentation-only change; checked local links and whitespace, no tests/training run.
  Next action remains choosing/designing the next controlled recognition experiment.
- **2026-11-06 — PDMX resource review:** inspected the upstream README, paper abstract
  and Zenodo v9 release documentation, alongside the local codec contract. Recorded
  potential use as a score-content source and a proposed bounded compatibility audit
  above. No dataset files were downloaded or experimentally validated; codec acceptance,
  PDF/MXL fidelity, relevant instrumentation and family grouping remain unverified.
  Documentation-only change; checked diff whitespace. Exact next action for this
  candidate is to select and audit a fixed filtered sample before implementing an
  importer; this is a proposal, not a decision to replace the recognition diagnostic.

- **2026-11-06 — Codec scope clarification:** user clarified that the restricted
  codec was chosen for early simplicity and may be broadened to all MusicXML if
  it obstructs progress. Inspected current element/attribute allowlists and fixed
  vocabulary: removing rejection checks alone would not encode new XML names.
  Broad preservation, semantic validation and rendering need separate guarantees.
  No codec or vocabulary changed and no experiments ran. Next action, if pursuing
  broader support, is to design a versioned general XML encoding or schema-derived
  vocabulary and preservation checks, using a fixed PDMX sample to measure actual
  coverage needs; this implementation approach remains a proposal.

- **2026-11-06 — Curriculum sequencing discussion:** recommended prioritizing
  bounded recognition diagnostics before broad PDMX training, based on the recorded
  short-staff failure. Added proposed stages, advancement gates and failure branches
  above; these are recommendations awaiting experiment selection. Revisited the
  [OMR curriculum paper abstract](https://arxiv.org/abs/2405.12105), which supports
  curriculum as a research direction but does not validate these thresholds or this
  architecture. Also retained the user's intervening clarification: a codec rewrite
  may start fresh without maintaining multiple codec versions; incompatible tokens
  and checkpoints must still be detected, and existing exports stay preserved.
  Documentation-only change; diff whitespace checked, no tests or training run.
  Exact next action: define a bounded one-note pilot before implementation/execution.

- **2026-11-06 — Bounded one-note pilot setup:** user approved setup. Implemented
  `datasets/one_note_data.py`, `training/one_note_experiment.py` and dedicated tests;
  [fixed contract and launch command](experiments/full_page_omr/docs/ONE_NOTE.md).
  The shared dataset adapter now accepts explicitly grouped one-note raster
  variants while checking source/family consistency. No codec/model change.
  Final immutable export: `experiments/full_page_omr/outputs/one_note_pitch_20261106_03/`;
  80/32 training/validation images, 10/four absolute-pitch targets, 157-token
  labels under a fixed 256 cap. All page translations stay with their source.
  Explicitly documented that one-note transposition equivalence collapses the
  entire task, so this finite absolute-pitch holdout uses a different fingerprint
  and cannot claim composition-family transfer or 100 independent validation
  families. Earlier incomplete setup exports remain untouched.
  Bound: 8000 updates or 300 training-loop seconds; initialization/decoding are
  additional. Seeds 7 and 19 are fixed first-run/replication choices, not queued.
  Controls assess every training image, all held-out images, both checkpoints,
  gold-prefix fields and autonomous donor correctness. Invalid outputs remain
  unscorable and cannot earn success credit. No automatic stage advancement.
  Checks: 82-test suite passed with one MPS skip; final dedicated four tests also
  passed. Tiny random-encoder/forced-EOS one-update CPU smoke test exercised wiring
  only. CLI help and whitespace passed. Independently audited 336 artifact hashes,
  round trips, split/donor grouping, source hashes and 112 distinct 1024 RGB inputs;
  saved `setup_audit.json` in the export. Audit script:
  `/private/tmp/audit_one_note_20261106.py`; test logs:
  `/private/tmp/musvit-one-note-tests-20261106.log` and
  `/private/tmp/musvit-one-note-final-tests-20261106.log`. Visually inspected one
  validation page. Local encoder weight/config paths exist; production training
  and GPU behavior remain untested for this pilot. Exact next action: execute the
  documented seed-7 command in a new run directory and review selected/final gates.

- **2026-11-06 — One-note pilot execution:** user requested the prepared run.
  Sandbox MPS attempt stopped before initialization; preserved its empty `-01`
  run directory. Approved GPU execution in new
  `experiments/full_page_omr/outputs/one_note_pitch_mps_20261106_02/` completed all
  8000 updates, exactly 100 presentations/image, in 73.728 training-loop seconds;
  selected update 1600. Original contract unchanged; no time cap reached, no test
  scoring, encoder frozen, no production source-code changes. Both checkpoint
  controls completed successfully. All 294 autonomous outputs valid/EOS with
  correct constant duration; training pitch/exact 8/80 selected and 15/80 final,
  validation and donor-reference pitch/exact 0/32 at both. Selected predicts F5
  everywhere; final predicts only F5/F4/B5. All three gate checks failed. Fixed
  duration and score validity do not establish rhythm or pitch reading; this is
  a training-recognition failure, not only a generalization gap. Full results and
  limits: [one-note report](experiments/full_page_omr/docs/ONE_NOTE.md).
  Independent CPU audit recomputed all 294 autonomous metrics, verified 336
  artifact hashes, input/checkpoint identities, exposure counts, source-grouped
  donor/layout pairing, donor prediction consistency, totals and gate decisions.
  Saved `independent_audit.json` under the run. Gold-prefix fields were read from
  executed GPU controls, not rerun. Actual MPS training and cached/full-prefix
  decoder agreement passed. Latest regression suite remains setup's 82 tests
  (81 passed/one MPS skip); documentation whitespace checked after execution.
  Log: `/private/tmp/musvit-one-note-training-20261106-02.log`; audit script/output:
  `/private/tmp/audit_one_note_run_20261106.py`,
  `/private/tmp/musvit-one-note-run-audit-20261106.json`. Seed 19 and later stages
  remain unrun. Proposed exact next action: specify a bounded local pitch probe
  on these frozen features, reporting training fit and held-out-position transfer
  separately; no additional experiment was launched.

- **2026-11-06 — Encoder probe rationale and paper check:** user asked whether the
  MuSViT paper already supports encoder capability. Reviewed the original paper
  (especially A.9.1), author model card and local loader/preprocessing/feature path.
  Paper reports successful frozen-encoder OMR, so the probe is a local diagnostic,
  not evidence that the published encoder lacks pitch information. Flagged the
  older recorded configuration identifier versus the current published model;
  weight equivalence remains unverified. Proposed direct spatial-feature readout,
  separating training fit, layout robustness and unseen-position regression;
  noted unseen-label classification would be invalid. Documentation-only change,
  no inference/training/downloads; diff whitespace checked. Exact next proposed
  action: verify checkpoint provenance, then specify a bounded probe and controls.

- **2026-11-06 — PRAIG weight checksum comparison:** user supplied MD5
  `d4e67487e3b93d600609c5926e7e6b25` for their downloaded PRAIG `model.safetensors`.
  Executed local MD5 and SHA-256 checks: MD5 matches exactly; SHA-256 remains
  `109bbaf31d9f2184df1b841579e06d25bc58ed6a42a10dd5f4a5d27d01889db2`, matching
  the one-note run configuration. Our experiment used the same file checksum as
  the user's PRAIG download. This resolves the raised weight-file provenance
  concern; no weight replacement or retraining is needed on that basis. No new
  model inference or experiment ran. Next proposed action remains specifying
  the bounded direct pitch-feature probe; diff whitespace checked.

- **2026-11-06 — Longer one-note run discussion:** user asked about more training.
  Inspected saved training/validation loss histories and checkpoint keys. The
  final checkpoint omits optimizer/RNG state; loading decoder weights alone is
  not exact continuation. Proposed an unchanged fresh seed-7 40,000-update /
  900-training-second comparison with intermediate autonomous pitch measurements.
  Loss histories were nonmonotonic and validation CE best remained step 1600;
  existing 10%/18.75% training accuracy does not establish a plateau or predict
  later success. No code/weights/data changed, no additional training launched.
  Next action is to select this bounded comparison or the direct feature probe;
  an extended run requires updating the wrapper's explicit limits first.

- **2026-11-06 — Longer one-note run launch:** user authorized execution. Added
  explicit extended bounds (40,000 updates / 900 training-loop seconds) and optional
  fixed-step snapshots in the shared trainer. Evaluation decodes all training and
  validation images at reached 8k/16k/24k/40k snapshots after training, with final
  outputs reused; selected/final swap controls remain. CPU tests check both bounds,
  intermediate/final snapshot evaluation and identical final weights with/without
  snapshot saving. Full suite: 82 tests, 81 passed/one sandbox MPS skip, 12.681s;
  log `/private/tmp/musvit-one-note-long-tests-20261106.log`. Launch contract recorded
  before execution in [one-note report](experiments/full_page_omr/docs/ONE_NOTE.md).
  Fresh seed-7 MPS run launched with approved GPU access outside the sandbox in
  `experiments/full_page_omr/outputs/one_note_pitch_long_mps_20261106_01/`.
  Log: `/private/tmp/musvit-one-note-long-training-20261106-01.log`.
  Original dataset, weights, architecture and optimizer settings preserved. No
  numerical results yet. Exact next action: monitor completion, audit both controls
  and the fixed-step trajectory, compare the 8k snapshot with the prior final
  weights, then update the current state and report without launching another run.

- **2026-11-06 — Longer one-note run completed:** MPS run
  `outputs/one_note_pitch_long_mps_20261106_01/` completed 40,000 updates, exactly
  500 presentations/image, in 343.255 training-loop seconds; no time cap reached.
  Same data/model/lr/optimizer, frozen encoder, fresh seed 7, no test access.
  Selected update 1600 still predicts F5 (training 8/80 exact, validation 0/32).
  New 8k snapshot: training 21/80 exact with 58/80 valid; validation 0/32 exact,
  26/32 valid. **16k and 24k: training 80/80 exact/valid, validation 0/32
  pitch/exact with 32/32 valid.** This establishes training mastery and a finite
  held-out pitch gap, superseding the initial short run's undertraining-only
  evidence. Loss spiked around 28k; all 147 final outputs hit the cap without EOS
  or valid scores. Late instability cause remains unisolated. Both selected/final
  gate reports fail. No harder stage, replication or follow-up run launched.
  Audited all 630 saved autonomous predictions and intermediate musical totals,
  336 dataset artifact hashes, inputs/checkpoints, exposures, donor pairing,
  selected/final gates and final snapshot/last tensor equality. Compared new 8k
  to old final: all 57 tensors differ, max absolute difference 1.259953; numerical
  divergence cause is unisolated, so use within-run snapshots for time comparisons.
  Saved `independent_audit.json` under the run. Audit script/output:
  `/private/tmp/audit_one_note_long_run_20261106.py`,
  `/private/tmp/musvit-one-note-long-run-audit-20261106.json`.
  Full report/limits: [one-note report](experiments/full_page_omr/docs/ONE_NOTE.md).
  Actual MPS training/cached decoder agreement passed. Latest prelaunch regression
  suite is 82 tests (81 passed/one skip); no runtime code changes after launch.
  Documentation whitespace checked. Proposed next action: choose a bounded
  staff-position readout for transfer or a separate lower/decaying-lr comparison
  for stability; training-set mastery alone does not authorize advancing curriculum.

- **2026-11-06 — Reconsidering the curriculum gate:** user questioned whether
  withholding complete note positions was appropriate for initial music reading,
  then asked for an independent recommendation rather than deference to their
  analogy. Reassessed experiment design against the executed evidence: withheld
  absolute pitch positions test inference of untaught mappings; 16k/24k establish
  memorization of all taught targets, but do not test new appearances of taught
  labels. Recommended a new bounded comparison teaching all 14 pitches in the
  current range and assessing unseen renderings, then unseen sequences of known
  notes. Explicitly distinguish finite rendering assessment from composition-family
  isolation; preserve prior results and the harder unseen-position test. Proposed
  musical accuracy/validity for checkpoint selection and separate stability work.
  This corrects the role of the original gate, not its measured outcomes. No new
  experiment/code/data changed; documentation diff whitespace checked. Exact next
  proposed action: specify all-notes rendering pilot/split/evaluation/bounds before
  implementation; no further run is authorized by the discussion alone.

- **2026-11-06 — Recognition versus serialization discussion:** user questioned
  whether the current model is equipped to output MusicXML and whether two hard
  tasks are being learned together. Inspected the codec contract, fresh decoder
  construction, feature path and earlier exact-output evidence. Confirmed that
  MuSViT is the pretrained encoder; our new decoder learns both image-conditioned
  labels and the restricted MusicXML-tree token sequence. Restricted in-sample
  generation works, including 80/80 one-note targets at 16k/24k; neither general
  MusicXML coverage nor serialization as the cause of recognition failure is
  established. Recommended a controlled target comparison on the same future
  all-notes dataset, with the same decoder architecture and deterministic MusicXML
  export from compact predictions plus explicitly fixed task context. Later varied
  musical content must be predicted explicitly. No code/data/weights/experiments
  changed; diff whitespace checked. Exact next proposed action: specify the shared
  all-notes dataset, rendering assessment and paired target/evaluation/budget
  contract before implementing either arm.

- **2026-11-06 — Paired compact-target setup and launch:** user authorized trying
  the compact pitch target. Implemented an explicit all-pitches-taught appearance
  diagnostic, paired score/pitch labels and a matched autoregressive trainer;
  [prelaunch contract](experiments/full_page_omr/docs/PITCH_TARGETS.md). Four-token
  pitch stream reuses existing BOS/literal/EOS IDs and all 614 vocabulary entries;
  no classifier, masking or general codec replacement. Strict compact parsing
  and deterministic MusicXML export preserve the fixed fixture exactly for all
  14 pitches; quarter duration/clef/meter/part context are supplied, not inferred.
  New immutable export: `outputs/pitch_targets_20261106_01/`, 56 training and 56
  validation images, same 14 labels but disjoint fixed placements. Explicitly
  shared-source finite diagnostic, not composition-family isolation; original
  adapters still reject it and prior exports are preserved. One encoder extraction
  and one initial non-encoder state shared by both arms, seed/image order matched;
  same model and full vocabulary, full score target 157 tokens versus pitch 4.
  Bound 300 presentations/image / 16,800 updates or 600 active training seconds
  per arm; extraction/diagnostics additional. Musical validation selection at
  fixed checkpoints; selected/final train-all and same-placement donor controls.
  Dedicated four tests passed, then full suite: 86 tests, 85 passed/one MPS skip
  (14.151s). Logs `/private/tmp/musvit-pitch-target-setup-tests-20261106.log`,
  `/private/tmp/musvit-pitch-target-full-tests-20261106.log`. Independent audit
  verified 336 artifact hashes, 112 distinct 1024 RGB inputs, paired source/target
  semantics and source hashes; saved `setup_audit.json` under the export, script
  `/private/tmp/audit_pitch_target_setup_20261106.py`. Launched MPS outside the
  sandbox with approved GPU access in `outputs/pitch_targets_mps_20261106_01/`;
  log `/private/tmp/musvit-pitch-target-training-20261106-01.log`.
  No learning result yet. Exact next action: complete both arms, independently
  audit checkpoints/predictions/exposure matching, then update current results.

- **2026-11-06 — Paired target comparison completed:** MPS run
  `outputs/pitch_targets_mps_20261106_01/` finished both versions at 16,800 updates,
  exactly 300 presentations/image; active training times score 139.825s / compact
  142.173s, no time cap. Same 56/56 known-pitch/new-placement images, 112 shared
  frozen feature tensors, identical initial non-encoder state, same reconstructed
  image order/vocabulary/model/optimizer/lr. Selected score update 11200: training
  35/56 and validation/donor 18/56 pitch/joint/exact; all valid. Selected compact
  update 560: constant B5, training/validation/donor 4/56 each, all valid. Final
  score training/validation 8/56 and 9/56, all valid. Final compact outputs all
  malformed; validation EOS 17/56, remaining 39 hit cap 8. Both selected/final
  gates fail every check. No evidence that short output alone fixes learning at
  these settings; one matched learning rate is not an optimization study of each
  representation. No claim that compact targets cannot work or encoder lacks
  pitch information. Fixed MusicXML context is supplied rather than recognized.
  Independent CPU audit recomputed all 1008 predictions, verified all 672 valid
  MusicXML exports, 336 dataset artifact hashes, input/implementation hashes,
  checkpoint identities, selection/tie rules, musical totals, order/exposures,
  same-placement donors, donor-prediction consistency and gates. Saved
  `independent_audit.json` under the run. Audit script/output:
  `/private/tmp/audit_pitch_target_run_20261106.py`,
  `/private/tmp/musvit-pitch-target-run-audit-20261106.json`. GPU inference was not
  rerun by this audit. Actual MPS training and cached/full-prefix checks passed
  for both versions. Full prelaunch suite 86 tests (85 passed/one skip); no
  production code changes after launch. Documentation whitespace checked.
  Full report: [paired targets](experiments/full_page_omr/docs/PITCH_TARGETS.md).
  During execution the user asked what "arms" meant; explained the two experimental
  versions and adopted plain "versions" wording. No follow-up experiment launched.
  Exact next proposed action: specify a bounded direct 14-note choice from frozen
  features, removing sequence generation and measuring training/new-placement fit;
  keep optimization/stability comparisons separate and predeclared.

For future entries, record the decision/change, evidence or report link, remaining
uncertainty and exact next action. Keep the current state current; put long recipes,
full metrics and transient troubleshooting in subsystem reports rather than repeating them here.

- **2026-11-08 — Pretrained multimodal alternative review:** user asked about
  fine-tuning Qwen3.5 and whether the current architecture has sufficient capability.
  Reviewed diary evidence and local decoder defaults (width 128, two layers,
  frozen encoder). Current results establish limited memorization, not reliable
  recognition; they do not prove an architectural impossibility. Reviewed the
  official [Qwen3.5-9B model card](https://huggingface.co/Qwen/Qwen3.5-9B)
  (image/text input, Apache-2.0) and NVIDIA's
  [multimodal fine-tuning recipe](https://docs.nvidia.com/nemo/automodel/nightly/model-coverage/vision-language-models/qwen/Qwen3.5-9B).
  Proposed evaluating the intact pretrained VLM before adapter fine-tuning, using
  balanced written-pitch examples plus short passages and representative scans;
  retain musical metrics, source grouping and deterministic export validation.
  This is an alternative research direction, not an agreed replacement or evidence
  of Qwen OMR accuracy. Existing data/export/review infrastructure is reusable;
  model input processing, tokenizer and trainer require separate integration.
  No model download, inference, training or image upload executed. Exact proposed
  next action: specify a fixed Qwen3.5-9B baseline, output contract and compute
  bound before implementation; local memory/runtime feasibility remains unverified.

- **2026-11-08 — Published OMR success reconsidered:** user challenged abandoning
  MuSViT given its published results. Rechecked paper section 3.1 and A.9.1,
  tables 15–16: frozen SER 17.6/15.2 and fine-tuned 10.5/11.3 on
  Mozarteum/Polish Digital Scores, versus prior 14.1/25.8. SER is edit distance,
  not exact-page success. Paper trains on synthetic GrandStaff pages with an
  increasing-system curriculum, then mixes target scans; fine-tuning unfreezes
  the encoder at the real-page stage. Local pilot report explicitly documents
  a two-layer width-128 diagnostic decoder versus original eight-layer width-256
  configuration. Current experiments do not reproduce that recipe. Revised the
  previous preference for Qwen: audit/reproduce the published approach first;
  intact Qwen remains an untested alternative (paper compares visual encoders,
  not intact Qwen3.5). No experiment executed. Next action is the recipe audit
  specified above; documentation whitespace check passed.

- **2026-11-08 — Medium pilot proposal:** inspected paired trainer and model
  factory in response to budget constraint. Suggested four layers/width 256,
  retaining score targets and same 56/56 all-pitches placement diagnostic, with
  a fresh small control. Proposed retaining seed 7, AdamW .001 and existing
  checkpoint selection; optimization sensitivity remains a limitation. Executed
  CPU model construction/counting only with a config-bearing dummy encoder
  (initial dummy without config failed, then corrected); no data inference or
  training. Next action: expose bounded capacity/target selection in the paired
  runner, validate wiring and run the matched small/medium score comparison
  when proceeding with this proposed experiment. Existing exports preserved.

- **2026-11-08 — Capacity comparison authorized and launched:** user approved
  small/medium run. Added explicit `--capacity-comparison` mode to paired trainer,
  sharing frozen features across fresh 2x128 and 4x256 score decoders. Contract:
  [capacity comparison](experiments/full_page_omr/docs/CAPACITY_COMPARISON.md).
  Same existing all-pitches export, seed/order/optimizer/evaluation, 16800 updates
  or 600 active seconds per version, diagnostics extra. Full suite 86 tests,
  85 passed/one sandbox MPS skip (14.804s), including new capacity wiring check.
  Initial test attempt lacked native Cairo environment; passed after sourcing
  documented activation script. Log `/private/tmp/capacity-tests.log`.
  GPU run authorized outside sandbox, output `outputs/capacity_mps_20261108_01`,
  log `/private/tmp/capacity-training-20261108.log`. No results yet. Next action:
  monitor completion, audit musical totals and matched exposure, record results.

- **2026-11-08 — Capacity comparison completed:** matched 16800 updates/order,
  300 presentations/image. Selected small validation 10/56, medium 7/56;
  medium later collapsed (all final outputs invalid). No capacity benefit at
  lr .001. All 1008 saved predictions, exports, summaries and checkpoint selection
  audited on CPU; data integrity and implementation hashes verified. Report:
  [capacity comparison](experiments/full_page_omr/docs/CAPACITY_COMPARISON.md),
  including initialization metadata caveat. No inference rerun. Prelaunch 85 tests
  passed/one skipped; actual MPS cache checks passed. User's one-note question is
  not steering. Next proposed action: bounded lower-lr comparison, not launched.
  Explained persistent GPU approval through a narrow command-prefix rule using
  official OpenAI documentation; no permission settings changed. Whitespace checked.

- **2026-11-08 — Lower learning rate authorized and launched:** user approved
  medium .0001 run against completed .001 medium baseline. Added explicit
  `--medium-lr-baseline` mode and configurable lr; fail before training unless
  dataset/encoder identities, seed/resolution/presentations, frozen feature hashes
  and initial medium tensors match baseline. Contract in
  [lower-lr report](experiments/full_page_omr/docs/MEDIUM_LOWER_LR.md).
  Same 16800-update/600-active-second bound, evaluation additional; no new data.
  Full suite 86 tests: 85 passed/one MPS skip (15.415s), including baseline
  comparison wiring. Log `/private/tmp/medium-lr-tests.log`. GPU launch in
  `outputs/medium_lr_mps_20261108_01`; specific trainer prefix approval saved.
  Next action: monitor, audit matching exposures/initialization/features and
  musical outcomes against .001, update report. No results yet.

- **2026-11-08 — Lower-lr run completed and audited:** lr .0001 medium reached
  56/56 training and 32/56 new-placement/donor exact at selected/final 16800,
  all valid; active time 254.952s, 300 presentations/image, no cap. Initial
  tensors, features, order/exposures exactly match .001 baseline. Validation
  trajectory 4/7/10/28/32. Stable relative to baseline collapse; generalization
  still below gate. Audit verified 504 saved predictions/XML, summaries,
  checkpoint selection/hashes and data/implementation identities; no inference
  rerun. Report: [lower lr](experiments/full_page_omr/docs/MEDIUM_LOWER_LR.md).
  Prelaunch 85 tests passed/one skipped; actual MPS cache check passed. No follow-up
  launched. Exact next proposed action: specify bounded replication or placement
  generalization comparison retaining .0001. Documentation whitespace checked.

- **2026-11-08 — Placement comparison authorized and launched:** user approved
  four versus sixteen placements/pitch, fresh shared four-placement validation.
  Contract [placement comparison](experiments/full_page_omr/docs/PLACEMENT_COMPARISON.md).
  Added fixed placement recipe and dedicated runner reusing evaluated training
  logic; explicit common checkpoint steps support unequal dataset sizes.
  New immutable dataset `outputs/placements_20261108_01`: 224 train/56 validation;
  control is 56-image subset identical to previous training images. Setup audit
  verified all 280 distinct resized inputs and existing image/source identities.
  Fixed 16800 updates (300/control image, 75/expanded), 600 active seconds each,
  medium decoder/lr .0001, same restored initial tensors/shared cached features.
  Full suite 87 tests: 86 passed/one skip (16.244s), log
  `/private/tmp/placement-tests.log`; new CPU wiring covers common checkpoints
  and exposure counts. Run `outputs/placement_mps_20261108_01` launched on MPS;
  dedicated command-prefix approval saved. Next action: monitor both versions,
  audit outputs and common evaluation, record conclusions. No results yet.

- **2026-11-08 — Placement comparison completed:** both versions finished
  16800 updates without cap; selected control 25/56 validation, expanded 48/56.
  Final training 56/56 and 224/224; final validation 24/56 and 48/56. All valid,
  donor correctness matches validation. Same initial weights/shared validation;
  300 vs 75 presentations/image. Active times 250.830s/259.479s. More placements
  improved single-seed interpolation at fixed updates; not broad OMR mastery.
  Audit recomputed all 1344 predictions/XML, summary/donor/selection/checkpoint
  metrics and exposures; data and implementation identities verified, no inference
  rerun. Report [placement comparison](experiments/full_page_omr/docs/PLACEMENT_COMPARISON.md).
  Full prelaunch suite 86 passed/one skip; actual MPS cache checks passed.
  No further run launched. Exact proposed next action: bounded second-seed
  replication. Documentation whitespace checked; all previous exports preserved.

- **2026-11-08 — Seed-19 placement repeat launched:** user authorized replication.
  Exposed CLI seed choice 7/19, leaving recipe unchanged. Dedicated placement
  wiring test passed (1.231s), CLI help and whitespace checked; previous full
  suite remains 86 passed/one skip. Same dataset, lr .0001, medium decoder,
  16800 updates/600 active seconds per version, fresh seed19 initialization/order.
  Run `outputs/placement_seed19_mps_20261108_01` launched using saved GPU command
  approval. Contract appended to placement report. Next action: monitor both
  versions, audit and compare with seed7; no further experiment queued.

- **2026-11-08 — Seed-19 placement repeat completed:** selected control 13/56,
  expanded 48/56 validation; expanded training 224/224, all valid. Expanded
  selected 11200/final 16800 tie, earliest selected. Control final validation
  10/56, 55 valid; training 33/56. Full trajectory/limits in placement report.
  Both 16800 updates, no cap; active 259.928/259.049s. Benefit replicated
  despite control seed sensitivity; only one expanded selected error shared
  with seed 7. Audit checked 1344 saved predictions/XML, totals/selection/hashes/
  exposures; features and fixed settings match seed 7, initialization differs.
  No inference rerun; MPS cache checks passed. Dedicated test and CLI checks passed.
  No further experiment launched. Next proposed action: inspect remaining error
  patterns and specify bounded generalization diagnostic. Whitespace checked.

- **2026-11-08 — Full-model curriculum and scan-data direction:** user selected
  moving toward the paper-based full model and curriculum/dataset design. Reviewed
  latest recorded experiment results, local model factory/configuration, codec and
  generation contracts, and accepted Augraphy profiles. Rechecked paper A.9.1 and
  upstream decoder source online. Recorded that placement diversity improved both
  seeds, whereas capacity at the improved learning rate has not been isolated.
  Added [design](experiments/full_page_omr/docs/CURRICULUM_DATASET.md): explicit
  eight-layer model settings, separate musical/appearance progression, grouped
  sources and real-scan evaluation, provisional sampling/counts/gates, calibrated
  degradation families, legibility after resizing, ambiguity and geometry rules,
  and feature-cache implications. Updated directory guide and active direction;
  older proposals/results preserved as history. Documentation-only work: no new
  model configuration, dataset, training, image review or annotation executed.
  Checked local links in new design and documentation diff whitespace. Remaining
  limits: scan distribution/calibration and full-model resource costs unmeasured;
  curriculum efficacy and augmented real-scan recognition untested. Exact next
  action: implement explicit full-model preset and bounded integration check;
  assemble grouped scan calibration inventory and candidate augmentation contact
  sheets before freezing the first short-passage export and run budget.

- **2026-11-08 — Curriculum Lab implemented in Bar Review:** user requested a
  visual curriculum/augmentation explorer building on the local app. Added
  `curriculum.py`, lab HTML/CSS/JS, sidebar navigation and local API/artifact/ZIP
  routes. Reuses one-note, short-passage, complete-page and voice/percussion
  generators; exposes five proposed stages, eight synthetic example types,
  imported scan pages, three fonts, music/augmentation seeds, light-copy/library
  profiles, copy strength, rotation and Augraphy InkBleed. Preserves original
  annotation behavior, source scans and existing exports. Preview folders are
  unique and manifests explicitly unapproved/unassigned; serialization protects
  Augraphy global RNG/JIT state. Viewer has native/1024 input comparison, zoom,
  keyboard/click detail navigation, stale-settings indication and exact-preview
  download. No model, training or dataset split changed.
  Checks: all 14 app tests passed (9 existing plus 5 preview tests); all eight
  synthetic types rendered with combined library/rotation/ink effects. HTTP
  checks on a temporary loopback server passed for pages, catalog, document list,
  Petaluma passage preview, every artifact, ZIP and invalid-stage rejection.
  Inspected the generated 1024 augmented image; browser layout/interaction QA was
  unavailable and is not claimed. JS syntax and diff whitespace checked. Existing
  editor dependencies installed with pnpm because npm was unavailable; no package
  manifest/lockfile changes. Temporary installer scratch moved outside checkout.
  Local HTTP test artifacts: `/private/tmp/musvit-curriculum-http-20261108/`;
  test server stopped after checks. Runtime previews use the selected Bar Review
  data directory's `curriculum/` subdirectory. Limits: focused stage-3 coverage,
  no spatial mapping or automatic legibility judgment, real-page labels not
  inferred, and previews are not calibrated training pairs. Exact next action:
  visually exercise the lab with representative synthetic notation and imported
  development scans, then freeze reviewed augmentation recipes for the planned
  short-passage curriculum dataset.

- **2026-11-08 — SSH forwarding host validation fixed:** user encountered
  "Use the local loopback URL" through an SSH tunnel. Code inspection found
  the Host check required the browser port to equal the server listening port.
  Changed validation to accept localhost, 127.0.0.1 and [::1] with any valid
  client-side port (or default port), rejecting nonlocal, malformed and duplicate
  Host headers. Kept loopback binding and exact browser-origin POST checks.
  Added three regression tests covering forwarded hosts, invalid hosts and
  forwarded POST origin matching; all 17 app tests passed. Documented SSH
  forwarding and server restart. Diff whitespace checked. No live SSH tunnel
  was exercised; next action is to restart Bar Review and reopen it through
  the user's local forwarded port.

- **2026-11-08 — Native preview crash isolated:** user reported a browser fetch
  NetworkError and supplied terminal output: first preview and images returned
  200, then Verovio failed font/glyph initialization and aborted Python with
  uncaught C++ `std::out_of_range`. This establishes a renderer/server abort,
  not an SSH Host rejection. Installed Verovio initialization sets a default
  resource path on import; repeated HTTP request threads were sharing native
  renderer state. Exact internal native failure was not independently isolated.
  Changed the preview endpoint to launch a fresh Python process/main thread for
  each preview, inheriting the rendering environment; capture exit diagnostics,
  return JSON for failures and enforce a 120-second timeout. This also contains
  native aborts that Python exception handlers cannot catch. Added a useful
  connection-loss message in the frontend and documented worker behavior.
  Checks: all 19 app tests passed, including simulated native worker failure,
  timeout and a successful request following failure; four actual sequential
  isolated previews from distinct parent threads passed for Leipzig, Bravura,
  Petaluma, then Leipzig. Those integration previews used temporary directories.
  JS syntax and diff whitespace passed. No live SSH/browser retest performed.
  Existing scans, annotations and exports preserved. Exact next action: restart
  the server with the rendering activation environment, reload the browser, and
  retry consecutive previews through the user's tunnel.

- **2026-11-08 — Antialiased lab rotation:** user observed visible stair steps
  in rotated previews and clarified that the affected component is Augraphy,
  not Verovio. Inspected installed Augraphy 8.2.6: Geometric calls a Pillow
  rotate helper without a resampling argument (nearest neighbour). Replaced
  the lab's final rotation with Pillow bicubic at 2× resolution and Lanczos
  downsampling; preserve the expanded canvas, use white fill, and bypass all
  filtering at zero degrees. Other Augraphy effects and historical standalone
  scan recipes remain unchanged. Recipe manifests record the new backend,
  angle, filters and supersampling. Rotation-only previews now preserve RGB.
  All 20 app tests passed, including grey edge coverage, expanded dimensions,
  white fill, exact zero-angle pixels and ink conservation within 5% across
  ±1/±3-degree synthetic staff-line checks. Generated and visually inspected
  a 4× magnified before/after line comparison at
  `/private/tmp/musvit-rotation-antialiasing.png`; new edges are smoothly graded.
  Diff whitespace checked. No training run or real-scan calibration performed.
  Next action: generate a fresh rotated lab preview and inspect fine notation
  at native and model-input resolutions; old immutable previews are unchanged.

- **2026-11-08 — Ordered Augraphy recipe builder:** user requested composable
  effects with explicit application order, including border/framing,
  BindingsAndFasteners and BadPhotoCopy. Added validated `recipes.py` catalog and
  sequential executor, seven effect types, four starter recipes and per-step UI
  controls. Steps can be repeated, moved with accessible up/down buttons,
  disabled or removed; max 12 steps and bounded canvas growth. Added local
  punch/binding holes, clips and triangle clips with no external foreground or
  Figshare downloads. Rotation remains antialiased and now accepts fractional
  degrees. Stable effect IDs derive independent seeds from the recipe seed so
  reordering preserves each step's random stream, subject to upstream image and
  dimension changes. Exports retain requested/disabled steps, applied order,
  exact backend parameters/seeds/dimensions and recipe implementation hash.
  Legacy profile requests and existing artifacts remain supported/preserved.
  Checks: all 23 app tests passed, including replay, changed-order pixel
  difference, stable seeds, bypass equivalence, validation, four binding styles,
  and exported manifest order. Individually smoke-tested all seven effects.
  Isolated synthetic composite worker preview succeeded and its 1024 image was
  visually inspected at `/private/tmp/musvit-ordered-recipe-20261108/curriculum/d5ddd0aed2644698a525f2f66df32ca5/`.
  JS syntax and diff whitespace passed. Browser interaction QA remains unexecuted;
  composite profiles are experimental, not calibrated scan distributions. No
  training or existing dataset changed. Exact next action: restart Bar Review,
  reload the lab, load the border/framing/bindings/copy starter and compare orders
  on representative notation before selecting a dataset recipe.

- **2026-11-08 — Lower-DPI scan simulation:** user requested lower scan DPI.
  Added an ordered Scan resolution effect with target DPI (36–600), assumed
  current canvas width in mm, and reduced-pixel versus restored-size output.
  Uses Pillow BOX pixel-area averaging for sampling loss and optional bilinear
  enlargement. Does not invent source resolution: targets above available
  pixels bypass resizing and flag the limit in manifest/UI. DPI is explicitly
  conditional on the physical-width assumption, including prior framing; current
  1400px synthetic pages are approximately 169 DPI at 210mm width. Manifests
  record effective input/scan DPI, requested DPI, sampled dimensions and filters;
  geometry changes are marked for native-size reduction. Final model resizing
  remains separate. Existing previews/datasets unchanged.
  Checks: all 25 app tests passed, including expected dimensions, measurable
  fine-line detail loss, restored-size mode, exact equal/higher-resolution bypass
  and input validation. Isolated full-page horn preview at 75 DPI produced
  620x877 from 1400x1981 and was visually inspected. Artifact:
  `/private/tmp/musvit-scan-dpi-20261108/curriculum/78b2b43c49a8483dbc687edd3cb2f832/`.
  JS syntax and diff whitespace passed; browser QA not executed. Sampling only,
  not calibrated scanner optics/thresholding/compression. Next action: restart
  server, reload lab, add Scan resolution and compare 75/100/150 DPI on notation
  and real development scans at native and 1024 input sizes.

- **2026-11-08 — Bilevel scan simulation:** user explicitly requested actual
  black/white scan appearance rather than grayscale, extending the prior scope.
  Added ordered Black & white scan effect with fixed threshold, Otsu automatic
  global threshold and Gaussian adaptive threshold; adaptive window radius and
  offset are configurable. No dithering; output pixels are only 0/255 at that
  step. Save native augmented PNG as true 1-bit when this is the last active
  effect. Later effects may reintroduce grey, and the separate final RGB 1024
  bilinear model preprocessing intentionally remains unchanged. Recorded native
  PNG mode and effective threshold/backend settings in the manifest; documented
  placing thresholding after DPI/rotation for final bilevel capture.
  Initial test used only a smooth gradient and incorrectly expected adaptive
  thresholding to retain black pixels; corrected the fixture to include a local
  ink mark (an all-white adaptive result on that gradient was valid).
  Checks: all 27 app tests passed, including pure binary output in all three
  modes, fixed threshold boundary/ink coverage, actual mode-1 PNG export,
  expected grey edge pixels after model resizing, and RGB output after a later
  rotation. Diff whitespace checked. Browser QA and real-scanner calibration
  remain unexecuted; no existing exports or training changed. Exact next action:
  restart server, reload lab, append Black & white scan after DPI reduction and
  compare threshold settings on faint staff lines, dots and noteheads.

- **2026-11-08 — Eight additional Augraphy effects:** user requested DirtyDrum,
  DirtyRollers, DirtyScreen, LinesDegradation, LowInkPeriodicLines,
  LowInkRandomLines, Markup and SubtleNoise. Added all eight to the ordered
  recipe catalog/executor, exposing bounded controls for each effect and exact
  constructor parameters in manifests. Existing generic UI picks up the new
  catalog; all steps support order, bypass and stable seeds. Markup uses
  monochrome ink and detected content, so requested line counts are not
  guaranteed and marks are not added to musical labels. Initial smoke testing
  found DirtyRollers' import-time Numba dispatcher still compiled despite
  numba_jit=0, causing an AttributeError. The lab now calls the original Python
  mask function on that effect instance, avoiding global patches and preserving
  RNG/JIT restoration; this execution mode is recorded in manifests.
  Checks: all 28 app tests passed, including per-effect deterministic replay,
  unchanged source/dimensions, actual changed pixels on a staff fixture, and
  Python/NumPy/JIT state restoration. Eight isolated full-page horn previews
  also completed; visually inspected their contact sheet at
  `/private/tmp/musvit-added-effects-20261108/contact-sheet.png`.
  Artifacts reside beneath that directory's `curriculum/` tree. JS syntax and
  diff whitespace passed. Browser interaction QA and scan calibration remain
  unexecuted; effects are exploratory, not newly approved training recipes.
  No existing dataset/annotation/training changed. Exact next action: restart
  Bar Review, reload the lab, and tune the added steps on representative music
  while checking that distinguishing notation remains readable.

- **2026-11-08 — BUI desktop Curriculum Lab:** user requested a desktop version
  using BUI's Python Blender components, then selected Blender-style top mode tabs.
  Inspected the supplied upstream repository and installed/pinned optional
  `blenderui==0.4.1`; updated `pyproject.toml`/`uv.lock` without changing the core
  dependency versions. Added `apps/bar_review/desktop.py`, executable macOS
  `launch_curriculum.command`, six desktop integration tests and README workflow.
  Four shared-state workspaces expose five proposed stages/eight examples/three
  fonts/all 17 ordered effects; collapsible panels support native grip dragging,
  Up/Down, bypass and removal. Viewer has native/1024 comparison, click/slider/key
  relative focus and 100/200/400% nearest-neighbor pixel detail. Added versioned
  scan-recipe JSON save/load, displayed-preview manifest and exclusive-create ZIP
  exports. Background worker requests snapshot controls/documents, recover errors
  and indicate mid-render edits. Uses the existing isolated Verovio worker and
  immutable preview backend; reads existing scan DB read-only without initializing
  it. Original web backend, exports, annotations, models and training unchanged.
  Executed checks: all 34 app tests passed (28 existing plus 6 desktop); actual
  BUI input tested workspace clicks and native panel-grip recipe reordering;
  checked layout bounds, letterbox hit testing, worker failure recovery/stale
  request snapshots, JSON validation, read-only collection and exact ZIP hashes/
  refusal to overwrite. Initial real passage worker and ZIP passed. An actual
  window opened/closed, but the first live image preview crashed with SIGSEGV.
  macOS report showed BK_image_poll → bk_ctx_dirty_rect → Python callback on
  the Tk/Cocoa event loop. Inspection points to the released wheel's unguarded
  async redraw callback/GIL interaction; the precise upstream defect was not
  independently isolated. Replaced file-backed async image loading in the viewer
  with Pillow-decoded RGBA buffers passed to BUI; reuse unchanged page buffers.
  A repeated live-window Petaluma full horn preview with rotation -1°, 75 DPI,
  Otsu threshold completed in 3.65 seconds through display/export/workspace
  switching and clean event-loop shutdown. Native output was 620x867, true 1-bit.
  Artifact: `/private/tmp/musvit-desktop-gui-fixed-20261108/curriculum/f88db588448348feab7f6f70b633e6e0/`;
  ZIP beside its curriculum directory. Dark preview and light Compare layout
  screenshots were visually inspected. Launcher headless screenshot, Python
  compilation, shell syntax, offline lock consistency and diff whitespace passed.
  Limits: this Mac's wheel reports no native C window host and uses BUI's Tk host;
  GPU acceleration and a packaged/signed `.app` are not delivered. File-dialog
  interaction and extended manual usability review remain unexecuted. Detail
  viewports are relative and need refreshing after width changes; no spatial
  registration, legibility approval or scanner calibration added. Exact next
  action: open the desktop launcher and exercise recipes/export dialogs against
  representative notation and imported development scans before approving data.

- **2026-11-08 — Preview progress and measured startup reductions:** user reported
  slow desktop previews and requested progress plus straightforward optimization.
  Profiled original clean/light-copy/bound-copy horn-page workers (music seed 7,
  Leipzig, recipe seed 42): clean still loaded Augraphy's complete stack;
  profiled import cost was roughly 1.5–2s, with source generation/rendering around
  1s. These profiles include profiler overhead, not direct speed-comparison data.
  Added atomic worker progress sidecars read by a short-lived monitor thread,
  queue-based desktop updates on the UI thread, a BUI progress bar with named
  phases/effects and elapsed clock, completion duration and source-reuse status.
  Bar fractions are pipeline milestones, not wall-time predictions. Manifests now
  store source/augmentation/save/worker timings and separate per-effect durations
  without making deterministic effect records depend on runtime measurements.
  Deferred Augraphy imports for clean/disabled-only and rotation/DPI/threshold
  recipes. Added desktop session source reuse (up to 64 source selections):
  match request fields, relevant generator/renderer/codec code and dependency
  versions, verify PNG/MusicXML hashes from an immutable previous preview, and
  fall back to rendering if absent/corrupt. Source reuse creates a distinct new
  preview, never overwrites the earlier one, and does not reuse real-scan files.
  Removed detail PNG write/reopen cycles and repeated full-page decode while
  panning; BUI receives in-memory RGBA crops and still avoids its unsafe async
  file-image callback. Documented operation, limits and measured timings.
  Checks: all 37 app tests passed, including three new checks for avoided imports,
  source/input/code/hash invalidation with identical source pixels, actual isolated
  worker progress/timing delivery; extended desktop test checks progress and
  completion. Existing worker timeout/failure, RNG/replay, geometry, immutability,
  browser/server and desktop behavior checks still pass. A live two-preview
  desktop check completed in 2.40s then 2.09s with source reuse; active/completed
  progress screenshots generated, active screenshot visually inspected, event
  loop closed cleanly. Python compilation and diff whitespace checks passed.
  For unprofiled comparisons, copied the original backend from Git into temporary
  scratch, adjusting only its repository-root lookup. One new-worker run per case
  before/after: clean 2.070→0.895s; repeated clean with source reuse 0.140s;
  light-copy 2.192→1.377s reused; bound-copy 2.744→2.115s reused. Every PNG and
  MusicXML hash matched the baseline. Light-copy effect execution was 0.0381s;
  remaining augmentation time (~1.03s) was predominantly dependency setup.
  Bound-copy rotation was 0.5003s. Benchmark artifacts/configs/results:
  `/private/tmp/musvit-preview-profile-20261108/`,
  `/private/tmp/musvit-preview-baseline-20261108/`,
  `/private/tmp/musvit-preview-final-20261108/comparison.json`;
  live check: `/private/tmp/musvit-desktop-progress-live-20261108/`.
  Limits: single-run timings on this Mac, not broad effect/resolution calibration;
  fresh isolated workers still pay imports for actual Augraphy recipes. No
  persistent renderer/native state sharing, recipe reordering, quality reduction,
  training, source-scan edits or existing export changes. Browser progress/source
  reuse was not added. Exact next action: restart the desktop and inspect the
  active effect plus exported timing manifest for the user's slow recipe before
  choosing further effect-specific optimization.

- **2026-11-08 — Persistent desktop preview worker:** user reported ~10 seconds
  in "Starting preview worker" and requested an always-running worker receiving
  jobs. Added `preview_worker.py`: one long-lived subprocess with serial stdin
  job submission and atomic result/progress files, no stdout protocol dependence.
  The process preloads Verovio/Cairo, generator dependencies and Augraphy on its
  main thread, then blocks waiting for jobs. Each render/toolkit is also created
  on that same thread; the previous per-request HTTP-thread renderer problem is
  not reintroduced. Desktop starts warmup through its existing executor when the
  window opens, reports loading phases/readiness, queues Generate behind warmup,
  keeps the process idle between requests and retains source-reuse/progress.
  Native exits/broken connections/job deadlines retire the process and restart
  on the next request; validation errors preserve it. Startup has its own
  120-second deadline, preview execution has 120 seconds, and close terminates
  even an active worker without waiting for its serial job lock. Failed jobs
  are not automatically replayed. Web one-shot worker behavior is unchanged.
  Updated README to distinguish warm desktop behavior from earlier fresh-worker
  timing measurements; existing data, recipes and immutable exports preserved.
  Checks: all 41 app tests passed (four new persistent-process tests), including
  six cross-font passage renders in one PID with exact replay, equivalent image/
  MusicXML hashes versus a one-shot worker, invalid request recovery in the same
  PID, simulated fatal exit and timeout followed by successful real replacement,
  startup timeout and active-job close/cleanup. First manual warm-worker check:
  warmup 2.389s, four same-PID cross-font light-copy jobs 0.392/0.265/0.269/0.267s.
  Separate horn-page benchmark: warmup 1.636s; light-copy new source 0.437s,
  reused source 0.222s; bound-copy reused source 0.787s, all one PID. Config:
  stage 2 horn_page, Leipzig, music seed 7, recipe seed 42. Results/artifacts:
  `/private/tmp/musvit-warm-worker-benchmark-20261108/benchmark.json`.
  Actual desktop `run()` warmup/readiness and two jobs passed at 0.57s/0.32s,
  same PID; second reused its source. Window shutdown terminated the process
  and removed its IPC directory. Live artifacts:
  `/private/tmp/musvit-warm-desktop-live-20261108/`. Python compilation and diff
  whitespace passed. Limits: local warmup measurements do not reproduce or
  dismiss the user's reported ~10s startup; that cost remains once per session/
  restart. Larger pages/heavy effects still take computation time, and long
  soak/memory-growth testing remains unexecuted. Exact next action: restart the
  desktop and compare consecutive previews after "Preview worker ready" on
  the user's slow recipe; inspect per-effect timings if computation remains slow.

- **2026-11-08 — Blender-style Add Effect popup:** user supplied a Blender Add
  Modifier screenshot and requested direct effect insertion from a button/menu.
  Replaced the desktop effect dropdown/button sequence with Add Effect opening
  BUI's own popup menu: Paper & framing, Ink & printing, Dirt & interference and
  Scan & geometry. Native type-to-search finds leaves across all categories;
  selecting a leaf appends a default-parameter step with a fresh stable ID.
  Escape cancels, existing order is retained, and the 12-step guard remains.
  README updated. All six desktop tests passed; the recipe integration test now
  opens the popup, types a search and clicks its result before verifying reorder/
  save/load. Additional headless interaction checks confirmed all 17 catalog
  effects appear exactly once, hovering a category opens its submenu, selecting
  DPI adds it and closes popups, Escape adds nothing, and insertion stops at 12.
  Popup/submenu screenshots generated and submenu layout visually inspected.
  No renderer, recipes, worker lifecycle, datasets or exports changed; full
  backend suite was not repeated for this UI-only edit. Exact next action:
  restart the desktop and use Add Effect, then choose a category/item or type
  to search. Live mouse/keyboard usability review remains available to the user.

- **2026-11-08 — Unified zoomable main image viewports:** user requested replacing
  the separate full-page and zoomed sections with main-image zoom and scrolling.
  Replaced both page/detail pairs with clipped BUI image viewports, a Fit/25–400%
  selector, −/+ and Fit buttons. Wheel pans vertically, Shift+wheel horizontally,
  Ctrl+wheel changes zoom, dragging pans, and existing arrow shortcuts pan.
  Link views defaults on and synchronizes relative image centers; turning it off
  permits independent panning. Same percentage zoom applies to both images.
  Removed detail crops and X/Y sliders. Fit centers the complete image; scroll
  is bounded to image edges and disabled when the complete image fits. Native
  100% maps an image pixel to a UI raster pixel, enlargement uses nearest-neighbor
  and reduction uses bicubic. Viewport resize events automatically redraw, using
  affine sampling of visible pixels from cached pages and direct RGBA delivery
  to BUI. No oversized scaled image buffers or temporary crop files introduced.
  README updated. Checks: six desktop tests passed; replaced the earlier detail
  hit test with actual wheel/Shift/Ctrl/drag events, linked/unlinked centers,
  viewport bounds, immediate decoded pixels and resized Fit behavior. Live BUI
  window check loaded an existing immutable horn-page preview, zoomed to 100%,
  scrolled, switched to full-width Compare and closed cleanly. Both layout
  screenshots were visually inspected. Python compilation and diff whitespace
  passed. Full backend suite not repeated for this frontend-only change; worker,
  generation, recipes and existing exports untouched. Relative linked viewports
  are not geometric registration after augmentation. Exact next action: restart
  desktop, generate a preview, zoom the main images and scroll/drag to inspect;
  turn off Link views when independent positioning is preferred.

- **2026-11-08 — Resizable Blender-style regions:** user requested resizing the
  sidebars and viewports like Blender. Added reusable component-based region
  dividers and rows using BUI pointer capture/cursors: one border at each sidebar
  and one between source/augmented views. Drag redistributes only the adjacent
  areas' width shares, with minima (source 180px, central viewer 320px, recipe
  220px, image columns 120px each) enforced while dragging. Proportions scale with
  the window; for windows below a pair's combined minimum the drag bounds scale
  down proportionally. Border hover highlights and horizontal resize cursors
  expose the interaction. Double-click resets the corresponding full row's
  default proportions. Workspace visibility also hides unused dividers; the
  remaining weights are preserved. No disk layout persistence or arbitrary
  region splitting/joining added. Image resize notifications redraw the current
  zoom/pan without generating a new preview. README updated.
  Checks: seven desktop tests passed, including actual captured multi-motion
  drags on all three borders, independent neighboring widths, minimum clamp,
  automatic Fit redraw, cursor feedback, double-click reset, hidden borders and
  preserved ratios across workspace changes. Request/displayed manifest identity
  remained unchanged. Live BUI window check dragged all borders while showing
  an existing horn preview, verified unequal viewport widths and Compare mode
  visibility, and closed cleanly. Resized layout screenshot visually inspected;
  Python compilation and diff whitespace passed. Backend suite not repeated for
  this layout-only edit; source images, recipes, workers and exports unchanged.
  Exact next action: restart desktop and drag the dark borders beside sidebars
  or between the images; double-click a border to restore default widths.

- **2026-11-08 — Native macOS file-dialog close crash repaired:** user reported
  app termination when closing Save Recipe. Read the actual macOS crash report:
  SIGABRT, objc autorelease-pool fatal path returning through BUI BK_window_run.
  An unsandboxed probe confirmed native Cocoa availability; earlier sandboxed
  probes reporting false did not establish that the wheel lacks a native host.
  Corrected README/current-state backend description explicitly; historical
  observations retained. Reproduced using the original blocking filebrowser.ask
  from a native callback, closing its child window: method returned, then process
  aborted (exit 134) with "Invalid or prematurely-freed autorelease pool".
  Inspection found filebrowser.ask recursively pumps host.update/kit_pump inside
  the main native loop. Replaced that path with `desktop_dialog.py`: same Blender
  filebrowser node in a retained window/context, parent-window timer polling and
  deferred close/callback disposal, with no nested event loop. Save/Open/Export
  now return immediately; duplicate opens focus the existing child, cancellation
  writes nothing, and main-window close disposes the child/cancels its timer.
  Recipe bytes and preview ID are captured at dialog-open time so background
  preview completion/control edits cannot change the selected export mid-dialog.
  Exclusive-create writes still preserve existing files. README updated.
  Checks: exact native reproduction survived after fix, followed by a native
  end-to-end close-request, actual Cancel-button click, recipe save with extension,
  recipe reopen, preview ZIP export and closing the main app with a browser open.
  All passed with clean native event-loop exit. One attempted automated Escape
  check did not dismiss the browser (focus/key routing) and hit the test deadline;
  no native abort occurred. Replaced that test action with an actual Cancel-button
  click; no claim of verifying Escape behavior. Native round-trip artifacts:
  `/private/var/folders/c4/krtyyfns7mbgvrd43qzdkb8r0000gn/T/musvit-dialog-roundtrip-ykncqllx/`.
  Eight desktop tests passed, including new cancellation, duplicate-window focus,
  recipe/preview snapshots, no-overwrite error handling and owner-close regression.
  Python compilation and diff whitespace passed. Full backend suite not repeated;
  rendering, augmentation, workers and existing data/exports unchanged. Exact
  next action: restart desktop and retry closing/cancelling Save Recipe; verify
  the same behavior for Open Recipe and Export in normal use.

- **2026-11-08 — Seeded parameter ranges in effect recipes:** user requested
  ranges such as rotation ±3° and black/white threshold. Added optional numeric
  `ranges` per step, retaining fixed parameters as fallbacks. Validates numeric
  fields only, exactly two finite/in-bounds ordered endpoints and integer bounds
  for integer properties. Samples independently per parameter using a local
  SHA256-derived RNG from the existing stable effect seed; no global RNG changes,
  reorder-dependent reassignment or changes to fixed recipes' effect records.
  Integer bounds are inclusive, fractional properties sample continuously.
  Effect manifests add requested_ranges, sampled_parameters and sampling rule
  only for ranged steps; exact backend parameters remain recorded separately.
  Desktop numeric controls now have Range checkbox and Min/Max fields, preserving
  valid endpoint ordering. Rotation initially uses the existing full ±3° bounds;
  other properties start at their current fixed value. New sample increments
  recipe seed and generates another preview, reusing source engraving. Same-seed
  Generate replays. Threshold range affects fixed mode only; automatic methods
  retain their documented behavior. Save ranged recipes as schema v2 so older
  apps reject them, while keeping fixed v1 and reading both. README updated;
  source selection and existing root `scan-recipe.json` were preserved.
  Checks: all 47 app tests passed, including range validation, pixel/record replay,
  changed seed, reordering stability, integer endpoints and both rotation signs,
  global RNG preservation, requested/resolved manifest ZIP contents and bilevel
  export, UI checkbox/bounds interaction, v2 save/load and New sample wiring.
  Native Cocoa desktop ran horn-page rotation [−3,3] + fixed threshold [140,180]:
  seed 42 sampled −1.8483006425°/140; New sample seed 43 sampled −1.4253223358°/174;
  another seed-43 Generate exactly matched all image/MusicXML hashes. Preview ZIP,
  v2 recipe export and clean warm-worker shutdown passed. Artifacts:
  `/private/tmp/musvit-range-desktop-20261108/`. Screenshot QA also revealed that
  live Retina captures must use the actual window raster, not the initial logical
  size; updated the screenshot helper accordingly. Visually inspected controls at
  actual 3024x1678 native size, and headless screenshot/compilation/whitespace
  checks passed. No scanner calibration, batch dataset export or training added;
  these remain exploratory ranges. Web backend accepts ranges, but its frontend
  range controls were not added. Exact next action: restart desktop, set rotation
  Range −3…3 and a fixed threshold interval, then use New sample to compare
  realizations while checking notation legibility at model resolution.

- **2026-11-08 — Editable current values with Range enabled:** user requested
  keeping the slider editable when Range is selected and showing the value used
  in the current preview. Sliders now remain enabled, constrained to their range
  endpoints, and synchronize without callbacks to actual resolved values when
  a current-settings preview finishes. More recent mid-render edits are retained.
  Editing a ranged slider sets separate per-step/property preview_values for
  Generate; sampling bounds stay unchanged. Backend validates those choices
  against active numeric ranges, applies them after seeded sampling, and records
  preview_overrides alongside requested ranges/resolved/backend parameters.
  Preview request/settings preserve exact overrides for replay; recipe JSON does
  not pin the distribution to a preview choice. New sample clears overrides
  before advancing seed; preset/recipe replacement clears stale choices.
  Disabling Range keeps the shown value as the fixed value. Bounds edits clamp
  current values and any manual override. README updated; existing recipe files,
  source images, immutable previews and exports preserved.
  Checks: all 49 app tests passed. New backend test verifies exact manual
  rotation/threshold pixels equal fixed-value execution, unchanged ranges and
  rejection of unknown/out-of-range/noninteger/nonfinite overrides; ZIP test
  checks override serialization. New UI test verifies sampled slider sync,
  editability, exact request values, preserved stale edits and New sample reset.
  Native Cocoa full-page check confirmed actual slider dragging with Range on,
  seed-42 synchronization (−1.8483006425°, threshold 140), exact edited preview
  (1.5°, threshold 170), unchanged ranges [−3,3]/[140,180], and resumed seed-43
  sampling (−1.4253223358°, threshold 174). Exported manual-preview ZIP and clean
  shutdown passed; screenshot visually inspected. Artifacts:
  `/private/tmp/musvit-edit-ranged-preview-20261108/`. Python compilation and diff
  whitespace passed. Preview edits still require Generate; no automatic render
  on every slider movement or training/dataset change added. Exact next action:
  restart desktop, generate a ranged preview, edit its value slider and Generate;
  use New sample to return to random choices within the saved bounds.

- **2026-11-08 — Existing recipe saves retain range selections:** user reported
  Range selections lost after save/reload. Inspection found serialization/load
  already retain active ranges, but Save used the export-only exclusive-create
  writer, rejecting an existing filename and leaving its older settings on disk.
  Existing root `scan-recipe.json` was still v1 without ranges; it was read only
  during diagnosis and left unchanged. Added a recipe-specific atomic writer:
  save prior bytes exclusively under sibling `.recipe-backups/`, write/fsync a
  same-directory temporary file, atomically replace the chosen recipe, and remove
  staging files on failure. Identical content avoids unnecessary backups. ZIP
  exports retain the existing refusal to overwrite. Save/Open remember the last
  loaded/saved path, prefill its directory/name and report the actual path.
  Backup history is ignored by Git. README updated; no existing user file was
  migrated or overwritten by the agent.
  Checks: all 11 desktop tests passed. New regression starts with fixed v1,
  enables rotation/threshold ranges through UI, saves over that file, verifies
  v2 ranges and exact old-byte backup, reloads and checks both Range checkboxes
  and endpoints. Simulated atomic-replace failure preserves original bytes and
  leaves no staging files. Existing async snapshot test now verifies successful
  backed-up updates rather than expected overwrite rejection. Native Cocoa
  dialog round trip confirmed updating an existing temporary file, backup,
  reopening enabled rotation [−2.5,2.5] and threshold [130,185], and clean exit.
  Artifact directory:
  `/private/var/folders/c4/krtyyfns7mbgvrd43qzdkb8r0000gn/T/musvit-range-save-yrqj6lrf/`.
  Python compilation and diff whitespace checked. Full backend suite not repeated
  for this save-path-only fix; previous backend results remain recorded above.
  Exact next action: restart desktop, enable desired ranges and Save to the
  existing recipe filename, then Open it and confirm the restored bounds.

- **2026-11-08 — Entire lab projects and multi-level comparisons:** user changed
  the save unit from separate recipes to the full project, with several degradation
  levels, side-by-side Compare and saved previews/curriculum choices. Added
  `lab_project.py` project schema/ZIP asset writer/validated restore and seven
  project integration tests. Main UI now has Save project/Open project (Ctrl+S
  saves project), independent level selection/name/seed/recipe/ranges/manual
  choices, Add/Duplicate/Remove/Move left/right, and editable Clean/Mild/Moderate/
  Heavy starter levels (not measured severity classes). Compare uses resizable
  source + all-level viewports and Generate all levels, submitting sequential
  requests to the existing warm worker with shared source-cache reuse. Selected
  generation/export stays separate; switching editor level during a request
  preserves result ownership. Source/settings changes mark old comparison columns;
  per-job failures retain older previews while successful jobs continue.
  `.musvitlab` contains project.json, exact native/model source/augmented PNGs,
  manifests/hashes and synthetic MusicXML for all displayed level previews, plus
  the currently selected real scan page when applicable. It stores active level,
  stage/example/font/music seed/document/page, all recipes/seeds/manual preview
  overrides and pending edits, view mode/zoom/pan/linking/region widths/theme and
  sidebar/effect collapse state. Reopening displays saved previews without render
  and restores controls; copied scan pages remain project-local source assets,
  without importing/approving annotation history. Validates archive sizes/schema,
  entry whitelist, checksums and image data before restoration. Existing matching
  immutable artifacts are reused; conflicts get a new preview ID, preserving local
  files. Atomic file updates retain `.project-backups/`; bundles/backups are Git
  ignored. JSON v1/v2 recipe imports remain supported for the selected level.
  README updated; existing user `scan-recipe.json`/exports were not migrated.
  Checks: all 57 app tests passed in 14.411s. Project tests cover full state and
  exact asset hashes after loading into an empty data folder, stale displayed
  preview versus pending slider overrides, independent levels/duplicate/order,
  portable real scan/no annotation DB, corrupt/unexpected archive rejection,
  conflicting preview IDs without replacement, dialog-open snapshots/backup
  updates, and changing selected level while rendering. Existing app/worker/
  range/native-failure server tests remain passing. Native Cocoa integration
  generated all four Petaluma horn-page levels from music seed 19 with identical
  source image hashes, saved via the project dialog, changed editor/source state,
  reopened via the project dialog, and checked exact project-document equality,
  restored five comparison viewports, manual rotation 1.25°, range controls and
  current layout. Warm worker closed cleanly. Artifacts:
  `/private/var/folders/c4/krtyyfns7mbgvrd43qzdkb8r0000gn/T/musvit-whole-project-mn3bgzyy/`.
  Compare/restored screenshots were generated and restored layout visually
  inspected. Python compilation and diff whitespace passed. Limits: eight levels,
  512 MiB uncompressed bundle; only selected scan page/preview assets are portable,
  not the whole scan collection or annotation database. Names/preset severity are
  editable proposals, not calibrated training distributions. No batch training
  dataset or model/training change added. Exact next action: restart desktop,
  configure levels and common curriculum source, Generate all levels in Compare,
  then Save project; import older recipe JSON into a selected level as needed.


- **2026-11-08 — Desktop workbench concern separation:** user requested a
  maintainability refactor of the growing desktop entry point. Extracted initial
  BUI construction/bindings into `desktop_layout.py`, callback-based reusable
  widgets into `desktop_widgets.py`, job submission/batch/progress polling into
  `desktop_preview.py`, project/legacy-recipe snapshots and actions into
  `desktop_projects.py`, and read-only collection access/atomic backed-up writes
  into BUI-independent `desktop_storage.py`. `CurriculumDesktop` retains shared
  session state, level/source/recipe/view coordination, dialog ownership and
  worker/executor shutdown. Explicit delegating methods preserve existing caller
  and callback APIs; collaborators receive the host explicitly, with type-only
  host imports to avoid runtime cycles. Existing storage helper imports remain
  available through the entry module. Updated the atomic-failure test patch to
  target the storage implementation. Added the README module/ownership/threading
  guide and documented native image/dialog invariants. Main file reduced from
  1,300 to about 660 lines. No file formats, default recipes, datasets, scans,
  annotation databases, weights or existing user project files were changed.
  Checks: baseline 57 tests passed in 14.647s; after fixing a missed Separator
  import during extraction, all 57 app tests passed in 14.360s. Existing tests
  cover real input/layout interactions, project/asset restoration, manual ranges,
  stale results, save snapshots/backups and worker/server failure handling.
  Separate headless comparison rendered each of Curriculum, Scan Recipe, Compare
  and Manifest from the Git baseline and refactored code: all initial workspace
  images were pixel-identical. Temporary comparison outputs were cleaned up.
  Compilation and whitespace checks passed. Limits: native Cocoa event-loop
  interaction was not repeated; collaborators intentionally share the existing
  coordinator state rather than introducing a new application-state model.
  Exact next action: restart the desktop and continue workbench development in
  the responsible module listed in README's Desktop code navigation section.


- **2026-11-08 — File menu and current-project Save hotkeys:** user requested
  menu-bar file actions and Command+S overwriting the current project. Added a
  BUI header File menu with Open project, Save project, Save project as, Import
  recipe, Export recipe and Export preview ZIP. Menu entries, window hotkeys and
  toolbar Save share coordinator callbacks. `ProjectActions.save_project` bundles
  current state and writes directly to the saved/opened project path; untitled
  projects use the existing non-blocking browser. Shared write helper preserves
  atomic updates/backups and changes the current path only after success. Save As
  retains dialog-open snapshots and always requests a filename. Bindings: Cmd/Ctrl
  S for Save, Shift+S for Save As, O for Open, Shift+E for preview ZIP export;
  existing Cmd/Ctrl+Enter generates the selected preview. Inspection of the local
  BUI Cocoa source confirmed Command and Control map to the same kit CTRL bit.
  README documents menu actions and platform hotkeys. Existing refactor work was
  preserved; no user project files or data were overwritten during development.
  Checks: all 60 app tests passed in 14.425s. Added actual BUI shortcut-event tests
  for first save, repeated in-place overwrite/exact backup, Save As path switching,
  Open then Save, plus failed atomic replacement retaining original bytes/path.
  Actual header menu clicks verify Open, Save As, recipe import/export and preview
  export's missing-preview handling. Headless CLI screenshot rendered successfully
  and was visually inspected at `/private/tmp/musvit-file-menu-20261108.png`.
  Compilation and whitespace checks passed. Limits: menu is the BUI workbench
  header, not a new macOS system-menu bridge; native Cocoa event-loop key delivery
  was not exercised in this session. Exact next action: restart the workbench,
  open or save a project once, then use Command+S to update that project directly;
  use Command+Shift+S when a different filename is wanted.


- **2026-11-08 — Progress aligned to footer right:** user requested moving the
  full-width bottom progress bar into the right side of the application footer.
  Changed only initial layout: status and progress share a Row with 70/30 width
  weights and 12px spacing. Existing progress visibility, text and job callbacks
  are retained. All 11 desktop tests passed in 0.853s. Executed headless geometry
  checks with visible progress at 1520×960 and minimum 1060×760: status/progress
  share a y-coordinate, progress follows status without overlap, occupies less
  than 35% of window width and remains within the window. Screenshot visually
  inspected: `/private/tmp/musvit-footer-progress-20261108.png`. Whitespace check
  passed. No native event-loop check or backend test rerun for this layout-only
  change. Exact next action: restart desktop and generate a preview to see
  progress at the footer's right edge.


- **2026-11-08 — Reference-focused Curriculum and full stage management:** user
  requested removing the degradation sidebar from Curriculum, showing only the
  reference, and adding stage customization. Clarification selected full stage
  add/remove/reorder support. Curriculum now shows source/stage controls and one
  reference viewport, hiding the augmented pane/divider and Link views toggle.
  Scan Recipe retains paired images and degradation controls, Compare retains
  all levels. Workspace changes preserve existing region weights/preview state.
  Added `desktop_curriculum.py` for Add/Duplicate/Remove/Move up/down, editable
  unique name/description/focus/mix notes, Reset stage details and source-type
  selection. Added BUI-independent `curriculum_plan.py` for defaults/validation
  (1–32 stages, bounded text, unique stable IDs/names, supported generator types).
  Custom stage IDs remain distinct from the existing five backend source IDs,
  so renaming, cloning or reordering does not misroute generation. Duplicates have
  independent details; deleting the final stage is blocked. Source types choose
  among the existing generators or Real scans; no new musical generator coverage
  or training sampler was introduced. Stage mix remains editable planning text.
  Complete plan/order and selected stage persist in `.musvitlab` schema v2. Old
  v1 projects receive default stages on load; old app versions reject new v2 files
  instead of silently dropping custom plans. Existing recipe JSON remains v1/v2.
  Updated workspace input/layout tests to exercise paired controls in Scan Recipe,
  and documented the new workflow/modules. Restored a missing sqlite3 import in
  the coordinator's collection-error handling found during inspection.
  Checks: all 63 app tests passed in 14.592s after schema-version changes. New
  coverage checks independent stage edits, clone/order/reset/source mapping,
  generation using the backend stage ID, exact custom-plan project round trip,
  old-project defaults, invalid names/types/selection and 1–32-stage boundaries.
  Additional legacy archive Open/upgrade and required-v2-plan checks passed in
  the targeted project suite. Headless geometry with a displayed fixture reference
  passed at 1520×960 and 1060×760: single viewport occupies over 60% of window
  width and hidden degradation/image dividers stay hidden. Screenshot visually
  inspected at `/private/tmp/musvit-curriculum-stages-20261108.png`. Compilation
  and whitespace checks passed. Native Cocoa event-loop interaction and actual
  musical engraving were not repeated for this UI/project change; source-image
  test uses a mocked generator. No datasets, scans, annotations, existing project
  files, weights or training exports were overwritten. Exact next action:
  restart the desktop, customize/add/reorder stages in Curriculum, choose each
  supported source type, inspect the reference and Save project to retain it.


- **2026-11-13 — Transcoda paper review and target recommendation:** read the
  supplied `trasncoda_paper.pdf` (arXiv:2605.10835v1), inspected the rendered
  normalization/augmentation and ablation pages, and compared the local MuSViT
  paper A.9.1, codec contract, historical target-format audit and curriculum design.
  Also read the public Transcoda repository landing page and Humdrum kern
  specification; no upstream code executed or model evaluated. Paper Table 3:
  synthetic greedy OMR-NED 18.71 versus 82.51 without normalization; real-scan
  greedy baseline 65.76 versus 80.10 without concatenation, 76.95 without raster
  degradation and 78.99 without asymmetric augmentation. These are authors'
  reported results, not local experiments. Normalization is a bundled intervention,
  including removing non-target notation; it does not isolate a kern-versus-our-
  codec benefit. Suggested retaining MusicXML as canonical source/export and
  evaluating normalized Humdrum for model targets with required notation/text
  preservation, rather than restoring the historically lossy bekern cleaner.
  Further takeaways: match page density/target length as well as scan appearance;
  vary engraving geometry/fonts; avoid treating intended performance markings as
  distractors; keep validity distinct from recognition accuracy; evaluate in a
  common musical metric. Grammar cannot prevent valid hallucinations/voice drift.
  Cautions: historical scans remain at 63.97 beam OMR-NED; no demonstrated
  handwritten-notation result; Polish references occur in the synthetic validation
  description, so this is not proof of untouched-domain evaluation; visual
  pretraining comparison changes encoder size too, and its table/prose differ.
  Existing compact-target local failure remains evidence against assuming that
  shortening alone fixes training. No files containing datasets, scans, labels,
  weights or user projects changed, and no training/conversion experiment ran.
  Exact proposed next action: audit existing horn/piano/cross-staff/drum/navigation/
  text fixtures through the candidate conversion/normalization path, recording
  loss, target length and MusicXML round-trip fidelity before a replacement decision.


- **2026-11-13 — MusicXML normalization policy and differential audit:** user
  asked to write the policy and check equivalence/preservation after selecting
  MusicXML; clarified that existing early datasets/checkpoints do not matter.
  Recorded policy in `experiments/full_page_omr/docs/NORMALIZATION_POLICY.md` and
  linked it from codec, curriculum and workspace guides. Concrete rules are
  recommended implementation details, not claims of completed codec behavior.
  Proposed omissions name editor metadata, absolute layout coordinates/automatic
  breaks, playback-only settings and classified unprinted analysis; readable
  notation remains preserved. Source MusicXML stays intact. No migration layer
  or separate compatibility-preservation project is required.
  Added `diagnostics/normalization_audit.py`: original programmatic paired scores,
  no renderer, downloads or artifact writes. Executed 15 pairs: 2 equivalences
  satisfied, 6 equivalences remain distinct, all 7 required musical differences
  remain distinct. The six gaps are redundant later divisions declarations,
  chord order, independent voice serialization, absent/zero alteration, default
  note visibility and equivalent cursor-relative direction locations. Every
  stream passed encode/decode round trip and normalization idempotence; no probe
  errors. Audit exits 1 explicitly because policy gaps remain, not a passing
  implementation acceptance test. Executed codec/constrained-decoding unittest
  suites: 23 tests passed in 5.837s. No renderer/score-editor comparison or model
  experiment executed. Production codec and all existing datasets, annotations,
  weights and desktop work preserved. Exact next action: implement timing/default/
  declaration canonicalization directly, followed by relationship-aware ordering;
  expand hard-case probes and re-render fixtures before the next training export.


- **2026-11-14 — MusicXML beside the Curriculum reference:** user requested
  inspecting MusicXML next to the rendered image on the Curriculum tab. Added a
  dedicated resizable reference/XML split, visible only in Curriculum. Existing
  source/augmented split and project image-weight serialization remain intact.
  Added `SourceText` in `desktop_widgets.py`: BUI 0.4.1 only supplies single-line
  editable fields, so the read-only inspector draws visible monospaced lines and
  a number gutter through the existing synchronous image-buffer path. Wheel
  scrolls lines; Shift+wheel scrolls horizontally; Top resets both axes. Original
  UTF-8 XML is held unchanged, with no parsing, rewriting or source edits.
  Coordinator loads `source.musicxml` when displayed preview identity changes,
  shows unavailable/no-source/no-preview messages, and keeps XML synchronized
  with displayed images across workspace switches and pending control edits.
  Project restore uses existing bundled XML assets without a schema change.
  Added two integration tests covering stale-control ownership, Unicode/exact
  source retention, saved-project reload, empty states, workspace visibility,
  normal/minimum layout, actual BUI scroll and Top-button events, and image-pan
  independence. First scroll test exposed floating-point wheel deltas entering
  line indices; corrected integer clamping. Final full Bar Review suite: 65 tests
  passed in 16.019s. Generated an actual clean one-note source/engraving in a
  temporary directory and inspected headless screenshot
  `/private/tmp/musvit-curriculum-xml-20261114.png`. Whitespace checks passed.
  Native Cocoa window interaction was not repeated. Inspector is not an editor
  or normalizer; new divider/scroll state is session-only. Existing uncommitted
  desktop/normalization work preserved; datasets, scans, annotations, user project
  files and weights unchanged. Exact next action: restart the desktop, generate
  or reopen a synthetic Curriculum preview, then inspect XML beside its image.


- **2026-11-14 — Reference-scoped controls and drag performance:** user requested
  moving zoom controls from the shared image/XML parent into the reference pane
  and improving mouse-drag panning. Moved resolution/zoom/Fit controls and image
  help into Source / Reference; shared controls reparent to the Compare toolbar
  only when that workspace opens. Source and XML widths remain independently
  resizable. Profiling a 75%-zoom drag showed repeated bicubic affine sampling
  dominating the callback: 0.413s of a 0.491s 60-step trace. Added one reduced-page
  cache per viewport/source/scale below 100%, with fast nearest-neighbour viewport
  extraction; native/magnified views keep direct sampling to bound memory. Added
  an identical-frame guard and a dedicated center-only visible-image redraw path,
  avoiding preview/recipe labels, XML and hidden augmented-pane work during pan.
  Quick second clicks (BUI double-click events) now start dragging too; otherwise
  rapid repeated drags could be ignored. Cache drops when the viewport clears or
  returns to >=100% zoom and rebuilds for changed source/scale.
  Added integration checks for control containment at 1520×960 and 1060×760,
  repeated workspace reparenting without duplicate controls, actual drag events,
  absence of XML/hidden/full-preview redraws, nearest-only transforms after warmup,
  and cache reuse/invalidation. Full app suite: 67 tests passed in 15.485s.
  Headless benchmark `/private/tmp/musvit-pan-benchmark.py` uses the programmatic
  1400×1981 test image and 250-line source, 75% zoom, 60 warmup steps plus 180
  measured mouse-motion/render frames. Baseline median/p95 8.4106/8.8029ms;
  final 0.5768/0.6416ms. Final profiled 60-step trace 0.036s. An intermediate
  artificially low median exposed repeated presses becoming double-click events;
  it was discarded, corrected and rerun. Layout/image area also changes between
  baseline/final, so timings are local end-to-end evidence, not a matched cache
  ablation or native Cocoa latency result. Generated an actual one-note render
  and inspected `/private/tmp/musvit-reference-controls-20261114.png`; inspected
  minimum-size fixture screenshot at `...-small-20261114.png`. An initial small
  screenshot attempt used a nonexistent Raster.save API; corrected to PPM/Pillow.
  Whitespace checks passed. Native window drag smoothness not measured; the first
  new-source/zoom frame still pays downsampling cost. Existing datasets, scans,
  weights, user projects and other uncommitted work preserved. Exact next action:
  restart desktop and test dragging a zoomed reference in the native window.


- **2026-11-14 — Reconsidering a kern-based project scope (discussion):** user
  is leaning toward revising goals around what **kern can express, motivated by
  its use across the referenced papers. This reopens the earlier MusicXML target
  choice; no replacement or removal of collection requirements was yet agreed.
  Read current coverage/historical format audit and official Humdrum kern and
  Verovio Humdrum Viewer documentation. Core kern covers pitch/rhythm/chords,
  polyphonic spines and many notation marks; broader Humdrum conventions add
  text/dynamics. Distinguish core kern, renderer-supported Humdrum and each paper's
  normalized/cleaned target subset. Historical losses in our old bekern cleaner
  were implementation findings, not general format incapacity. Recommendation:
  pause expanding the MusicXML model target, define a concrete normalized Humdrum
  recognition scope around supported conversion/render/export fixtures, and keep
  MusicXML as source/editor interchange. Unusual percussion, jazz shorthand,
  arbitrary scoped instructions and historical alternative layouts need explicit
  tests or agreed deferral, not assumptions of unsupported syntax. Cross-paper
  format use is an engineering advantage, not an isolated learning-performance
  comparison. No code, exports or training changed; no conversion was executed.
  Exact proposed next action: produce a representative feature coverage sheet
  using the candidate converter/normalizer/renderer/editor-export path, marking
  demonstrated support, missing implementation and proposed deferrals before
  selecting the first kern-based training scope.


- **2026-11-14 — Approved Humdrum scope and initial conversion audit:** user
  accepted the proposed direction and answered all three scope questions: include
  common dynamics/performance text immediately; cover percussion plus pitched
  parts and piano; transcribe supported content and flag omissions for review.
  Created `docs/HUMDRUM_SCOPE.md` with agreed scope, candidate standard conventions,
  normalization/omission requirements, acceptance gaps and exact next action.
  No 32nd-note cap was agreed. Omission detection on real scans is not solved;
  report known source-backed losses and require review rather than promise all
  unsupported symbols will be located automatically. MusicXML remains source and
  editor interchange; the implemented v1 codec is retained pilot infrastructure.
  Read primary Humdrum/VHV documentation for dynamics, text layout directions,
  transposition and percussion; distinguished lyric **text from performance
  `!LO:TX:` records. Inspected local dependencies: Verovio 5.0.0 installed;
  music21/converter21 absent and conversion command names absent from PATH.
  Added `diagnostics/humdrum_scope_audit.py` with isolated 15-second native probes,
  disabled core dumps, summary-only stdout and no artifact writes. Executed
  MusicXML-hum conversion -> buffer -> Humdrum reimport -> MEI on horn/piano/drums:
  all three processes return zero and both conversion/reimport succeed. Horn
  370 bytes/one initial kern spine; piano 287/two; drums 308/one. Basic event
  counts match these fixtures, but no pitch/onset/staff/voice fidelity audit ran.
  Horn's two complete instruction strings not found in returned MEI despite two
  Humdrum text-layout comments; no returned gliss element for its two endpoints.
  Piano returns no pedal elements for its two source pedal markers. Drums return
  both instruction strings. These are converter/reimport observations, not
  inherent format limitations. The historical native aborts did not recur on
  these probes; no patch/upgrade was made. Script success means smoke execution,
  not representation acceptance. No SVG/PNG/editor round trip, target training,
  dataset export or model experiment executed. Preserved other uncommitted work.
  Exact next action: build minimal text/escaping, pedal and glissando fixtures,
  investigate their loss and select/repair a converter plus editor-export route
  before declaring Humdrum feature support and freezing a tokenizer.


- **2026-11-14 — Pedal conversion isolated:** user correctly pointed out kern's
  `*ped` syntax. Verified primary VHV pedal documentation: `*ped` means pedal down,
  `*Xped` pedal up. Ran an isolated native subprocess (15-second bound, core dumps
  disabled) with local Verovio 5.0.0: a minimal direct Humdrum example loads and
  yields two MEI pedal elements with down/up directions. The MusicXML-converted
  piano fixture has no pedal-related tokens. Therefore the observed loss is in
  this MusicXML-to-Humdrum conversion path, not lack of format expressiveness or
  basic Humdrum import support. Updated scope report; no converter code changed.
  Pedal-line/change/half-pedal, attachment and editor export remain untested.
  Exact next action: repair/select the source conversion path to emit the existing
  pedal syntax, preserving staff/onset, and add a regression fixture.


- **2026-11-14 — Direct canonical Humdrum generation and source viewer:** user
  approved removing MusicXML from the core pipeline and displaying kern instead
  of XML. Added `generation/humdrum_scores.py`: direct seeded sources for all
  eight Curriculum examples, fixed generated spelling/order, direct Verovio
  input, derived SVG/MEI, outlined text and native raster generation. New sources
  are newly authored examples, not translations of older MusicXML compositions;
  updated source fingerprints prevent reuse of obsolete engravings. Native
  source profile is `musvit-humdrum-preview-v1`. Piano includes native pedal
  down/up, chords, split/merge voices and dynamics. Drums include unpitched
  marks, x noteheads, rhythmic voices and scoped instructions. Cross-staff RDF
  explicitly moves two notes above. Rendering checks expected event/measure/
  staff/pedal counts, instruction text and cross-staff assignment presence.
  These safeguards do not establish arbitrary-score equivalence or coverage.
  Text-before-split experiments exposed lost attachment; comments now immediately
  precede target notes after structural interpretations. MEI full rests use
  mRest rather than rest and are counted appropriately.
  Simplified `curriculum.synthetic`, warm-worker preload and source fingerprints
  to remove the MusicXML generators, pilot exporter and tree-codec dependencies.
  Preview artifacts now contain source.krn plus derived source.svg/source.mei;
  checksum-verified reuse validates/copies all derived files. Artifact allowlists
  and portable projects accept them; old XML-only saved assets remain readable,
  but the viewer requests regeneration instead of silently converting them.
  Source pane is now **kern / HUMDRUM with readable tab stops and existing
  scrolling/Top/ownership behavior. Web lab exposes the same exact source.
  Initial replay tests exposed random Verovio IDs, unordered glyph definitions,
  differing formatting tails and ID-bearing milestone classes. Stabilized those
  derived XML structures/references and omitted renderer application isodate;
  source Humdrum strings are unchanged. Repeated font/process replay now passes.
  Added three focused tests, including isolated native integration rendering all
  eight examples, actual percussion x-head/two cross-staff-note checks, all three
  fonts, exact source/hash identity, deterministic replay, reuse, ZIP and fresh-
  directory project restoration. An import guard rejects legacy MusicXML dataset/
  codec imports in the native path. Full Bar Review suite: 70 passed in 15.500s.
  JS syntax and diff whitespace passed. Generated and visually inspected actual
  desktop piano/drum screenshots at `/private/tmp/musvit-kern-piano-20261114.png`
  and `...-drums-20261114.png`; cross-staff screenshot also generated. Native
  Cocoa mouse interaction and web browser interaction were not repeated.
  Added pipeline guide and updated scope/workspace/app/diary docs. No historical
  datasets, scans, annotations, weights or user project files overwritten; prior
  uncommitted work preserved. Current native generation has no hairpin/full jazz/
  navigation/imported-score normalization contract, and the Humdrum training
  tokenizer/adapter is not implemented. Old MusicXML trainers remain historical
  tools, not the new target path. Exact next action: restart/regenerate in the
  lab; extend feature fixtures and implement a deterministic Humdrum tokenizer/
  bounded training adapter before producing fresh training datasets.
