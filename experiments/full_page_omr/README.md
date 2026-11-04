# Full-page OMR workspace

Start with [the project diary](../../PROJECT_DIARY.md) for decisions and the latest
results. This directory contains the current `musvit-score-v1` experiments.
The original bekern/Lightning pipeline has been removed; its implementation
remains available in the [original MuSViT repository](https://github.com/OMR-PRAIG-UA-ES/MuSViT).

## Where things live

| Directory / file | Purpose | Used by |
| --- | --- | --- |
| `generation/` | Synthetic parts, MusicXML/MEI conversion, jazz notation, scenario sampling, fonts | Dataset/tooling work; codec fixtures also use conversion and font helpers |
| `representation/` | Versioned score vocabulary, codec, semantic checks, fixtures, optional grammar constraints | All current exports, training and evaluation |
| `datasets/` | Pilot, clean-page and short-staff exports/adapters; controlled dense edits | Current training and transfer probes |
| `training/` | Pilot and clean-page trainers; short-staff orchestration | Current experiments; shared model/greedy-decoding helpers live here too |
| `diagnostics/` | Musical-field and image-swap probes, constrained evaluation, re-engraving | Evaluation of saved runs |
| `smt_foundation/` | Shared encoder/decoder model and configuration | Current training and diagnostics |
| `paths.py` | Stable experiment-root location | Source provenance hashes after relocation |
| `docs/` | Dataset/codec guides and experiment reports | Reading and reproduction |
| `outputs/` | Ignored datasets, saved runs, diagnostics and local native dependencies | Existing experiment artifacts; preserved in place |
| `weights/` | Original pipeline's local checkpoints | Historical artifacts; preserved in place |

## Current experiment path

The latest completed experiment is the [short-staff transfer diagnostic](docs/SHORT_STAFF.md).
It failed transfer and sampled training validity. Curriculum learning beginning
with one note is a proposed investigation; it has not been implemented or run.

```text
representation/codec_fixtures + datasets/clean_page_data
                      |
             datasets/short_staff_data
                      |
          training/short_staff_experiment
                      |
          training/clean_page_experiment
                      |
             training/overfit_pilot
                      |
               smt_foundation
```

`overfit_pilot.py` is shared infrastructure as well as an older experiment:
`local_encoder`, `make_model`, `CachedGreedy` and related decoding helpers are
still used by current trainers and diagnostics. `datasets/pilot_data.py` similarly
provides export, hashing and adapter helpers used beyond the pilot.
`short_staff_experiment.py` also calls `diagnostics/clean_page_diagnostics.py` for
field metrics. These historical names do **not** indicate dead code.

## Commands and reports

Run from the repository root. CLI arguments remain documented in the linked
reports; module names now include their purpose directory.

| Task | Module (`python -m ...`) | Guide |
| --- | --- | --- |
| Generate instrumental parts | `experiments.full_page_omr.generation.generate_parts` | [Synthetic parts](docs/SYNTHETIC_PARTS.md) |
| Compare fonts | `experiments.full_page_omr.generation.font_coverage` | [Font coverage](docs/FONT_COVERAGE.md) |
| Export codec fixtures | `experiments.full_page_omr.representation.codec_fixtures` | [Score codec](docs/SCORE_CODEC.md) |
| Tiny/dense overfit training | `experiments.full_page_omr.training.overfit_pilot` | [Pilot](docs/OVERFIT_PILOT.md), [dense overfit](docs/DENSE_OVERFIT.md) |
| Export clean pages | `experiments.full_page_omr.datasets.clean_page_data` | [Clean baseline](docs/CLEAN_BASELINE.md) |
| Clean-page/diversity training | `experiments.full_page_omr.training.clean_page_experiment` | [Long baseline](docs/LONG_BASELINE.md), [diversity](docs/DIVERSITY_BASELINE.md) |
| Export short passages | `experiments.full_page_omr.datasets.short_staff_data` | [Short staff](docs/SHORT_STAFF.md) |
| Train/evaluate short passages | `experiments.full_page_omr.training.short_staff_experiment` | [Short staff](docs/SHORT_STAFF.md) |
| Controlled note edits | `experiments.full_page_omr.datasets.dense_contrast`, `experiments.full_page_omr.datasets.dense_composition` | [Controlled edits](docs/CONTROLLED_EDITS.md) |
| Evaluate edit transfer | `experiments.full_page_omr.diagnostics.dense_contrast_eval` | [Controlled edits](docs/CONTROLLED_EDITS.md) |
| Musical-field probes | `experiments.full_page_omr.diagnostics.clean_page_diagnostics` | [Long baseline](docs/LONG_BASELINE.md) |
| Aggregate image-conditioning probe | `experiments.full_page_omr.diagnostics.clean_page_conditioning` | [Clean baseline](docs/CLEAN_BASELINE.md) |
| Compare grammar constraints | `experiments.full_page_omr.diagnostics.constrained_experiment` | [Constrained decoding](docs/CONSTRAINED_DECODING.md) |
| Re-engrave pilot predictions | `experiments.full_page_omr.diagnostics.pilot_review` | [Pilot](docs/OVERFIT_PILOT.md) |

## Removed pipeline and migration notes

The legacy bekern datasets, Lightning trainer, excerpt renderer, augmentation,
configs and vocabularies were deleted on 2026-11-04 at the user's request, along
with the `musvit full-page-omr` launcher and legacy-only runtime helper. The
legacy parser/vocabulary audit script was removed because it reads those sources;
its [historical findings](docs/TARGET_FORMAT_ANALYSIS.md) remain documented.

Use the module commands above for current experiments. Shared model code and
pilot helpers remain because they are used by current training and evaluation.
Saved datasets, checkpoints and historical outputs remain in place.

Flat Python import and `python -m` paths have moved to the directories above;
there are no compatibility wrappers. Repository callers, tests and report commands
have been updated. Saved manifests, datasets, checkpoints and ignored historical
scripts are untouched. Historical scripts that import the old flat module names
need the same module-path updates before rerunning. Old source hashes describe
those original runs; newly exported data/runs record the reorganized source hashes.

For local validation with the existing native rendering dependencies:

```sh
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh
.venv/bin/python -m unittest discover -s tests -v
```

The activation script is a local artifact, not a portable installation recipe;
see the [pilot setup report](docs/OVERFIT_PILOT.md#mac-studio-rerun--2026-10-31)
for details.
