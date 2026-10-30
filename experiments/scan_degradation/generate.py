"""Reproducible photocopy previews from a PDF; no notation is regenerated.

Run with the repository Python environment. Requires Poppler's pdftoppm.
Outputs are experimental image variants, not automatically approved labels.
"""
import argparse
from copy import deepcopy
from contextlib import contextmanager
from importlib.metadata import version
import hashlib
import json
import random
from pathlib import Path
import subprocess
import tempfile

from augraphy import BadPhotoCopy, Geometric, PageBorder
from numba import config as numba_config
import numpy as np
from PIL import Image, ImageDraw, ImageFont


# These dictionaries are passed directly to Augraphy's BadPhotoCopy.
# Disable JIT so Python/NumPy seeds control the selected effects consistently.
PROFILES = {
    'light-copy': dict(noise_type=2, noise_side='none', noise_iteration=(1, 1),
                       noise_size=(1, 2), noise_value=(190, 240),
                       noise_sparsity=(0.1, 0.2), noise_concentration=(0.1, 0.2),
                       blur_noise=1, blur_noise_kernel=(3, 3), wave_pattern=0,
                       edge_effect=0, numba_jit=0, p=1),
}


# Ordinary Augraphy constructors, in application order. Inspired by a
# library scan with a dark right edge and extra scanner canvas around the sheet.
LIBRARY_SCAN = dict(
    scanner_edge=dict(padding=(0.002, 0.045, 0.003, 0.003),
                      padding_type='fill', padding_value=(0, 0, 0), p=1),
    page_border=dict(page_border_width_height=(0.035, 0.008),
                     page_border_color=(0, 0, 0), page_border_background_color=(0, 0, 0),
                     page_border_use_cache_images=0, page_numbers=1,
                     page_rotation_angle_range=(0, 0), curve_frequency=(1, 3),
                     curve_height=(2, 5), curve_length_one_side=(40, 100),
                     same_page_border=0, numba_jit=0, p=1),
    photocopy=dict(PROFILES['light-copy'], noise_side='right',
                   noise_value=(170, 230), noise_sparsity=(0.15, 0.25)),
    framing=dict(padding=(0.015, 0.025, 0.01, 0.055),
                 padding_type='fill', padding_value=(255, 255, 255),
                 rotate_range=(-1, -1), p=1),
)


@contextmanager
def _seeded(seed):
    """Isolate Augraphy's process-global random/JIT settings.

    Intended for sequential notebook/CLI previews, not concurrent worker threads.
    """
    python_state, numpy_state = random.getstate(), np.random.get_state()
    jit_disabled = numba_config.DISABLE_JIT
    try:
        random.seed(seed)
        np.random.seed(seed)
        yield
    finally:
        random.setstate(python_state)
        np.random.set_state(numpy_state)
        numba_config.DISABLE_JIT = jit_disabled


def bad_photocopy(source, parameters, seed):
    """Pixel-only Augraphy effect; page coordinates remain unchanged."""
    with _seeded(seed):
        return BadPhotoCopy(**parameters)(source.copy(), force=True)


def library_scan(source, parameters, seed):
    """Augraphy border, localized copying noise, then scanner framing/rotation."""
    with _seeded(seed):
        image = Geometric(**deepcopy(parameters['scanner_edge']))(source.copy(), force=True)
        image = PageBorder(**deepcopy(parameters['page_border']))(image, force=True)
        image = BadPhotoCopy(**deepcopy(parameters['photocopy']))(image, force=True)
        return Geometric(**deepcopy(parameters['framing']))(image, force=True)


def comparison(images, output):
    """Same relative opening-system viewport and display width per version."""
    width = 1200
    tiles = []
    for title, array in images:
        image = Image.fromarray(array).convert('RGB')
        w, h = image.size
        image = image.crop((int(w*.035), int(h*.085), int(w*.97), int(h*.30)))
        image = image.resize((width, round(image.height * width / image.width)), Image.Resampling.LANCZOS)
        tile = Image.new('RGB', (width + 40, image.height + 65), 'white')
        draw = ImageDraw.Draw(tile)
        draw.text((20, 12), title, fill='#24352d', font=ImageFont.load_default(size=22))
        tile.paste(image, (20, 50))
        tiles.append(tile)
    board = Image.new('RGB', (width + 40, sum(t.height for t in tiles)), '#eeeeee')
    y = 0
    for tile in tiles:
        board.paste(tile, (0, y))
        y += tile.height
    board.save(output)


def preview(pdf, page=1, seed=42, profiles=None, render_dpi=300, scan_profile=None):
    """Rasterize and simulate in memory; temporary raster files are cleaned up."""
    pdf = Path(pdf).resolve()
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    if page < 1 or render_dpi <= 0:
        raise ValueError('page and render_dpi must be positive')
    profiles = PROFILES if profiles is None else profiles
    if scan_profile is not None and 'library-scan' in profiles:
        raise ValueError('library-scan is reserved when scan_profile is supplied')
    # Export names are filenames, not paths. Validate before processing a page.
    for name in profiles:
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in name) or name in ('clean', 'comparison', 'manifest'):
            raise ValueError(f'invalid or reserved profile name: {name!r}')
    with tempfile.TemporaryDirectory(prefix='musvit-scan-') as directory:
        prefix = Path(directory) / 'clean'
        subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page),
                        '-singlefile', '-r', str(render_dpi), '-gray', '-png', str(pdf), str(prefix)], check=True)
        with Image.open(prefix.with_suffix('.png')) as image:
            source = np.array(image.convert('L'))
    manifest = dict(schema_version=3, backend='augraphy',
                    augraphy_version=version('augraphy'),
                    source=str(pdf), page=page,
                    source_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
                    render_dpi=render_dpi, seed=seed, dimensions=list(source.shape[::-1]),
                    status='experimental; inspect notation legibility before training', variants={})
    variants = {}
    for index, (name, profile) in enumerate(profiles.items()):
        variant_seed = seed + index
        result = bad_photocopy(source, profile, variant_seed)
        variants[name] = result
        manifest['variants'][name] = dict(augmentation='BadPhotoCopy',
                                         parameters=deepcopy(profile), seed=variant_seed,
                                         dimensions=list(result.shape[::-1]), geometry='unchanged')
    if scan_profile is not None:
        # Keep the user-reviewed library scan stable as other profiles change.
        variant_seed = seed + 3
        result = library_scan(source, scan_profile, variant_seed)
        variants['library-scan'] = result
        manifest['variants']['library-scan'] = dict(
            augmentation=['Geometric', 'PageBorder', 'BadPhotoCopy', 'Geometric'],
            parameters=deepcopy(scan_profile), seed=variant_seed,
            dimensions=list(result.shape[::-1]),
            geometry='changed: border, padding and rotation; source coordinate mapping not exported')
    return source, variants, manifest


def export_preview(source, variants, manifest, output):
    """Save exactly the inspected preview; refuse to overwrite an existing run."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    Image.fromarray(source).save(output / 'clean.png')
    for name, array in variants.items():
        Image.fromarray(array).save(output / f'{name}.png')
    comparison([('Clean reference', source), *variants.items()], output / 'comparison.png')
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return output.resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent / 'outputs')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--page', type=int, default=1)
    parser.add_argument('--library-scan', action='store_true',
                        help='also preview a framed, rotated sheet with dark scanner edges')
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f'refusing to overwrite {args.output}; choose a new --output directory')
    print(export_preview(*preview(args.pdf, args.page, args.seed,
                                  scan_profile=LIBRARY_SCAN if args.library_scan else None), args.output))


if __name__ == '__main__':
    main()
