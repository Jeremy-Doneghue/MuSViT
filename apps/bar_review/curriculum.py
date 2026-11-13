"""Local, immutable curriculum previews. Never modifies training exports or reviews."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import threading
import time
import uuid
import zipfile

import numpy as np
from PIL import Image
import recipes

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Augraphy uses process-global RNG state. Serialize all preview work.
LOCK = threading.RLock()
STAGES = [
    dict(id="0", title="Recognition check", description="One note with staff context. Explore placement and the survival of ledger lines.", examples=["note"], focus="Pitch and staff position", mix="50% clean · 40% mild · 10% moderate"),
    dict(id="1", title="Short passages", description="Two complete bars with varied pitches and rhythms. Compare readable engraving with mild scan damage.", examples=["passage"], focus="Pitch, duration and note spacing", mix="50% clean · 40% mild · 10% moderate"),
    dict(id="2", title="Systems & pages", description="Complete generated pages with several systems, dynamics and performance text.", examples=["horn_page", "piano_page", "drums_page"], focus="Density, system order and small symbols", mix="30% clean · 40% mild · 30% moderate"),
    dict(id="3", title="Notation & voices", description="Focused examples of piano voices, cross-staff beaming and drum notation. These fixtures illustrate only part of the proposed stage.", examples=["piano", "cross_staff", "drums"], focus="Voices, staff attachment and noteheads", mix="30% clean · 40% mild · 30% moderate"),
    dict(id="4", title="Real scans", description="Explore pages imported in Bar Review. These are source scans, not clean references or automatically verified training pairs.", examples=[], focus="Actual scan appearance and legibility", mix="Real + synthetic · proportion to be calibrated"),
]
EXAMPLES = {"note": "Single written note", "passage": "Two-bar melody", "horn_page": "Horn · full page", "piano_page": "Piano · full page", "drums_page": "Drums · full page", "piano": "Piano · independent voices", "cross_staff": "Piano · cross-staff beam", "drums": "Drums · heads & instructions"}
DEFAULTS = dict(profile="light-copy", strength=1, rotation=0, ink=0, seed=42)


def catalog():
    return dict(stages=STAGES, examples=EXAMPLES, defaults=DEFAULTS,
                effects=recipes.EFFECTS, recipe_presets=recipes.PRESETS,
                profiles=["clean", "light-copy", "library-scan"], status="Proposed curriculum · exploration only")


def preview_isolated(data, payload, documents, *, progress=None, source_preview=None):
    """Keep native renderer state and fatal C++ errors out of the HTTP server.

    Each invocation gets its own main thread, resource initialization and RNG.
    A normal thread lock cannot contain a native abort or repair thread-local
    renderer initialization between HTTP request threads.
    """
    with tempfile.TemporaryDirectory(prefix="musvit-preview-worker-") as temp:
        result_path = Path(temp) / "result.json"
        progress_path = result_path.with_suffix('.progress.json')
        stop = threading.Event()

        def observe():
            previous = None
            while not stop.wait(.08):
                try:
                    value = json.loads(progress_path.read_text())
                except (OSError, ValueError):
                    continue
                if value != previous:
                    progress(value)
                    previous = value

        observer = None
        if progress:
            progress(dict(label='Starting preview worker', fraction=0.02))
            observer = threading.Thread(target=observe, daemon=True)
            observer.start()
        try:
            process = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--worker",
                 str(Path(data).resolve()), str(result_path)],
                input=json.dumps(dict(payload=payload, documents=documents, source_preview=source_preview)),
                text=True, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("Preview generation exceeded 120 seconds. Try a simpler example; the server is still running.") from error
        finally:
            stop.set()
            if observer:
                observer.join()
        if process.returncode != 0:
            detail = (process.stderr or process.stdout).strip()[-4000:]
            raise RuntimeError(f"Preview renderer failed (exit {process.returncode}). The server is still running.\n{detail}")
        if not result_path.is_file():
            raise RuntimeError("Preview worker finished without a result. The server is still running.")
        if progress:
            progress(dict(label='Preview files ready', fraction=.99))
        return json.loads(result_path.read_text())


def integer(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not float(value).is_integer() or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}")
    return int(value)


def settings(payload):
    if not isinstance(payload, dict):
        raise ValueError("Expected settings object")
    if 'recipe' in payload:
        result=dict(seed=integer(payload.get('seed',42),0,2**31-1,'Augmentation seed'),
                    recipe=recipes.validate(payload['recipe']))
        if 'preview_values' in payload:
            result['preview_values']=recipes.validate_preview_values(result['recipe'],payload['preview_values'])
        return result
    value = {**DEFAULTS, **payload}
    if value["profile"] not in ("clean", "light-copy", "library-scan"):
        raise ValueError("Unknown scan profile")
    return dict(profile=value["profile"], strength=integer(value["strength"], 0, 3, "Copy strength"),
                rotation=integer(value["rotation"], -3, 3, "Rotation"),
                ink=integer(value["ink"], 0, 3, "Ink spread"),
                seed=integer(value["seed"], 0, 2**31-1, "Augmentation seed"))


def synthetic(example, seed, font, folder):
    from experiments.full_page_omr.generation.humdrum_scores import make_score, render
    if example not in EXAMPLES:
        raise ValueError('Unknown example')
    seed = integer(seed, 0, 2**31-1, 'Music seed')
    score = make_score(example, seed)
    image, provenance = render(score, folder, font)
    provenance.update(kind='synthetic', example=example, music_seed=seed, font=font,
        generator_source_hashes={name: hashlib.sha256((ROOT/'experiments/full_page_omr'/name).read_bytes()).hexdigest()
                                for name in ['generation/humdrum_scores.py','generation/font_resources.py']},
        split='exploration-unassigned',
        note='Direct Humdrum source; SVG and MEI are derived, not model labels.')
    return image, provenance, score.source


def rotate_antialiased(image, angle):
    """Rotate at 2x resolution, then integrate edges back to source scale.

    Keep the expanded canvas and white scanner background. Zero rotation is
    pixel-exact, avoiding unnecessary filtering of the clean control.
    """
    if not angle:
        return image.copy()
    scale = 2
    enlarged = image.resize((image.width * scale, image.height * scale), Image.Resampling.BICUBIC)
    rotated = enlarged.rotate(angle, resample=Image.Resampling.BICUBIC,
                              expand=True, fillcolor="white")
    return rotated.resize(((rotated.width + scale - 1) // scale,
                           (rotated.height + scale - 1) // scale), Image.Resampling.LANCZOS)


def augment(image, config, on_step=None):
    if 'recipe' in config:
        return recipes.apply(image,config['recipe'],config['seed'],rotate_antialiased,on_step=on_step,
                             preview_values=config.get('preview_values'))
    if config['profile'] == 'clean' and not config['ink']:
        output = rotate_antialiased(image, config['rotation'])
        effects = [] if not config['rotation'] else [dict(name='AntialiasedRotation', backend='Pillow', parameters=dict(
            angle_degrees=config['rotation'], supersampling=2, upsample='bicubic', rotation_resampling='bicubic',
            downsample='lanczos', expand=True, fill='white'))]
        return output, effects
    from augraphy import InkBleed
    from experiments.scan_degradation.generate import PROFILES, LIBRARY_SCAN, bad_photocopy, library_scan, _seeded
    array = np.array(image.convert("L"))
    result = array.copy()
    effects = []
    strength = config["strength"]
    noise = [(245, 255), (190, 240), (140, 210), (80, 180)][strength]
    if config["profile"] == "light-copy":
        params = deepcopy(PROFILES["light-copy"])
        params["noise_value"] = noise
        result = bad_photocopy(result, params, config["seed"])
        effects.append(dict(name="BadPhotoCopy", parameters=params, seed=config["seed"]))
    elif config["profile"] == "library-scan":
        params = deepcopy(LIBRARY_SCAN)
        if strength != 1:
            params["photocopy"]["noise_value"] = noise
        # Rotation is controlled separately below, including for the accepted recipe.
        params["framing"]["rotate_range"] = (0, 0)
        result = library_scan(result, params, config["seed"])
        effects.append(dict(name="library-scan", parameters=params, seed=config["seed"]))
    if config["ink"]:
        level = config["ink"]
        params = dict(intensity_range=(.1*level, .2*level), kernel_size=(3, 3), severity=(.1*level, .15*level), p=1)
        with _seeded(config["seed"] + 1):
            result = InkBleed(**params)(result, force=True)
        effects.append(dict(name="InkBleed", parameters=params, seed=config["seed"] + 1))
    # Preserve source RGB in the true no-effects control.
    output = image.copy() if not effects else Image.fromarray(result).convert("RGB")
    if config["rotation"]:
        output = rotate_antialiased(output, config["rotation"])
        effects.append(dict(name="AntialiasedRotation", backend="Pillow", parameters=dict(
            angle_degrees=config["rotation"], supersampling=2, upsample="bicubic",
            rotation_resampling="bicubic", downsample="lanczos", expand=True, fill="white")))
    return output, effects


def source_fingerprint(payload):
    """Conservative source reuse key; no augmentation inputs or training data."""
    files = ['generation/humdrum_scores.py', 'generation/font_resources.py']
    value = dict(stage=str(payload.get('stage', '0')), example=payload.get('example'),
                 seed=payload.get('music_seed', 7), font=payload.get('font', 'Leipzig'),
                 implementation=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 versions={name: version(name) for name in ['verovio', 'CairoSVG', 'Pillow', 'fonttools', 'matplotlib']},
                 code={name: hashlib.sha256((ROOT/'experiments/full_page_omr'/name).read_bytes()).hexdigest()
                       for name in files})
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def reuse_source(data, preview_id, fingerprint):
    """Reuse only intact synthetic artifacts with matching source inputs/code."""
    if not preview_id:
        return None
    try:
        manifest = json.loads(artifact(data, preview_id, 'manifest.json').read_text())
        if manifest.get('source_fingerprint') != fingerprint or manifest['source']['kind'] != 'synthetic':
            return None
        png = artifact(data, preview_id, 'source.png').read_bytes()
        source = artifact(data, preview_id, 'source.krn').read_bytes()
        if any(hashlib.sha256(content).hexdigest() != manifest['files'][name]
               for name, content in [('source.png', png), ('source.krn', source)]):
            return None
        for name, digest in manifest['source'].get('derived_sha256', {}).items():
            if name not in ('source.svg', 'source.mei') or hashlib.sha256(artifact(data, preview_id, name).read_bytes()).hexdigest() != digest:
                return None
        with Image.open(io.BytesIO(png)) as image:
            return image.convert('RGB'), manifest['source'], source.decode('utf-8')
    except (OSError, ValueError, KeyError, TypeError):
        return None


def preview(data, payload, documents, *, progress=None, source_preview=None):
    started = time.perf_counter()
    timings, effect_timings = {}, []

    def report(label, fraction):
        if progress:
            progress(dict(label=label, fraction=fraction))

    def on_step(index, total, label, elapsed):
        if elapsed is None:
            report(f'Effect {index+1}/{total}: {label}', .3 + .55*index/total)
        else:
            effect_timings.append(dict(position=index, label=label, seconds=round(elapsed, 4)))

    if not isinstance(payload, dict):
        raise ValueError("Expected a preview object")
    config = settings(payload.get("settings", {}))
    stage = str(payload.get("stage", "0"))
    if stage not in {s["id"] for s in STAGES}:
        raise ValueError("Unknown stage")
    with LOCK, tempfile.TemporaryDirectory(prefix="musvit-curriculum-") as temp:
        source_started = time.perf_counter()
        source_reused = False
        fingerprint = None
        report('Loading source scan' if stage == '4' else 'Preparing source engraving', .08)
        if stage == "4":
            doc = next((d for d in documents if d["id"] == payload.get("document_id")), None)
            if doc is None:
                raise ValueError("Choose an imported document in Bar Review")
            page = next((p for p in doc["pages"] if p["number"] == payload.get("page")), None)
            if page is None:
                raise ValueError("Choose an imported page")
            with Image.open(data / doc["id"] / f"page-{page['number']}.png") as opened:
                image = opened.convert("RGB")
            source = None
            provenance = dict(kind="real-scan", document_id=doc["id"], source_sha256=doc["sha256"],
                              page=page["number"], split="exploration-unassigned", labels="unverified; no full-page transcription attached")
        else:
            example = payload.get("example", STAGES[int(stage)]["examples"][0])
            if example not in STAGES[int(stage)]["examples"]:
                raise ValueError("Example does not belong to this stage")
            fingerprint = source_fingerprint(payload)
            cached = reuse_source(data, source_preview, fingerprint)
            if cached:
                image, provenance, source = cached
                source_reused = True
                report('Reusing unchanged source engraving', .28)
            else:
                report('Generating and rendering source engraving', .12)
                image, provenance, source = synthetic(example, payload.get("music_seed", 7), payload.get("font", "Leipzig"), Path(temp) / "render")
        timings['source'] = round(time.perf_counter()-source_started, 4)
        report('Preparing scan effects (loading Augraphy if needed)', .3)
        effects_started = time.perf_counter()
        result, effects = augment(image, config, on_step=on_step)
        timings['augmentation'] = round(time.perf_counter()-effects_started, 4)
        report('Saving preview images and model inputs', .87)
        save_started = time.perf_counter()
        preview_id = uuid.uuid4().hex
        folder = data / "curriculum" / preview_id
        folder.mkdir(parents=True, exist_ok=False)
        files = {}
        binary_export = bool(effects and effects[-1]['name'] == 'BlackWhiteScan')
        for name, picture in [("source", image), ("augmented", result)]:
            native = picture.convert('1', dither=Image.Dither.NONE) if name == 'augmented' and binary_export else picture
            native.save(folder / f"{name}.png")
            picture.resize((1024, 1024), Image.Resampling.BILINEAR).save(folder / f"{name}-1024.png")
            for suffix in ("", "-1024"):
                filename = f"{name}{suffix}.png"
                files[filename] = hashlib.sha256((folder / filename).read_bytes()).hexdigest()
        if source:
            (folder / 'source.krn').write_text(source, encoding='utf-8')
            files['source.krn'] = hashlib.sha256(source.encode('utf-8')).hexdigest()
            for name, digest in provenance.get('derived_sha256', {}).items():
                if name not in ('source.svg','source.mei'):
                    raise ValueError('Unknown derived source artifact')
                original = artifact(data, source_preview, name) if source_reused else Path(temp)/'render'/name
                content = original.read_bytes()
                if hashlib.sha256(content).hexdigest() != digest:
                    raise ValueError('Derived source artifact checksum mismatch')
                (folder/name).write_bytes(content)
                files[name] = digest
        timings['save_images_and_hashes'] = round(time.perf_counter()-save_started, 4)
        timings['worker_total'] = round(time.perf_counter()-started, 4)
        report('Writing manifest', .97)
        manifest = dict(schema_version=1, id=preview_id, stage=stage, created_at=datetime.now(timezone.utc).isoformat(),
                        status="exploration only; not approved training data", source=provenance, settings=config,
                        request=payload, effects=effects, augraphy_version=version("augraphy"),
                        timings_seconds=timings, effect_timings_seconds=effect_timings,
                        source_fingerprint=fingerprint, source_reused=source_reused,
                        pillow_version=version("Pillow"), numpy_version=version("numpy"),
                        preview_implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        recipe_implementation_sha256=hashlib.sha256(Path(recipes.__file__).read_bytes()).hexdigest(),
                        source_dimensions=list(image.size), augmented_dimensions=list(result.size),
                        augmented_png_mode='1-bit' if binary_export else 'RGB',
                        geometry="changed; coordinate mapping unavailable" if any(e.get('geometry_changed',False) for e in effects) or config.get("rotation") or config.get("profile") == "library-scan" else "unchanged",
                        preprocessing="RGB, square 1024x1024 bilinear resize; matches current pilot (may distort aspect ratio)",
                        files=files)
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
        report('Preview files ready', .99)
        return manifest


def artifact(data, preview_id, filename):
    if len(preview_id) != 32 or any(c not in "0123456789abcdef" for c in preview_id):
        raise ValueError("Invalid preview ID")
    if filename not in {"source.png", "augmented.png", "source-1024.png", "augmented-1024.png", "manifest.json", "source.krn", "source.svg", "source.mei", "source.musicxml"}:
        raise ValueError("Unknown preview artifact")
    return data / "curriculum" / preview_id / filename


def export_preview(data, preview_id):
    manifest_path = artifact(data, preview_id, "manifest.json")
    manifest = json.loads(manifest_path.read_text())
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(manifest_path, "manifest.json")
        for name in manifest["files"]:
            archive.write(artifact(data, preview_id, name), name)
    return buffer.getvalue()


def write_atomic(path, value):
    staging = path.with_suffix('.tmp')
    staging.write_text(json.dumps(value))
    staging.replace(path)


def run_persistent_worker(root):
    """All imports, toolkit construction and rendering stay on this main thread."""
    write_atomic(root/'startup.progress.json', dict(label='Loading engraving dependencies', fraction=.02))
    import verovio  # noqa: F401
    import cairosvg  # noqa: F401
    from experiments.full_page_omr.generation import humdrum_scores  # noqa: F401
    write_atomic(root/'startup.progress.json', dict(label='Loading Augraphy (once per session)', fraction=.02))
    import augraphy  # noqa: F401
    write_atomic(root/'ready.json', dict(pid=os.getpid()))
    for line in sys.stdin:
        request = json.loads(line)
        identity = request['id']
        if len(identity) != 32 or any(c not in '0123456789abcdef' for c in identity):
            raise ValueError('Invalid internal preview job ID')
        progress_path = root/f'{identity}.progress.json'
        try:
            manifest = preview(Path(request['data']), request['payload'], request['documents'],
                progress=lambda value: write_atomic(progress_path, value),
                source_preview=request.get('source_preview'))
            result = dict(ok=True, manifest=manifest)
        except Exception as error:
            result = dict(ok=False, type=type(error).__name__, error=str(error))
        write_atomic(root/f'{identity}.result.json', result)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == '--persistent-worker':
        run_persistent_worker(Path(sys.argv[2]))
        raise SystemExit(0)
    if len(sys.argv) != 4 or sys.argv[1] != "--worker":
        raise SystemExit("This module is launched by the Bar Review preview endpoint.")
    request = json.load(sys.stdin)
    progress_path = Path(sys.argv[3]).with_suffix('.progress.json')

    def write_progress(value):
        write_atomic(progress_path, value)

    result = preview(Path(sys.argv[2]), request["payload"], request["documents"],
                     progress=write_progress, source_preview=request.get('source_preview'))
    Path(sys.argv[3]).write_text(json.dumps(result))
