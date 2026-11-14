# Bar Review

A local prototype for transcribing individual instrumental parts one passage
at a time. Scans are segmented into proposed staff/bar regions, queued in
reading order, and shown alongside a Smoosic notation editor and staff context.
There is no note-recognition model connected yet: initial rests are entry
scaffolding, not predictions.

## Run

From the repository root:

```bash
npm ci --prefix apps/bar_review
uv run python apps/bar_review/server.py
```

Open <http://127.0.0.1:8765/>. The server binds to loopback only. Use `--port`
to change the port and `--data-dir` to choose another annotation directory.
The Python environment uses the repository's existing Pillow, NumPy and OpenCV
dependencies; it does not load the training model. PDF import requires Poppler
(`brew install poppler` on macOS).

Use `--scan-dir /path/to/scans` to prefill the import dialog's folder.

For SSH access, start the server on the remote machine, then forward its port
from your own computer (replace `user@remote-host`):

```bash
ssh -N -L 9000:127.0.0.1:8765 user@remote-host
```

Open <http://localhost:9000/curriculum.html> on your computer. The local port
may differ from the server port. Use `localhost`, `127.0.0.1`, or `[::1]` in
the browser URL; remote hostnames and LAN addresses are not accepted. The
server still binds only to loopback and rejects cross-origin POST requests.
Restart the Python server after updating its code.

## Workflow

### Desktop Curriculum Lab (BUI)

The desktop lab uses [BUI](https://github.com/ppmpreetham/BUI)'s Python Blender
components. It runs directly against the existing Python curriculum backend;
no HTTP server, browser, notation-editor dependencies or Blender installation
is needed.

```bash
uv sync --extra desktop
.venv/bin/python apps/bar_review/desktop.py
```

On macOS, double-click `launch_curriculum.command` in this folder after installing
the extra. The launcher uses the checkout's `.venv`, supplies the Homebrew Cairo
library path when available and puts Matplotlib's cache in the temporary directory.
The Python entry point also detects the documented Homebrew Cairo path for preview
workers. Other platforms need the same Verovio/Cairo setup as the web lab.

The top workspace bar follows Blender's layout:

- **Curriculum:** editable curriculum stages and source properties, with the
  reference image beside its read-only **kern / Humdrum source.
- **Scan Recipe:** paired viewer and more room for effect properties.
- **Compare:** the source and every degradation level side by side.
- **Manifest:** provenance and parameters of the selected level's preview.

The Curriculum workspace has **Add**, **Duplicate**, **Remove**, **Move up** and
**Move down** stage controls (1–32 stages). Each stage has an editable name,
description, learning focus and mix notes. **Source type** maps it to an existing
generator family—Recognition check, Short passages, Systems & pages, Notation &
voices—or Real scans. The Source panel selects a supported example/font/music
seed or imported page. Stage IDs remain stable when renamed/reordered, and
duplicated stages have independent details. **Reset stage details** restores the
selected source type's suggested text. Names must be nonblank and unique.

Stage order, details, source types and selected stage are saved with the project.
Mix notes describe the curriculum plan; they do not configure a training sampler
or launch training. The generators' musical coverage remains unchanged. The
degradation sidebar and augmented image are available in **Scan Recipe**; all
levels remain available in **Compare**.

In **Curriculum**, the reference and **kern / Humdrum** panes share a draggable divider.
The source pane shows the exact `source.krn` belonging to the displayed
preview, with monospaced text and line numbers. Scroll for more lines,
Shift+scroll sideways for long lines, and use **Top** to reset the view. Pending
source-control edits keep the old image and matching XML visible until Generate
finishes. Saved project previews restore their embedded XML automatically.
Imported scan previews have no score source and show an empty-state message.
New synthetic previews are generated directly in Humdrum and rendered through
Verovio; MusicXML and the old model codec are absent from this path. ZIP/project
exports retain `source.krn`, derived `source.svg` and `source.mei`. Earlier
MusicXML-only previews need regeneration to show Humdrum. See the
[direct-source pipeline](../../experiments/full_page_omr/docs/HUMDRUM_PIPELINE.md).
The web lab also exposes the displayed source in a read-only section.

This pane is for inspection; it does not edit or normalize the source. Its divider
and scroll position are session-only and are not added to the project format.

Resolution and zoom controls live inside **Source / Reference**, above the image,
so they do not span the Humdrum pane. Compare retains shared controls above its
image columns. Panning reuses a reduced image at zoom levels below 100%, redraws
only visible image panes and skips preview/manifest/XML refreshes. At 100–400%
the viewport is sampled directly without allocating a magnified full-page cache.

The lab is a **project**, starting with editable Clean, Mild, Moderate and Heavy
levels. Select a level in the recipe sidebar to edit its independent recipe, seed,
ranges and manual preview choices. Add, duplicate, rename, remove or reorder levels
(up to eight). Initial recipes are exploratory starters, not calibrated severity
boundaries or approved curriculum mixes. All levels share the selected curriculum
source so their appearances can be compared fairly.

In **Compare**, **Generate all levels** renders the selected source through each
level on the warm worker, reusing its engraving. Columns have resizable widths and
the existing linked zoom/pan controls. **Generate selected level** updates only the
current editor selection. Missing previews show a placeholder; changed source,
recipe or seed settings mark older columns as **settings changed** until regenerated.
A batch failure retains previous previews and reports the error; successful
levels still finish. Changing editor selection while rendering does not attach
the result to the wrong level.

The workbench's **File** menu provides Open project, Save project, Save project
as, legacy recipe import/export and displayed preview ZIP export. The toolbar's
Save project button performs the same action as File → Save project.

| Action | macOS | Windows/Linux |
| --- | --- | --- |
| Save current project | Command+S | Ctrl+S |
| Save project as… | Command+Shift+S | Ctrl+Shift+S |
| Open project… | Command+O | Ctrl+O |
| Export displayed preview ZIP… | Command+Shift+E | Ctrl+Shift+E |
| Generate selected preview | Command+Enter | Ctrl+Enter |

**Save project** updates the current saved/opened `.musvitlab` directly, keeping
the previous version in `.project-backups/`. For an untitled project it opens the
save browser. **Save project as…** always opens that browser; after a successful
save the chosen file becomes the current project. Cancelling leaves the current
path unchanged.

Each `.musvitlab` file contains:

- Every level's name, order, recipe/effect IDs, enabled steps, numeric ranges,
  seed, manual preview choices, selected starting recipe and collapsed panels.
- Selected curriculum stage/example, font, music seed and imported scan/page.
- Complete customized curriculum stage list, order, details and source types.
- Each level's exact most recent preview: source/augmented PNGs, native/model
  inputs, manifest/hashes and synthetic Humdrum with derived SVG/MEI when available.
- Active level/workspace, resolution, zoom, linked state, pan centers, region
  proportions and theme.

**Open project** restores those previews immediately without rendering, including
in a different data folder. For Real scans, the selected source page is embedded
so generation can continue without the original import. Other pages and annotation
history are not bundled. Opening a project does not create or approve annotations.
Preview assets are verified before import. Identical local artifacts are reused;
conflicting immutable preview IDs are restored under new IDs. Projects have a
512 MiB uncompressed limit. The ZIP-based bundle is not a training dataset export.
Projects now save as schema v2; v1 projects open with the five default stages.
Older app versions reject v2 rather than silently discarding customized stages.

Project saves atomically update the chosen file and retain its prior version in
`.project-backups/`. Save/Open remember the current project folder/filename.
The file captures the workspace when Save is clicked, including older displayed
previews and pending edits; saving does not generate images. Opening a project is
blocked while rendering. Old v1/v2 recipe JSON can be opened through **Open project**
to import settings into the selected level, then saved as part of the full project.

Switching workspaces preserves the source, recipe and displayed preview. The five
initial stage templates, eight synthetic examples, three fonts and all 17 ordered
effects come from the shared catalog. Recipes support repeated effects, bypass, removal, Up/Down and
Blender panel-grip dragging; the executed order follows the visible order.

Drag the narrow borders beside either sidebar to adjust its width, or the border
between the source and augmented images to resize those viewports. The pointer
changes to a horizontal resize cursor and the border highlights on hover.
Neighboring areas resize together with minimum widths while dragging. Double-click
a sidebar border to restore the default sidebar layout; double-click the image
divider to restore equal image widths. Proportions remain in the current session
across workspace switches and scale with the window. Hidden sidebars also hide
their dividers. Viewports redraw automatically, preserving zoom and pan settings.

**Add Effect** opens a Blender-style popup with Paper & framing, Ink & printing,
Dirt & interference and Scan & geometry submenus. Choose an effect to append it
immediately, or start typing to search across all categories. Escape dismisses
the menu. The button disables at the 12-step limit.

Drag numeric properties or click to enter exact values. Preview ZIP exports remain
separate from projects: they export only the selected level's displayed preview
and refuse to overwrite an existing export.

Every numeric property has a **Range** checkbox. Enable it to show **Min / Max**
bounds beneath the editable value slider. Rotation
starts with −3° to +3°. Other properties start with both endpoints at the current
fixed value until edited. For example, choose Black & white scan → `fixed`, enable
Range beside Threshold, then set Min 140 and Max 180. Threshold ranges apply only
to fixed thresholding; Otsu chooses its threshold automatically and adaptive mode
uses the radius/offset properties. Moving a bound past its partner moves the
partner too, keeping a valid interval. Existing property limits still apply.

After a preview finishes, a ranged slider shows that preview's resolved value.
It stays editable within Min/Max: change it and click **Generate preview** to try
that exact value while retaining the range. Pending edits made during rendering
are preserved instead of being overwritten by the finishing preview. Disabling
Range keeps the currently shown value as a fixed setting. Bounds remain the saved
sampling distribution. Projects also retain manual preview choices; **New sample**
clears those choices for the selected level and samples again.
The preview manifest/request records manual choices as `preview_values` and
per-effect `preview_overrides`, so the displayed result remains reproducible.

Each active range samples uniformly for a preview: inclusive integer bounds for
integer properties, continuous values for fractional properties. The recipe seed,
step's stable ID and property name determine the sample independently of order
or other ranged properties. Generating with the same seed and manual choices
repeats the result.
**New sample** advances the recipe seed and generates another realization, reusing
the source engraving where possible. Original bounds and resolved values appear
in the exported manifest (`requested_ranges`, `sampled_parameters`); backend
parameters still record the values actually applied. Legacy ranged recipe JSON
uses version 2, fixed recipe JSON uses version 1, and both can be imported into
the current project's selected level.

Save, Open and Export use non-blocking Blender-style file browser windows.
Closing a browser window or choosing Cancel leaves the main app running; reopening
a file operation while a browser is already open brings that browser forward.
Save captures the project when its dialog opens, and Export captures the selected
preview at that moment, even if controls or a background preview change meanwhile.
Closing the main app also closes its file browser. This avoids BUI 0.4.1's nested
native macOS event-loop crash on file-dialog dismissal.

Choose **Native** or **Model 1024** for the image viewports. Each main image
zooms and pans directly; there is no separate detail section. Use **Fit** to see
the whole page, the percentage selector for 25–400%, or the **− / +** buttons.
At 100%, one image pixel occupies one UI raster pixel; magnification uses nearest
neighbor to expose actual pixels, while reductions use bicubic sampling.
Scroll vertically, Shift+scroll horizontally, drag to pan, or Ctrl+scroll to zoom.
Arrow keys also pan. **Link views** synchronizes relative centers; turn it off to
pan either image independently. Zoom applies to all displayed images. Resizing the window
or switching workspaces automatically redraws the viewports at their new size.
Fit mode centers the entire image and scrolling has no effect until it exceeds
the viewport. Geometry-changing effects do not produce registered views.

The desktop starts **one persistent preview process** in the background when its
window opens. It preloads engraving and Augraphy dependencies once, and its main
thread processes submitted jobs serially. The progress bar shows warmup and then
**Preview worker ready**. **Generate preview** (Ctrl+Enter) submits a job to that
warm process, with a 120-second per-job deadline. Controls stay responsive. Editing during rendering marks
the result as belonging to earlier settings. **Export preview ZIP** always
exports the displayed immutable preview, including its original request, images,
hashes and Humdrum/SVG/MEI where available. Full worker errors also print to the terminal.

The progress bar names the active phase/effect and shows elapsed wall time. It
advances at pipeline milestones, not an estimated percentage of execution time:
a slow effect can hold the bar while the clock continues. The manifest includes
source/augmentation/image-save timings and individual ordered-effect durations;
augmentation time includes dependency initialization, while worker time excludes
the initial worker warmup and final UI display. Native process crashes, lost
connections and timeouts retire the worker; the next preview automatically starts
a replacement. Invalid settings return an error while leaving the worker ready.
Closing the desktop stops both idle and active workers. Jobs are not automatically
replayed after a native crash.

The shared executor avoids unnecessary Augraphy imports for clean, rotation-only,
DPI-only and threshold-only recipes; the desktop's eager warmup deliberately loads
Augraphy once so later recipe changes need no additional dependency startup.
The desktop also remembers up to 64 synthetic
source selections per session and reuses an intact previous engraving when only
the recipe/augmentation seed changes. Source inputs, relevant code and dependency
versions must match, and PNG/Humdrum/derived artifact hashes are verified. A missing/corrupt source
falls back to fresh rendering. Every resulting preview still has a new immutable
folder. Real scans are loaded from their current page files. Detail panning reuses
decoded pages and supplies only visible in-memory pixels instead of writing/reopening PNGs.

Earlier **fresh-worker** measurements on this Mac with a Leipzig horn page, music seed 7 and recipe seed 42
(one unprofiled run per case; ordinary timing variation applies):

| Preview | Before | After |
| --- | --- | --- |
| Clean, fresh source | 2.07 s | 0.90 s |
| Clean, reused source | 2.07 s | 0.14 s |
| Light-copy, reused source | 2.19 s | 1.38 s |
| Bound-copy, reused source | 2.74 s | 2.12 s |

All image/MusicXML artifact hashes matched the baseline in those comparisons.
BadPhotoCopy itself took 0.04 s in the optimized light-copy run; most of its
remaining augmentation time was loading dependencies. The current desktop keeps
that process warm while retaining process-level crash containment. Repeated
two-bar light-copy previews across Leipzig, Bravura and Petaluma measured
0.27–0.39 s after one 2.39 s warmup, using the same process throughout. This is
a local check, not a timing guarantee; initial startup may be much slower on other
machines. Larger scans and different effects can take substantially longer.
Warm workers/progress/source reuse are desktop features; the web server retains
one process per preview. Conditional imports and timing manifests also benefit
web previews. Restart the desktop to load these changes.

`--data-dir /path/to/bar-review-data` shares the web app's imported scan collection
and preview folders. The desktop reads `annotations.sqlite3` read-only and never
initializes an absent database. Import scans with Bar Review, then **Refresh imported
scans** in the desktop's Real scans stage. The web server can be stopped while
using those scans in the desktop. A new preview gets its own unique directory;
existing exports, scans and annotations are preserved.

The tested package is `blenderui==0.4.1`. Native Cocoa windows are supported on this
Mac and were verified outside the execution sandbox. Earlier sandboxed probes
reported no native host and used BUI's Tk fallback; this was an environment
restriction, not a missing backend in the wheel. Blender components use BUI's
C kit in both hosts. GPU acceleration has not been verified in this app.
The viewer supplies Pillow-decoded RGBA pixels directly to BUI: the wheel's
asynchronous file-image wake caused a reproduced macOS/Tk native crash while
invoking a Python redraw callback. Direct pixels avoid that callback path;
unchanged full-page buffers are reused when moving the detail focus.
Windows/Linux hosting depends on BUI's available backend. This is a source-launched
desktop application, not a bundled/signed `.app` or installer.

For reproducible UI inspection without a desktop window:

```bash
.venv/bin/python apps/bar_review/desktop.py --screenshot /tmp/curriculum.png
.venv/bin/python apps/bar_review/desktop.py --workspace Compare --theme light
```

The screenshot option renders the initial UI only. BUI integration tests are
included in the check command below when the desktop extra is installed and skip
otherwise. They exercise workspace clicks, native panel dragging, image layout/hit
testing, shared read-only scans, request snapshots, failed-worker recovery, recipe
validation and immutable ZIP exports. The same exploratory/calibration limits
as the web lab apply. Persistent-worker checks additionally cover repeated
cross-font deterministic replay, equivalent one-shot output, same-process reuse,
fatal exit and timeout recovery, validation errors, startup deadlines and closing
an active job.

### Curriculum Lab

Choose **Curriculum Lab** in the sidebar, or open
<http://127.0.0.1:8765/curriculum.html>. The lab uses the same local server and
imported document collection; it does not require the notation editor to load.

- Explore five proposed stages: recognition, short passages, systems/pages,
  notation/voices, and real scans. Eight generated example types reuse the
  experiment generators. Stage descriptions and proposed appearance mixes follow
  [the curriculum design](../../experiments/full_page_omr/docs/CURRICULUM_DATASET.md).
- Change the music seed and engraving font. Focused piano/drum fixtures are fixed;
  seeds vary the one-note, passage and complete-page generators.
- Choose a **Starting recipe**, then **Load starting recipe**. This replaces the
  list with clean, light-copy, library-scan, or border/framing/bindings/copy steps.
  Use **Add effect** to compose your own recipe. Effects execute top to bottom;
  **↑ / ↓** changes order, the checkbox bypasses a step, and **×** removes it.
  Repeated effects are supported, up to 12 steps. **Clear effects** gives an
  unchanged source control. Generate again to apply any edits.
- Available steps: scanner edge, PageBorder, framing/padding,
  BindingsAndFasteners, BadPhotoCopy, InkBleed and antialiased rotation. Each has
  controls for relevant parameters: edge/width, padding/fill, binding type/count/
  inset, copy pattern/location/strength, ink spread or angle. Bindings use local
  generated punch holes, binding holes, clips or triangle clips; no downloads.
- **Scan resolution (DPI)** simulates lower-resolution capture through pixel-area
  downsampling. Set target DPI (36–600) and assumed current canvas width in mm
  (210 for A4 width, 215.9 for US Letter). This includes any margins already
  added by earlier steps. `scan_pixels` retains the smaller pixel dimensions;
  `restore_size` enlarges that degraded raster back with bilinear sampling for
  comparison. Reorder it like any effect—for example, after ink/paper/rotation,
  before artifacts applied to the digital scan. The usual 1024 model resize
  happens afterward regardless of this setting.
  Physical width is an explicit assumption, not inferred scan metadata. The
  1400-pixel synthetic source is about 169 DPI at A4 width; imported scans may
  already have been reduced during import. Requests above available resolution
  preserve source pixels and display a source-limit note. Exported parameters
  record assumed width, requested/effective DPI and sampled dimensions. This
  models sampling loss, not scanner optics, thresholding or compression.
- **Black & white scan** thresholds to two pixel values with no dithering.
  Choose a fixed threshold, automatic global Otsu threshold, or local Gaussian
  adaptive threshold for uneven backgrounds. Higher fixed thresholds make more
  pixels black; adaptive mode uses a `(2 × radius + 1)` pixel neighborhood and
  subtracts the offset from its local weighted mean. Fixed threshold is ignored
  by automatic methods; radius/offset apply only to adaptive mode.
  Put this after DPI reduction and rotation to emulate a final bilevel scan.
  When it is the last active effect, the native augmented PNG is saved as a true
  1-bit image. Later effects may legitimately restore grey pixels. The separate
  1024 RGB model input still uses bilinear resizing, so grey edge pixels there
  are expected; changing the scan does not change model preprocessing. Exact
  threshold settings (including Otsu's chosen threshold) are in the manifest.
- Additional Augraphy effects are available individually in **Add effect**:
  **DirtyDrum** (stripe width, concentration, direction, intensity),
  **DirtyRollers** (line width, white/dark scanline type),
  **DirtyScreen** (clusters, point count, spread, brightness),
  **LinesDegradation** (replacement/split probability, thickness, minimum line
  length, brightness), **LowInkPeriodicLines** (count, period, noise, consistency),
  **LowInkRandomLines** (count, noise, consistency), **Markup** (type, ink,
  requested count, length, thickness, monochrome brightness), and **SubtleNoise**
  (noise range). They support the same ordering, bypass and seed behavior.
  Markup is content-dependent, so requested counts are not guaranteed. These
  effects use the grayscale scan path; they do not add musical ground-truth
  annotations. DirtyRollers uses Augraphy's original Python mask routine rather
  than its import-time Numba dispatcher, ensuring reproducible non-JIT execution;
  the manifest records this execution mode. Parameters are experimental controls,
  not presets calibrated to real scanners.
- A recipe seed plus each step's stable ID determines its random stream.
  Moving/disabling another step does not reassign that stream, although changed
  upstream pixels/dimensions can change the result. The manifest records requested
  steps (including disabled ones), executed order, exact backend parameters,
  per-step seeds and before/after dimensions. Old previews are never overwritten.
- Rotation remains Pillow bicubic at 2× resolution with Lanczos downsampling,
  expanded white canvas and exact zero-degree bypass; fractional angles are now
  supported. PageBorder's own rotation is disabled. Other scan effects still use
  Augraphy. Composite starters are experimental variations, not newly calibrated
  reproductions of the earlier accepted monolithic preset. The standalone
  degradation notebook and legacy API profile path remain unchanged.
- Compare source/augmented pages, select rendered size or the current pilot's
  RGB 1024 × 1024 bilinear input, and zoom to 100%/200%. Click either image for
  detail crops; arrow keys move the detail location on a focused image.
  These are matching relative viewports, not registered crops after geometry changes.
- Import a real scan through the existing review queue to explore it in stage 4.
  Its original scan is the comparison reference; no clean ground truth is inferred.
- **Export preview & recipe** downloads exactly the displayed preview, both input
  resolutions, a manifest with settings/parameters/seeds/versions/hashes, and source
  Humdrum plus derived SVG/MEI for synthetic examples. Changing controls does not change an existing
  preview/export; generate again first.

Preview artifacts are append-only in `<data-dir>/curriculum/<unique-id>/` and
remain separate from annotation approval and reviewed training-pair exports.
They have no assigned train/validation/test split. Full-page real-scan labels are
not inferred from passage annotations. No model or training job is loaded.
Each preview runs in a fresh Python worker process, initializing Verovio fonts
on its own main thread. Native renderer failures return an error without aborting
the HTTP server. Workers have a 120-second timeout; requests remain serialized.
Workers inherit the server's rendering environment. If the browser loses its
connection, check the server terminal and SSH tunnel, then restart/reload as needed.

Synthetic rendering needs Verovio, Cairo and HarfBuzz's `hb-shape`. On this Mac,
use the Homebrew Cairo library path when starting the web server:

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python apps/bar_review/server.py
```

The desktop launcher sets this Cairo path automatically when available. On other
machines, use the installed system Cairo library. No ignored experiment activation
script is required. The lab uses existing Python dependencies and no new JS
dependencies. `pnpm --dir apps/bar_review install --ignore-scripts --lockfile=false`
is an alternative when npm is unavailable for the existing notation editor.

Limits: the proposed stage-3 notation coverage is only partially illustrated;
no handwriting generation, spatial transform mapping, automatic legibility
approval, curriculum training or batch dataset export is provided. Square model
resizing matches the current pilot and can distort non-square pages. Preview
files accumulate until manually archived or removed with the server stopped.

### Transcription queue

1. Choose **Import scans**, enter a local folder and choose **Find scans**.
   Select a PDF or image and a page range (up to ten pages at a time).
2. The app proposes passages automatically and presents the first pending one.
   The surrounding staff remains visible; **Show full page** reveals more context.
3. Confirm the written-pitch context: instrument, clef, key, time and sounding
   transposition. Page defaults are only inherited within that page, since a
   section PDF can contain different parts. Override them within a page when needed.
4. Enter music using the keyboard or notation toolbar. **Apply to editor** updates
   its context without intentionally transposing entered notes. This can reflow
   notation, so verify it afterwards. The initial blank measure uses quarter
   rests in 4/4; replace/check every note and rest.
   The selected note or rest has an outline. Select its position, choose a
   dynamic and click **Set dynamic**, or enter a direction such as `unis.` and
   click **Set text**. These markings save with the score and export as MusicXML
   directions. **None** removes the selected position's dynamic; empty text
   removes its first text direction. Undo also applies to these changes.
5. **Approve & next** saves a reviewed transcription and advances to the next
   pending passage. **Skip**, **Unclear** and **Bad crop** retain separate queues.
   Return to a queue or click a numbered region to revisit it. Draft edits save
   automatically; wait for the saved indicator before closing.
6. **Export reviewed pairs** downloads a ZIP containing approved image crops and
   MusicXML, page images and a JSON manifest with coordinates, context and review
   state. Unapproved transcriptions are included only in the manifest as review
   history, not as approved training examples. It is not a single assembled-part
   MusicXML export yet.

The **Adjust the crop** section edits source-page pixel coordinates. A crop
containing a multimeasure rest or multiple bars can record **Bars represented**;
this is metadata and does not automatically create the matching notation.
Ties/slurs crossing passage boundaries should be recorded in review notes until
cross-region editing and full-part assembly are implemented.

## Keyboard

Click the notation once to focus it. Buttons return focus to the editor.

| Shortcut | Action |
| --- | --- |
| A–G | Enter pitch and advance |
| 1–5 | Whole, half, quarter, eighth, sixteenth duration |
| Left / right | Select previous / next note |
| Shift + left / right | Extend selection |
| Up / down | Raise / lower octave |
| + / − | Raise / lower semitone |
| R / . / T | Rest / dot / triplet |
| Ctrl/Cmd Z | Undo notation edit |
| Space | Synthesized playback at 120 BPM |
| Ctrl/Cmd Enter | Approve and advance |
| Alt S / U / B | Skip / unclear / bad crop |

Playback is a simple synthesized reference, not an instrument sound library or
a complete MusicXML performance engine (for example, repeats are not executed).

## Storage and limits

Working source copies, page PNGs and `annotations.sqlite3` are stored under
`apps/bar_review/outputs/`, ignored by Git. Original scans are read-only and no
scan or annotation is sent to an external service. Back up that folder while
the server is stopped. npm dependencies are served locally; normal use needs no
external scripts or audio services.

Segmentation currently uses image morphology, not a trained detector. Expect
mistakes on warped pages, unusual layouts and narrow pickups. Boundaries are
explicitly marked unverified. This version provides coordinate adjustment and
bad-crop flagging; interactive splitting/merging, a trained segmenter, context
recognition, model suggestions, cross-bar notation editing and complete jazz
notation controls remain future work. The preserved full pages make it possible
to derive larger training examples later.

Smoosic supplies the notation model, rendering, note transformations and MusicXML
conversion. It is installed as an MIT-licensed npm dependency; its license is in
`node_modules/smoosic/LICENSE`. The editor integration needs representative manual
testing for MusicXML fidelity, jazz symbols and keyboard ergonomics before using
it to build a trusted dataset.

## Desktop code navigation

The desktop entry point remains `desktop.py`. Responsibilities are split by
concern so UI, worker and file-format changes have a clear home:

| Module | Responsibility |
| --- | --- |
| [desktop.py](desktop.py) | CLI, session state, level/source/recipe editing, view coordination and shutdown. |
| [desktop_layout.py](desktop_layout.py) | Initial BUI tree, workspace choices and callback bindings. |
| [desktop_curriculum.py](desktop_curriculum.py) | Stage editing, source-type selection, add/duplicate/remove/reorder controls. |
| [curriculum_plan.py](curriculum_plan.py) | Project-local stage defaults, limits and validation, independent of BUI. |
| [desktop_widgets.py](desktop_widgets.py) | Reusable image viewports, numeric ranges, draggable regions and recipe panels. |
| [desktop_preview.py](desktop_preview.py) | Selected/batch job submission, queued progress and completion polling. |
| [desktop_projects.py](desktop_projects.py) | Project/legacy-recipe snapshots, restoration and save/open/export actions. |
| [desktop_storage.py](desktop_storage.py) | Read-only scan collection access, exclusive exports and atomic backed-up writes; no BUI dependency. |
| [desktop_dialog.py](desktop_dialog.py) | Non-blocking file-browser lifecycle on the existing native event loop. |
| [lab_project.py](lab_project.py) | Portable archive schema, validation, assets and immutable restore. |
| [preview_worker.py](preview_worker.py) | Crash-isolated preview process and IPC. |

`CurriculumDesktop` owns the live session and resources. Its explicit action
methods delegate to `ProjectActions` and `PreviewJobs`, which receive the host
through their constructors. Runtime imports flow from the entry point into these
modules; collaborators use type-only imports of the host. Widgets use callbacks
and do not depend on the coordinator. Keep new reusable controls in the widget
module and initial layout changes in the layout module.

Only the UI thread mutates BUI nodes. Preview submissions capture request and
document snapshots; the batch runner executes on the single executor thread and
posts plain progress/results for UI polling. The coordinator closes the dialog,
worker and executor. File callbacks capture project/recipe bytes or a preview ID
when opened, preserving the displayed snapshot during asynchronous activity.
Retain the synchronous RGBA image path and non-blocking dialog loop: both avoid
previously reproduced native crashes.

The existing desktop/project tests exercise interactions through the coordinator,
including project portability, dialog snapshots, stale jobs, ranges and resizing.
Install the desktop extra to run them; without BUI they are skipped.

## Checks

```bash
uv run python -m unittest discover -s apps/bar_review -p 'test_*.py' -v
node --check apps/bar_review/public/app.js
node --check apps/bar_review/public/editor.js
node --check apps/bar_review/public/curriculum.js
```

The curriculum tests check actual Augraphy replay, RNG restoration, unchanged
source scans, immutable exports/hashes and input/path validation. All eight
synthetic types were also rendered with Augraphy in a manual integration smoke
check. HTTP page/API/image/ZIP checks passed; browser layout and interaction QA
has not been executed in this environment.
