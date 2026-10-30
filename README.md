<p align="center">
  <a  href="#"> <img src="https://raw.githubusercontent.com/OMR-PRAIG-UA-ES/MuSViT/refs/heads/main/resources/musvit_logo.svg" alt="MuSViT-logo" width="25%"></a>
</p>
<h1 align="center">MuSViT: A Foundation Vision Model for Sheet Music Representation</h1>
<h4 align="center">📄 Official publication at ECCV 2026.</h4>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.x-orange" alt="Python">
  <img src="https://img.shields.io/badge/uv-managed-6340ac?logo=uv&logoColor=white" alt="uv">
  <img src="https://img.shields.io/badge/-Weights%20%26%20Biases-FFBE00?logo=weightsandbiases&logoColor=black" alt="W&B">
  <img src="https://img.shields.io/static/v1?label=License&message=CC%20BY-NC-SA%204.0&color=blue" alt="License">
  <a href="https://arxiv.org/abs/2606.31811"><img src="https://img.shields.io/badge/arXiv-2606.31811-b31b1b.svg" alt="arXiv"></a>
  <a href="https://huggingface.co/PRAIG/musvit"><img src="https://img.shields.io/badge/🤗%20Hugging%20Face-PRAIG%2Fmusvit-yellow" alt="HuggingFace"></a>
</p>

<p align="center">
  <a href="#about">About</a> •
  <a href="#repository-layout">Repository Layout</a> •
  <a href="#installation">Installation</a> •
  <a href="#environment-variables">Environment Variables</a> •
  <a href="#running-experiments">Running Experiments</a> •
  <a href="#citations">Citations</a> •
  <a href="#acknowledgements">Acknowledgements</a> •
  <a href="#license">License</a>
</p>

<a name=about></a>
## 📚 About

This working repository is based on the official code for **MuSViT: A Foundation Vision Model for Sheet Music Representation**, presented at ECCV 2026, and focuses on synthetic data and OMR. The inherited difficulty-estimation and embedding-analysis experiments have been removed; staff-level OMR and symbol detection remain available as related baselines.

This is a **monorepo** collecting the experiments around MuSViT. Every experiment lives under [`experiments/`](experiments/) and is launched from the repository root through a single cross-platform CLI: **`musvit`**.

For ongoing synthetic full-page/multi-page OMR work, start with the
[project diary](PROJECT_DIARY.md): current state, proposed next steps, and dated
session handoffs. The [synthetic parts guide](experiments/full_page_omr/SYNTHETIC_PARTS.md)
documents the generator and dataset conventions.

This project includes:
- A central CLI (`musvit`) to discover and run all experiments from the repository root.
- A full-page Optical Music Recognition (OMR) fine-tuning pipeline.
- A staff-level OMR fine-tuning pipeline (linear probing or LoRA).
- An object-detection fine-tuning pipeline (Faster R-CNN with a MuSViT backbone).
- Synthetic instrumental-part generation, font coverage checks, and scan-degradation experiments.
- A local transcription-review prototype for building reviewed image/MusicXML pairs.

<a name=repository-layout></a>
## ⚙️ Repository Layout

| Folder | Description |
| --- | --- |
| [`musvit/`](musvit/) | Central launcher (`musvit` CLI): discovers and runs the experiments. |
| [`experiments/full_page_omr/`](experiments/full_page_omr/) | Fine-tune MuSViT for full-page Optical Music Recognition (OMR). |
| [`experiments/staff_level_omr/`](experiments/staff_level_omr/) | Fine-tune MuSViT for staff-level OMR (BiLSTM/CTC head; linear probing or LoRA). |
| [`experiments/object_detection/`](experiments/object_detection/) | Fine-tune MuSViT + Faster R-CNN for object detection (COCO-format data). |
| [`experiments/scan_degradation/`](experiments/scan_degradation/) | Explore reproducible photocopy effects for training-image augmentation. |
| [`apps/bar_review/`](apps/bar_review/) | Review and transcribe scanned passages locally. |
| [`data/`](data/) | Shared local PDF/MusicXML reference parts. |

Generated artifacts live under the producing experiment's `outputs/` directory
and are ignored by Git. Synthetic parts and font sheets are under
`experiments/full_page_omr/outputs/`; scan comparisons are under
`experiments/scan_degradation/outputs/`. Older synthetic exports are retained in
`experiments/full_page_omr/outputs/archive/`. The root `resources/` directory
contains the project logo. Engraving uses Verovio's bundled music fonts; no
separate downloaded Petaluma bundle is needed.

For visual scan experiments, open the
[scan degradation notebook](experiments/scan_degradation/scan_degradation.ipynb).
The [experiment guide](experiments/scan_degradation/README.md) includes Jupyter
setup and launch instructions.

<a name=installation></a>
## 🔧 Installation

The whole monorepo shares a single [uv](https://docs.astral.sh/uv/) project defined at the repository root ([`pyproject.toml`](pyproject.toml) / [`uv.lock`](uv.lock)). Install the environment once from the root:

```bash
uv sync
```

This also installs the `musvit` console command into the project environment.

Rendering and PDF import additionally rely on **system libraries** that `uv` does not manage:

- **ImageMagick** — used by `wand` in the full-page-OMR synthetic data generator (`brew install imagemagick`, or `apt install libmagickwand-dev`).
- **poppler** — used by PDF import in Bar Review and by the scan-degradation experiment (`brew install poppler`, or `apt install poppler-utils`).

<a name=environment-variables></a>
## 🔑 Environment Variables

Experiments authenticate against [Weights & Biases](https://wandb.ai) and the [Hugging Face Hub](https://huggingface.co). These credentials are shared across the whole monorepo through a single `.env` file at the repository root.

1. Copy the template:
```bash
   cp .env.example .env
```
2. Fill in your keys in `.env`:
```dotenv
   WANDB_API_KEY=...
   HUGGINGFACE_KEY=...
```

`.env` is git-ignored; only `.env.example` is committed. The `musvit` launcher loads this `.env` once at startup and automatically bridges `HUGGINGFACE_KEY` to `HF_TOKEN` / `HUGGING_FACE_HUB_TOKEN`, so every experiment authenticates from the same key regardless of which variable it reads.

<a name=running-experiments></a>
## 🚀 Running Experiments

All experiments are launched from the repository root with `musvit`. List what is available:

```bash
uv run musvit list
```

Each subcommand maps its options directly onto the experiment's Python entrypoint, and `--help` is generated automatically:

```bash
uv run musvit full-page-omr --help
uv run musvit staff-level-omr --help
uv run musvit object-detection --help
```

### Full-page OMR (fine-tuning)

```bash
uv run musvit full-page-omr \
  --config_path experiments/full_page_omr/config/Polish_Scores/finetuning.json \
  --experiment_name my_experiment \
  --finetuning CL
```

Checkpoints and W&B logs are written inside `experiments/full_page_omr/` (`weights/`, `wandb_logs/`).

The experiment automatically selects CUDA, Apple Silicon MPS, or CPU. CUDA
defaults to mixed precision; MPS and CPU default to full precision. On macOS,
data loading defaults to zero worker processes to avoid duplicating the in-memory
datasets and synthetic generator. Override these settings with `--accelerator`,
`--precision`, and `--num_workers`. For example, add `--accelerator mps
--num_workers 0` on a Mac. Full-page training memory depends strongly on the
transcription length; benchmark representative pages before a long run.

To preview synthetic training pairs without training a model:

```bash
uv run python -m experiments.full_page_omr.generate_examples \
  --count 4 --max-systems 4 --seed 20261028
```

This downloads GrandStaff if it is not already cached, then uses the training
renderer and augmentation pipeline. Outputs are saved to
`experiments/full_page_omr/outputs/training_examples/`: a `preview.jpg` contact
sheet, rendered and augmented images, exact `bekern` target tokens, decoded
targets, reconstructed `.krn` files, and a manifest recording seeds and image
sizes. Source excerpt counts cycle from 1 to `--max-systems`; Verovio determines
the visible number of systems. Use `--output-dir` to choose another folder
(relative paths are resolved from your current directory), or `--resolution`
to change the default 1024px training input size. The command requires the same
native rendering dependencies as full-page training. On Homebrew macOS, if
those libraries are not found, prefix the command with
`MAGICK_HOME="$(brew --prefix imagemagick)" DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"`.

### Local transcription editor

The [Bar Review prototype](apps/bar_review/README.md) presents scanned parts as
a queue of automatically proposed bar regions, retaining the surrounding staff
for context. It includes a Smoosic notation editor, separate review statuses,
local draft saving, and export of approved image/MusicXML pairs.

```bash
npm ci --prefix apps/bar_review
uv run python apps/bar_review/server.py
```

Open <http://127.0.0.1:8765/>. Scans and annotations remain local; segmentation
is preliminary, and the editor is not yet connected to an OMR model.

### Staff-level OMR (fine-tuning)

```bash
uv run musvit staff-level-omr \
  --ds_name catedrales \
  --model_name musvit \
  --method lora \
  --shape_patches '[8,128]'
```

Fine-tunes a MuSViT backbone with a BiLSTM/CTC head on cropped staves, by either linear probing (`--method linear_prob`, frozen backbone) or LoRA (`--method lora`). Checkpoints (`<model>_<ds>_<method>_<cols>_ctc.pt`) are written inside `experiments/staff_level_omr/`. Requires a GPU and editing the dataset paths in [`config.py`](experiments/staff_level_omr/config.py) to point at your local data.

### Object Detection (Faster R-CNN fine-tuning)

```bash
uv run musvit object-detection \
  --model musvit_base \
  --train_images /path/to/images \
  --train_ann /path/to/train.json \
  --val_images /path/to/images \
  --val_ann /path/to/val.json \
  --finetuning lora
```

Fine-tunes a Faster R-CNN with a MuSViT + FPN backbone. Annotations are read in **COCO format** (`images` / `annotations` / `categories`); convert DeepScores (or any detection set) to COCO and point `--train_ann` / `--val_ann` at the JSON files — the number of classes is inferred from `categories`. `--finetuning` selects `full`, `frozen` (freeze the ViT) or `lora` (LoRA adapters on q/k/v). Checkpoints (`ckpt-best.pt`, `ckpt-latest.pt`) are written inside `--out_dir` (under `experiments/object_detection/`); `--use_wandb` enables W&B logging and `--from_checkpoint` resumes. Requires a GPU.

<a name=citations></a>
## 📖 Citations

```bibtex
@InProceedings{Penarrubia:ECCV:2026,
  author="Penarrubia, Carlos
  and Rios-Vila, Antonio
  and Fuentes-Martinez, Eliseo
  and Martinez-Sevilla, Juan C.
  and Castellanos, Francisco J.
  and Alfaro-Contreras, Mar{\'i}a
  and Calvo-Zaragoza, Jorge",
  editor="Favaro, Paolo
  and Kukelova, Zuzana
  and Maki, Atsuto
  and Rohrbach, Anna
  and Schindler, Konrad
  and Tombari, Federico",
  title="MuSViT: A Foundation Vision Model for Sheet Music Representation",
  booktitle="Computer Vision -- ECCV 2026",
  year="2026",
  publisher="Springer Nature Switzerland",
  address="Cham",
  pages="459--476",
  isbn="978-3-032-37271-0",
  doi="10.1007/978-3-032-37271-0_25",
  url="https://doi.org/10.1007/978-3-032-37271-0_25"
}
```

<a name=acknowledgements></a>
## 🙏 Acknowledgements

The authors gratefully acknowledge Edward Guo, on behalf of IMSLP/Petrucci Music Library, for providing access to the data used to train the models.

This publication is part of the LEMUR project PID2023-148259NB-I00, funded by MICIU/AEI/10.13039/501100011033 and by ERDF/EU. The first author is supported by the University of Alicante through the FPU Program (UAFPU22-19). The third author is supported by a predoctoral contract associated with the LEMUR project. The fourth author is supported by a predoctoral contract from grant CISEJI/2023/9 "Programa para el apoyo a personas investigadoras con talento (Plan GenT) de la Generalitat Valenciana".

<a name=license></a>
## 📝 License

This work is under a [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) license.

> ⚠️ **Disclaimer**  
> This github is under active development. Some parts of the codebase may not work as expected or could change without notice.  
> Please proceed with caution and check back for updates.
