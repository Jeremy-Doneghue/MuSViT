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
  MusicXML for synthetic examples. Changing controls does not change an existing
  preview/export; generate again first.

Preview artifacts are append-only in `<data-dir>/curriculum/<unique-id>/` and
remain separate from annotation approval and reviewed training-pair exports.
They have no assigned train/validation/test split. Full-page real-scan labels are
not inferred from passage annotations. No model or training job is loaded.
Each preview runs in a fresh Python worker process, initializing Verovio fonts
on its own main thread. Native renderer failures return an error without aborting
the HTTP server. Workers have a 120-second timeout; requests remain serialized.
Workers inherit the server's rendering environment, so source the activation
script below before starting the server. If the browser loses its connection,
check the server terminal and SSH tunnel, then restart/reload as needed.

Synthetic rendering needs the repository's Verovio/Cairo setup. On this Mac:

```bash
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh
.venv/bin/python apps/bar_review/server.py
```

That activation script is a local artifact; see the
[rendering setup report](../../experiments/full_page_omr/docs/OVERFIT_PILOT.md#mac-studio-rerun--2026-10-31)
for other machines. The lab uses existing Python dependencies and no new JS
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
