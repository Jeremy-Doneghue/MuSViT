"""Local, immutable curriculum previews. Never modifies training exports or reviews."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import threading
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
    dict(id="2", title="Systems & pages", description="Complete generated pages with several systems, dynamics and rehearsal marks.", examples=["horn_page", "piano_page", "drums_page"], focus="Density, system order and small symbols", mix="30% clean · 40% mild · 30% moderate"),
    dict(id="3", title="Notation & voices", description="Focused examples of piano voices, cross-staff beaming and drum notation. These fixtures illustrate only part of the proposed stage.", examples=["piano", "cross_staff", "drums"], focus="Voices, staff attachment and noteheads", mix="30% clean · 40% mild · 30% moderate"),
    dict(id="4", title="Real scans", description="Explore pages imported in Bar Review. These are source scans, not clean references or automatically verified training pairs.", examples=[], focus="Actual scan appearance and legibility", mix="Real + synthetic · proportion to be calibrated"),
]
EXAMPLES = {"note": "Single written note", "passage": "Two-bar melody", "horn_page": "Horn · full page", "piano_page": "Piano · full page", "drums_page": "Drums · full page", "piano": "Piano · independent voices", "cross_staff": "Piano · cross-staff beam", "drums": "Drums · heads & instructions"}
DEFAULTS = dict(profile="light-copy", strength=1, rotation=0, ink=0, seed=42)


def catalog():
    return dict(stages=STAGES, examples=EXAMPLES, defaults=DEFAULTS,
                effects=recipes.EFFECTS, recipe_presets=recipes.PRESETS,
                profiles=["clean", "light-copy", "library-scan"], status="Proposed curriculum · exploration only")


def preview_isolated(data, payload, documents):
    """Keep native renderer state and fatal C++ errors out of the HTTP server.

    Each invocation gets its own main thread, resource initialization and RNG.
    A normal thread lock cannot contain a native abort or repair thread-local
    renderer initialization between HTTP request threads.
    """
    with tempfile.TemporaryDirectory(prefix="musvit-preview-worker-") as temp:
        result_path = Path(temp) / "result.json"
        try:
            process = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--worker",
                 str(Path(data).resolve()), str(result_path)],
                input=json.dumps(dict(payload=payload, documents=documents)),
                text=True, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("Preview generation exceeded 120 seconds. Try a simpler example; the server is still running.") from error
        if process.returncode != 0:
            detail = (process.stderr or process.stdout).strip()[-4000:]
            raise RuntimeError(f"Preview renderer failed (exit {process.returncode}). The server is still running.\n{detail}")
        if not result_path.is_file():
            raise RuntimeError("Preview worker finished without a result. The server is still running.")
        return json.loads(result_path.read_text())


def integer(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not float(value).is_integer() or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}")
    return int(value)


def settings(payload):
    if not isinstance(payload, dict):
        raise ValueError("Expected settings object")
    if 'recipe' in payload:
        return dict(seed=integer(payload.get('seed',42),0,2**31-1,'Augmentation seed'),
                    recipe=recipes.validate(payload['recipe']))
    value = {**DEFAULTS, **payload}
    if value["profile"] not in ("clean", "light-copy", "library-scan"):
        raise ValueError("Unknown scan profile")
    return dict(profile=value["profile"], strength=integer(value["strength"], 0, 3, "Copy strength"),
                rotation=integer(value["rotation"], -3, 3, "Rotation"),
                ink=integer(value["ink"], 0, 3, "Ink spread"),
                seed=integer(value["seed"], 0, 2**31-1, "Augmentation seed"))


def synthetic(example, seed, font, folder):
    from experiments.full_page_omr.datasets.one_note_data import make_note, PITCHES
    from experiments.full_page_omr.datasets.short_staff_data import make_passage
    from experiments.full_page_omr.datasets.clean_page_data import make_score
    from experiments.full_page_omr.representation.codec_fixtures import piano, cross_staff, drums
    from experiments.full_page_omr.datasets.pilot_data import export_pilot
    if example not in EXAMPLES or font not in ("Leipzig", "Bravura", "Petaluma"):
        raise ValueError("Unknown example or font")
    seed = integer(seed, 0, 2**31-1, "Music seed")
    if example == "note":
        source = make_note(PITCHES[seed % len(PITCHES)])
    elif example == "passage":
        source = make_passage(seed)
    elif example.endswith("_page"):
        source = make_score(seed, example.removesuffix("_page"))
    else:
        source = {"piano": piano, "cross_staff": cross_staff, "drums": drums}[example]().source
    options = dict(inputFrom="musicxml", breaks="encoded", pageWidth=2100, pageHeight=2970,
                   scale=55, header="none", footer="none", justifyVertically=False, font=font)
    manifest = export_pilot(folder, scores=[("example", source)], render_options=options)
    record = manifest["records"][0]
    with Image.open(folder / record["image"]) as opened:
        image = opened.convert("RGB")
    return image, dict(kind="synthetic", example=example, music_seed=seed,
                       font=font, render_options=options, renderer=manifest['renderer'],
                       generator_source_hashes=manifest['source_hashes'],
                       source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                       split="exploration-unassigned", target_length=record["target_length"],
                       note="Fixture seeds affect note/passage/page generators; focused voice fixtures are fixed."), source


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


def augment(image, config):
    if 'recipe' in config:
        return recipes.apply(image,config['recipe'],config['seed'],rotate_antialiased)
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


def preview(data, payload, documents):
    if not isinstance(payload, dict):
        raise ValueError("Expected a preview object")
    config = settings(payload.get("settings", {}))
    stage = str(payload.get("stage", "0"))
    if stage not in {s["id"] for s in STAGES}:
        raise ValueError("Unknown stage")
    with LOCK, tempfile.TemporaryDirectory(prefix="musvit-curriculum-") as temp:
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
            image, provenance, source = synthetic(example, payload.get("music_seed", 7), payload.get("font", "Leipzig"), Path(temp) / "render")
        result, effects = augment(image, config)
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
            (folder / "source.musicxml").write_text(source)
            files["source.musicxml"] = hashlib.sha256(source.encode()).hexdigest()
        manifest = dict(schema_version=1, id=preview_id, stage=stage, created_at=datetime.now(timezone.utc).isoformat(),
                        status="exploration only; not approved training data", source=provenance, settings=config,
                        request=payload, effects=effects, augraphy_version=version("augraphy"),
                        pillow_version=version("Pillow"), numpy_version=version("numpy"),
                        preview_implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        recipe_implementation_sha256=hashlib.sha256(Path(recipes.__file__).read_bytes()).hexdigest(),
                        source_dimensions=list(image.size), augmented_dimensions=list(result.size),
                        augmented_png_mode='1-bit' if binary_export else 'RGB',
                        geometry="changed; coordinate mapping unavailable" if any(e.get('geometry_changed',False) for e in effects) or config.get("rotation") or config.get("profile") == "library-scan" else "unchanged",
                        preprocessing="RGB, square 1024x1024 bilinear resize; matches current pilot (may distort aspect ratio)",
                        files=files)
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
        return manifest


def artifact(data, preview_id, filename):
    if len(preview_id) != 32 or any(c not in "0123456789abcdef" for c in preview_id):
        raise ValueError("Invalid preview ID")
    if filename not in {"source.png", "augmented.png", "source-1024.png", "augmented-1024.png", "manifest.json", "source.musicxml"}:
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


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "--worker":
        raise SystemExit("This module is launched by the Bar Review preview endpoint.")
    request = json.load(sys.stdin)
    result = preview(Path(sys.argv[2]), request["payload"], request["documents"])
    Path(sys.argv[3]).write_text(json.dumps(result))
