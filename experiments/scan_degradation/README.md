# Scan degradation with Augraphy

Rasterizes a PDF page with Poppler and applies **Augraphy** effects.
There is no custom photocopy simulation. The light-copy preset is a dictionary
of arguments passed directly to BadPhotoCopy; the small wrapper handles seeds,
previews and export. An optional `library-scan` recipe adds a dark scanner edge,
paper boundary, extra scan canvas and a slight rotation using Augraphy's
Geometric and PageBorder effects.

- [BadPhotoCopy parameters and examples](https://augraphy.readthedocs.io/en/latest/doc/source/augmentations/badphotocopy.html)
- [Geometric framing/rotation](https://augraphy.readthedocs.io/en/latest/doc/source/augmentations/geometric.html)
- [PageBorder](https://augraphy.readthedocs.io/en/latest/doc/source/augmentations/pageborder.html)
- [How Augraphy Works](https://augraphy.readthedocs.io/en/latest/doc/source/how_augraphy_works.html)

## Notebook

Open [the scan degradation lab](scan_degradation.ipynb) for whole-page comparisons,
passage/detail crops, editable light-copy parameters and library-scan framing controls:

```bash
uv sync --group notebooks
uv run --group notebooks jupyter lab experiments/scan_degradation/scan_degradation.ipynb
```

Select the project's Python kernel. Run all cells, then edit the PDF/page, seed,
Augraphy parameters, or crop boxes and rerun the affected cells. The default PDF
is the local reference at `data/reference_parts/Monsters_Inc-Bb_Clarinet.pdf`.
Poppler's `pdftoppm` must be installed (`brew install poppler` on macOS).

Preview uses temporary raster files and leaves existing outputs alone. The final
cell exports only when `EXPORT = True`, to a new directory. It saves the inspected
arrays, source hash, Augraphy version, exact parameters/seeds, per-image crop coordinates and
optional review note. Source notebook outputs are cleared; saved/executed copies
belong in `outputs/`. Start Jupyter at the repo root or inside this experiment.

## Command line

From the repository root, choose a new output directory:

```bash
uv run python experiments/scan_degradation/generate.py \
  data/reference_parts/Monsters_Inc-Bb_Clarinet.pdf \
  --library-scan \
  --output experiments/scan_degradation/outputs/augraphy_run_001
```

`--page` starts at 1; `--seed` defaults to 42. Output defaults to this experiment's
`outputs/` directory, independent of working directory. Explicit relative paths
resolve from the caller's working directory. Existing directories are rejected.

Exports contain:

- `clean.png`: original page rasterized at 300 DPI.
- `light-copy.png`: the retained light Gaussian-noise BadPhotoCopy preset.
- `library-scan.png`: optional framed/rotated page (`--library-scan`).
- `comparison.png`: opening-passage viewports at the same relative page location.
- `manifest.json`: schema version 3, backend, installed Augraphy version, source
  hash, raster resolution, per-variant output dimensions, effect order, exact
  parameters/seeds and whether each variant changes geometry.

BadPhotoCopy-only profiles keep source coordinates. `library-scan` is inspired by
a real library example: most notation stays clean, with slight rotation, an inset
sheet and a wider dark band along the right edge. Its groups are direct kwargs
for Geometric (dark edge), PageBorder, BadPhotoCopy (localized right-side noise)
and Geometric (white padding then rotation). It expands the canvas rather than
intentionally cropping notation. Augraphy 8.2.6 samples integer Geometric rotation
angles; the initial recipe fixes the angle at -1 degree.

Library-scan changes spatial coordinates and dimensions. Notebook crops use each
variant's own relative viewport and are not geometrically registered. New exports
explicitly mark this; no source-to-output coordinate mapping is provided. Source
boxes/masks must be transformed before using this recipe for spatial training.
This is an approximate recipe, not a reconstruction or calibration of that scan.

## Reproducibility and existing runs

Light-copy uses the base seed; library-scan uses base seed + 3. Its offset stays
fixed to preserve the reviewed appearance when other profiles change. The wrapper temporarily seeds Python and NumPy,
then restores their states and Augraphy's global Numba JIT setting. Presets use
`numba_jit=0` for repeatable sequential notebook/CLI previews; this wrapper is not
intended for concurrent threads. Exact results depend on installed library
versions and settings; keep `uv.lock` and the exported manifest with experiments.

Earlier exports and `outputs/notebook_validation/` were produced by the retired
custom simulator. They are retained as historical outputs; their old profiles and
affine metadata must not be interpreted as Augraphy configuration. Initial pixel-only Augraphy validation is in `outputs/augraphy_validation/`;
framing-recipe validation is in `outputs/library_scan_validation/`. Old version-2
manifests describe pixel-only variants; version 3 moves geometry metadata to each
variant because one run can now contain both pixel-only and spatial effects.

## Visual review

The user reviewed library-scan as good and light-copy as acceptable. Worn-copy
and the notebook's previous custom profile produced unrealistic noise and have
been removed from active presets/previews. Historical output folders are retained
as records of those experiments; they are not current dataset recipes.

These are starting settings, not calibrated photocopier models. Inspect dots,
accidentals, staff lines, ties and rest counts before using variants as training
pairs. Next: tune against real photocopies, then compare clean-only and augmented
training on held-out parts. Split by source piece before generating variants.

Checks: `uv run python -m unittest discover -s tests -p test_scan_degradation.py -v`.
