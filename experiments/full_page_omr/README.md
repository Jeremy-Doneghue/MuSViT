# Full-page OMR workspace

Start with [the project diary](../../PROJECT_DIARY.md) for decisions and verified
state. New curriculum examples are authored directly in **kern/Humdrum and
rendered by Verovio. MusicXML is optional at import/editor boundaries.

## Current code

| Path | Responsibility |
| --- | --- |
| [generation/humdrum_scores.py](generation/humdrum_scores.py) | Seeded Humdrum sources for eight examples; direct SVG/MEI/raster rendering and source checks. |
| [generation/font_resources.py](generation/font_resources.py) | Portable text outlines, font metadata and glyph-fallback inspection. |
| [smt_foundation/](smt_foundation/) | Reusable MuSViT encoder/Transformer decoder and configuration. No dependency on the retired score-tree codec. |
| [../../apps/bar_review/](../../apps/bar_review/) | Curriculum Lab desktop/web UI, scan recipes, isolated preview workers, project/export storage and transcription review. |
| [../scan_degradation/](../scan_degradation/) | Reproducible scan-image degradation tools shared with the app. |

## Current guides

- [Implemented Humdrum pipeline](docs/HUMDRUM_PIPELINE.md): source/image identity,
  artifact formats, checks and limitations.
- [Recognition scope](docs/HUMDRUM_SCOPE.md): pitched parts, piano, percussion,
  dynamics, performance text and explicit omissions/review.
- [Curriculum and dataset design](docs/CURRICULUM_DATASET.md): musical complexity,
  appearance variation, source-family splits and evaluation proposals.
- [Collection requirements](docs/TARGET_COVERAGE.md): the notation inventory and
  examples that still need coverage.
- [Historical reports](docs/HISTORY.md): previous experiments, measured results
  and how to retrieve the removed implementation from Git.

## Run and verify

From the repository root:

```sh
.venv/bin/python apps/bar_review/desktop.py
PYTHONPATH=apps/bar_review .venv/bin/python -m unittest discover -s apps/bar_review -p 'test_*.py' -q
.venv/bin/python -m unittest discover -s tests -v
```

The desktop extra is required for BUI tests. Native SVG-to-PNG rendering needs
Cairo; on this Mac set `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` when needed.
Text outlining requires the HarfBuzz `hb-shape` command. See the app guide for
installation, screenshots and the web server.

There is no active Humdrum training command yet. Next work is broader scoped
notation validation, arbitrary-input normalization and a tokenizer/training
adapter. The model implementation is retained for that work; the old training
entrypoints must not be treated as a Humdrum baseline.

The retired MusicXML generators, restricted tree codec, dataset exporters,
pilot trainers and their diagnostics/tests were removed after the Humdrum move.
No replacement compatibility modules or executable archive was added. Reports
stay at their existing paths with historical notices so diary links remain useful.
Generated datasets, scans, annotations, weights and user projects were not deleted
or rewritten; `outputs/` and `weights/` are local artifacts, not documentation.
