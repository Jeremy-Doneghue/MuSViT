"""Seeded complete pages for a source-disjoint clean recognition baseline."""

import argparse
from collections import Counter
from dataclasses import asdict
from fractions import Fraction
import hashlib
from importlib.util import find_spec
import json
from pathlib import Path
import random
import xml.etree.ElementTree as ET

from PIL import Image

from .codec_fixtures import add, direction, note, notation, score, xml
from .pilot_data import PilotDataset, sha256
from .score_codec import PROFILE, VOCABULARY, VOCABULARY_SHA256, decode, encode_with_metadata
from .score_semantics import inspect_score


SPLITS = ("train", "validation", "test")
KINDS = ("horn", "piano", "drums")
RENDER_OPTIONS = dict(inputFrom="musicxml", breaks="encoded", pageWidth=2100,
                      pageHeight=2970, scale=55, header="none", footer="none",
                      justifyVertically=True, spacingSystem=12)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def composition_seed(seed, split, index):
    if split not in SPLITS:
        raise ValueError("unknown split")
    return int(digest(["clean-page-v1", seed, split, index])[:15], 16)


def make_score(seed, kind):
    """Independent random compositions, never transformations of pilot examples.

    A deliberately limited 4/4, C-major distribution; features are shared across
    splits, compositions are not. No reserved scenario feature pairs are used.
    """
    if kind not in KINDS:
        raise ValueError("unknown instrument kind")
    rng = random.Random(seed)
    root, part, first = score("", {"horn": "Horn", "piano": "Piano", "drums": "Drums"}[kind],
                              2 if kind == "piano" else 1)
    for tag in ("work", "identification", "credit"):
        root.remove(root.find(tag))
    count, per_system = (8, 2) if kind == "piano" else (16, 4)
    position = rng.randint(2, 8)
    rhythms = ((1, 1, 1, 1), (2, 1, 1), (1, .5, .5, 1, 1),
               (.5, .5, 1, .5, .5, 1), (1.5, .5, 2))
    for index in range(count):
        bar = first if index == 0 else add(part, "measure", number=index + 1)
        bar.set("id", f"m{index + 1}")
        if index and index % per_system == 0:
            add(bar, "print", **{"new-system": "yes"})
        if index % per_system == 0:
            direction(bar, "rehearsal", chr(65 + index // per_system))
            _, marking = direction(bar, "dynamics")
            add(marking, rng.choice(("p", "mf", "f")))
            if kind == "drums":
                direction(bar, "words", rng.choice(("BRUSHES", "STICKS", "RIDE CYM.", "LIGHT SWING")))
        if kind == "horn":
            nodes = []
            for duration in rng.choice(rhythms):
                position = max(0, min(12, position + rng.choice((-2, -1, 0, 1, 2))))
                node = timed_note(bar, "CDEFGAB"[position % 7], 4 + position // 7,
                                  duration, rest=rng.random() < .12)
                nodes.append(node)
            sounding = [n for n in nodes if n.find("rest") is None]
            if len(sounding) >= 2 and rng.random() < .35:
                notation(sounding[0], "slur", type="start", number=1)
                notation(sounding[-1], "slur", type="stop", number=1)
            elif sounding and rng.random() < .5:
                add(notation(rng.choice(sounding), "articulations"), rng.choice(("accent", "staccato", "tenuto")))
        elif kind == "piano":
            # Chordal melody and an independent sustained inner voice on staff 1,
            # plus a separately timed bass voice on staff 2.
            for duration in rng.choice(rhythms[:3]):
                position = rng.randint(0, 6)
                timed_note(bar, "CDEFGAB"[position], 5, duration)
                if rng.random() < .5:
                    upper = position + 2
                    timed_note(bar, "CDEFGAB"[upper % 7], 5 + upper // 7, duration, chord=True)
            add(add(bar, "backup"), "duration", 48)
            timed_note(bar, rng.choice("CDEFGAB"), 4, 4, voice=2)
            add(add(bar, "backup"), "duration", 48)
            for duration in rng.choice(((2, 2), (1, 1, 2), (4,))):
                timed_note(bar, rng.choice("CDEFGAB"), rng.choice((2, 3)), duration, voice=3, staff=2)
        else:
            for duration in rng.choice(rhythms):
                timed_note(bar, rng.choice(("G", "A")), 5, duration, unpitched=True, head="x")
            add(add(bar, "backup"), "duration", 48)
            for duration in rng.choice(((1, 1, 1, 1), (2, 2), (1, .5, .5, 2))):
                timed_note(bar, rng.choice(("F", "C")), 4, duration, voice=2,
                           unpitched=True, rest=rng.random() < .3)
        if index == count - 1:
            add(add(bar, "barline", location="right"), "bar-style", "light-heavy")
    return xml(root)


def timed_note(bar, step, octave, duration, **kwargs):
    kind, dots = {4: ("whole", 0), 2: ("half", 0), 1.5: ("quarter", 1),
                  1: ("quarter", 0), .5: ("eighth", 0)}[duration]
    return note(bar, step, octave, Fraction(duration), kind, dots=dots, **kwargs)


def musical_fingerprint(source):
    """Ignore source IDs, text/layout and global pitch transposition.

    Reject a transposed/layout/text variant of the same event sequence across
    splits as well as byte-identical sources. Partial quotations, reordered
    passages and other musical variations are not detected by this check.
    """
    parts = []
    for part in inspect_score(source)["parts"]:
        base, measures = None, []
        for bar in part["measures"]:
            events = []
            for e in bar["events"]:
                p = e["pitch"]
                if p is None or p[0] == "unpitched":
                    pitch = p
                else:
                    absolute = int(p[2]) * 7 + "CDEFGAB".index(p[0])
                    if base is None:
                        base = absolute
                    pitch = (absolute - base, p[1])
                events.append((e["onset"], e["duration"], e["voice"], e["staff"], pitch, e["chord"]))
            measures.append((bar["length"], events))
        parts.append((measures, part["playback"]))
    return digest(parts)


def check_disjoint(records):
    """Fail closed on cross-split source/family/target/raster collisions."""
    for field in ("composition_id", "family_id", "musical_fingerprint", "target_sha256", "image_sha256"):
        seen = {}
        for record in records:
            if record["split"] not in SPLITS:
                raise ValueError("unknown split")
            key = record[field]
            if key in seen and seen[key] != record["split"]:
                raise ValueError(f"cross-split {field} collision")
            seen[key] = record["split"]
    if len({r["name"] for r in records}) != len(records):
        raise ValueError("duplicate record name")


def export_dataset(output, seed=71, train_count=36, validation_count=6, test_count=6, max_tokens=8192):
    import verovio
    from cairosvg import svg2png
    from .font_resources import outline_text

    counts = (train_count, validation_count, test_count)
    if any(n < 3 or n % 3 for n in counts):
        raise ValueError("each split must have a positive multiple of three pages")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    text_font = Path(find_spec("matplotlib").origin).parent / "mpl-data/fonts/ttf/DejaVuSerif.ttf"
    records = []
    for split, count in zip(SPLITS, counts):
        for i in range(count):
            kind = KINDS[i % 3]
            page_seed = composition_seed(seed, split, i)
            source = make_score(page_seed, kind)
            encoded = encode_with_metadata(source)
            if len(encoded.tokens) > max_tokens:
                raise ValueError("target exceeds preregistered token cap; do not truncate")
            if inspect_score(source) != inspect_score(decode(encoded.tokens)):
                raise ValueError("semantic round trip failed")
            name = f"{split}_{i:03d}_{kind}"
            folder = output / name
            folder.mkdir()
            (folder / "source.musicxml").write_text(source)
            (folder / "target.json").write_text(json.dumps(asdict(encoded), ensure_ascii=False, indent=2))
            toolkit = verovio.toolkit()
            toolkit.setOptions(RENDER_OPTIONS)
            toolkit.resetXmlIdSeed(0)
            if not toolkit.loadData(source) or toolkit.getPageCount() != 1:
                raise ValueError(f"composition must fit one complete page: {name}")
            svg = toolkit.renderToSVG(1).replace('overflow="inherit"', 'overflow="visible"')
            tree = ET.fromstring(svg)
            visible = {n.get("id") for n in tree.iter()}
            measures = [m.get("id") for m in ET.fromstring(source).findall("part/measure")]
            if not set(measures) <= visible:
                raise ValueError("renderer omitted source measures")
            systems = sum("system" in n.get("class", "").split() for n in tree.iter())
            svg, _ = outline_text(svg, text_font, text_font, output / "text_fonts", "Leipzig")
            (folder / "page.svg").write_text(svg)
            svg2png(bytestring=svg.encode(), write_to=str(folder / "page.png"), output_width=1400,
                    background_color="white")
            with Image.open(folder / "page.png") as image:
                dimensions = list(image.size)
            composition_id = hashlib.sha256(source.encode()).hexdigest()
            records.append(dict(name=name, kind=kind, split=split, seed=page_seed,
                                composition_id=composition_id, family_id=digest(["family", page_seed]),
                                musical_fingerprint=musical_fingerprint(source), page=1, total_pages=1,
                                written_measures=measures, systems=systems, dimensions=dimensions,
                                target_length=len(encoded.tokens), image=f"{name}/page.png",
                                source=f"{name}/source.musicxml", target=f"{name}/target.json",
                                image_sha256=sha256(folder / "page.png"), source_sha256=sha256(folder / "source.musicxml"),
                                target_sha256=sha256(folder / "target.json"),
                                inherited_context="self-contained complete composition"))
            print(json.dumps(dict(exported=name, measures=len(measures), systems=systems,
                                  tokens=len(encoded.tokens))), flush=True)
    check_disjoint(records)
    summary = {split: dict(count=sum(r["split"] == split for r in records),
                           kinds=dict(Counter(r["kind"] for r in records if r["split"] == split)),
                           token_min=min(r["target_length"] for r in records if r["split"] == split),
                           token_max=max(r["target_length"] for r in records if r["split"] == split)) for split in SPLITS}
    manifest = dict(schema_version=1, recipe="clean-page-v1", seed=seed, profile=PROFILE,
                    vocabulary_sha256=VOCABULARY_SHA256, renderer=toolkit.getVersion(),
                    render_options=RENDER_OPTIONS, max_tokens=max_tokens,
                    source_hashes={p.name: sha256(p) for p in (Path(__file__), Path(__file__).with_name("score_codec.py"),
                                   Path(__file__).with_name("codec_fixtures.py"))},
                    purpose="source-disjoint clean synthetic baseline; not real-scan validation",
                    split_policy="independent seed domains; no variants; same feature distribution in each split",
                    summary=summary, records=records)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (output / "vocabulary.json").write_text(json.dumps(VOCABULARY, ensure_ascii=False, indent=2))
    return manifest


class CleanPageDataset(PilotDataset):
    def __init__(self, directory, split, resolution=1024):
        super().__init__(directory, resolution, split=split)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=71)
    parser.add_argument("--train-count", type=int, default=36)
    parser.add_argument("--validation-count", type=int, default=6)
    parser.add_argument("--test-count", type=int, default=6)
    args = parser.parse_args()
    print(json.dumps(export_dataset(**vars(args))["summary"], indent=2))
