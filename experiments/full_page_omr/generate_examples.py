"""Preview synthetic training pairs without loading or training the model.

Run from the repository root with:
    uv run python -m experiments.full_page_omr.generate_examples --help
"""

import argparse
from contextlib import chdir
import json
from pathlib import Path
import random


PACKAGE_DIR = Path(__file__).resolve().parent


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def generate_examples(output_dir, count=4, max_systems=4, seed=20261028, resolution=1024):
    """Save rendered pages, augmented inputs, targets, and a contact sheet.

    Excerpt counts cycle from one to max_systems; rendered system counts can
    differ because Verovio determines line breaks. Relative output paths are
    interpreted from the caller's working directory.
    """
    if min(count, max_systems, resolution) < 1:
        raise ValueError("count, max_systems, and resolution must be positive")
    from musvit.env import setup

    setup()
    import numpy as np
    from PIL import Image, ImageDraw, ImageOps
    import torch

    from . import _globals
    from .Generator.SynthGenerator import VerovioGenerator
    from .data_augmentation.data_augmentation import augment

    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = min(count, 4)
    rows = (count + columns - 1) // columns
    sheet = Image.new("RGB", (columns * 400, 70 + rows * 940), "#e9e9e9")
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 12), "MuSViT synthetic training pairs", fill="black")
    draw.text((12, 34), "Each pair: rendered page above, augmented training input below.", fill="black")
    manifest = []
    previous_resolution = _globals.resolution
    try:
        _globals.resolution = resolution
        # The existing renderer resolves its bundled paper textures from cwd.
        with chdir(PACKAGE_DIR):
            generator = VerovioGenerator(
                "antoniorv6/grandstaff-ekern", split="train", tokenization_mode="bekern")
            for index in range(count):
                sample_seed = (seed + index + 1) % (2**32)
                random.seed(sample_seed)
                np.random.seed(sample_seed)
                torch.manual_seed(sample_seed)
                systems = index % max_systems + 1
                image, tokens = generator.generate_full_page_score(
                    max_systems=systems, strict_systems=True, strict_height=False,
                    include_title=True, include_author=True)
                rendered = Image.fromarray(image).convert("RGB")
                tensor = augment(image)
                pixels = tensor.squeeze(0).permute(1, 2, 0).numpy()
                training = Image.fromarray((pixels.clip(0, 1) * 255).round().astype("uint8"))
                name = f"example_{index + 1}"
                rendered.save(output_dir / f"{name}_rendered.png")
                training.save(output_dir / f"{name}_training.png")
                (output_dir / f"{name}_tokens.json").write_text(
                    json.dumps(tokens, indent=2), encoding="utf-8")
                decoded = ("".join(tokens[1:-1]).replace("<b>", "\n")
                           .replace("<t>", "\t").replace("<s>", " "))
                (output_dir / f"{name}_target.txt").write_text(decoded, encoding="utf-8")
                # Training targets omit the two-spine header and use bekern markers.
                kern = "**kern\t**kern\n" + decoded.replace("@", "").replace("·", "")
                (output_dir / f"{name}.krn").write_text(kern, encoding="utf-8")

                left = index % columns * 400 + 10
                top = index // columns * 940 + 70
                draw.text((left, top), f"Example {index + 1}: {systems} source excerpt(s)", fill="black")
                for img, offset, height in [(rendered, 30, 470), (training, 520, 400)]:
                    preview = ImageOps.contain(img, (380, height))
                    sheet.paste(preview, (left + (380 - preview.width) // 2,
                                         top + offset + (height - preview.height) // 2))
                record = dict(example=name, source_excerpts=systems, seed=sample_seed,
                              target_tokens=len(tokens), rendered_size=rendered.size,
                              training_size=training.size)
                manifest.append(record)
                print(json.dumps(record), flush=True)
    finally:
        _globals.resolution = previous_resolution

    sheet.save(output_dir / "preview.jpg", quality=92)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "README.txt").write_text(
        "Generated with the actual GrandStaff/Verovio renderer and training augment() function.\n"
        "Excerpt counts cycle from 1 to max_systems; the normal curriculum samples them randomly.\n"
        "Verovio determines visible system counts, which can differ from excerpt counts.\n"
        "*_rendered.png: textured renderer output before training augmentation.\n"
        "*_training.png: augmented input tensor converted back to PNG.\n"
        "*_tokens.json: exact bekern target tokens, including BOS/EOS.\n"
        "*_target.txt: target with whitespace tokens decoded.\n"
        "*.krn: reconstructed notation with the two-spine header restored.\n"
        "Titles are visual distractors, excluded from targets.\n"
        "preview.jpg: contact sheet; manifest.json: seeds, excerpt counts, and image sizes.\n",
        encoding="utf-8")
    print(f"Saved examples to {output_dir}", flush=True)
    return output_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=PACKAGE_DIR / "outputs" / "training_examples")
    parser.add_argument("--count", type=positive_int, default=4, help="Number of examples (default: 4)")
    parser.add_argument("--max-systems", type=positive_int, default=4,
                        help="Maximum source excerpt count to cycle through (default: 4)")
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--resolution", type=positive_int, default=1024,
                        help="Square training input size (default: 1024)")
    args = parser.parse_args()
    generate_examples(**vars(args))


if __name__ == "__main__":
    main()
