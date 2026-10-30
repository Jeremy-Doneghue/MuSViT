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

## Workflow

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
```
