"""Clean, complete single-page image/score pairs for an in-sample overfit check.

No continuation-page slicing, held-out evaluation, augmentation, or scan data.
"""

from dataclasses import asdict
import hashlib
from importlib.util import find_spec
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image
import torch

from .codec_fixtures import add, direction, drums, note, notation, piano, score, xml
from .score_codec import PROFILE, VOCABULARY, VOCABULARY_SHA256, decode, encode_with_metadata
from .score_semantics import inspect_score


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pilot_scores():
    """Eight distinct complete compositions, deliberately tiny and readable."""
    result = []
    for index, pitches in enumerate(("CDEF", "CEGC", "DFAD", "EFGA")):
        root, _, bar = score("", "Horn")
        if index == 2:
            _, dynamic = direction(bar, "dynamics")
            add(dynamic, "mf")
        if index == 3:
            direction(bar, "words", "SOLO")
        for position, pitch in enumerate(pitches):
            node = note(bar, pitch, octave=5 if position == 3 and index == 1 else 4)
            if index == 2 and position == 0:
                add(notation(node, "articulations"), "accent")
        result.append((f"horn_{index}", root))
    for index in range(2):
        root = ET.fromstring(piano().source)
        if index:
            for pitch in root.findall(".//pitch/step"):
                pitch.text = {"C": "D", "E": "F", "D": "E", "G": "A"}[pitch.text]
        result.append((f"piano_{index}", root))
    for index in range(2):
        root = ET.fromstring(drums().source)
        words = root.findall(".//words")
        words[0].text, words[1].text = ("STICKS", "CRASH") if index else ("BRUSHES", "RIDE")
        if index:
            for location in root.findall(".//unpitched/display-step"):
                if location.text == "G":
                    location.text = "A"
        result.append((f"drums_{index}", root))
    for name, root in result:
        # These fields are not drawn by the simple renderer's header. Do not
        # ask the image recognizer to recover invisible arbitrary metadata.
        for tag in ("work", "identification", "credit"):
            for child in list(root.findall(tag)):
                root.remove(child)
        for index, bar in enumerate(root.findall("part/measure"), 1):
            bar.set("id", f"m{index}")
        yield name, xml(root)


def export_pilot(output):
    import verovio
    from cairosvg import svg2png
    from .font_resources import outline_text

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    text_font = Path(find_spec("matplotlib").origin).parent / "mpl-data/fonts/ttf/DejaVuSerif.ttf"
    records = []
    for name, source in pilot_scores():
        encoded = encode_with_metadata(source)
        if inspect_score(source) != inspect_score(decode(encoded.tokens)):
            raise ValueError(f"semantic round trip failed: {name}")
        folder = output / name
        folder.mkdir()
        (folder / "source.musicxml").write_text(source, encoding="utf-8")
        (folder / "target.json").write_text(json.dumps(asdict(encoded), ensure_ascii=False, indent=2))
        toolkit = verovio.toolkit()
        toolkit.setOptions({"inputFrom": "musicxml", "breaks": "encoded" if "<print" in source else "auto",
                            "pageWidth": 2100, "pageHeight": 2970, "scale": 40,
                            "header": "none", "footer": "none"})
        if not toolkit.loadData(source) or toolkit.getPageCount() != 1:
            raise ValueError(f"pilot requires a complete single-page composition: {name}")
        svg = toolkit.renderToSVG(1).replace('overflow="inherit"', 'overflow="visible"')
        visible = {n.get("id") for n in ET.fromstring(svg).iter()}
        measures = [m.get("id") for m in ET.fromstring(source).findall("part/measure")]
        if not set(measures) <= visible:
            raise ValueError(f"renderer omitted measures: {name}")
        svg, _ = outline_text(svg, text_font, text_font, output / "text_fonts", "Leipzig")
        (folder / "page.svg").write_text(svg, encoding="utf-8")
        svg2png(bytestring=svg.encode(), write_to=str(folder / "page.png"), output_width=1400,
                background_color="white")
        with Image.open(folder / "page.png") as image:
            dimensions = list(image.size)
        records.append(dict(composition_id=hashlib.sha256(source.encode()).hexdigest(), name=name,
                            split="overfit_train", page=1, total_pages=1, written_measures=measures,
                            image=f"{name}/page.png", source=f"{name}/source.musicxml", target=f"{name}/target.json",
                            image_sha256=sha256(folder / "page.png"), source_sha256=sha256(folder / "source.musicxml"),
                            target_sha256=sha256(folder / "target.json"), dimensions=dimensions,
                            target_length=len(encoded.tokens), inherited_context="self-contained first page"))
    source_hashes = {p.name: sha256(p) for p in (Path(__file__), Path(__file__).with_name("score_codec.py"),
                                               Path(__file__).with_name("codec_fixtures.py"))}
    manifest = dict(schema_version=1, purpose="in-sample pipeline diagnostic; no generalization claim",
                    profile=PROFILE, vocabulary_sha256=VOCABULARY_SHA256, renderer=toolkit.getVersion(),
                    source_hashes=source_hashes, records=records)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (output / "vocabulary.json").write_text(json.dumps(VOCABULARY, ensure_ascii=False, indent=2))
    return manifest


class PilotDataset(torch.utils.data.Dataset):
    """Batch-size-one adapter with explicit, correctly shifted token labels."""

    def __init__(self, directory, resolution=1024, limit=None):
        self.directory = Path(directory)
        manifest = json.loads((self.directory / "manifest.json").read_text())
        if manifest["profile"] != PROFILE or manifest["vocabulary_sha256"] != VOCABULARY_SHA256:
            raise ValueError("dataset codec/vocabulary mismatch")
        self.records = manifest["records"][:limit]
        if not self.records or len({r["composition_id"] for r in self.records}) != len(self.records):
            raise ValueError("empty or duplicate pilot compositions")
        self.resolution = resolution
        self.samples = []
        for record in self.records:
            if record["page"] != 1 or record["total_pages"] != 1 or record["split"] != "overfit_train":
                raise ValueError("pilot only supports complete single-page training scores")
            for key in ("image", "source", "target"):
                if sha256(self.directory / record[key]) != record[key + "_sha256"]:
                    raise ValueError(f"dataset {key} hash mismatch")
            target = json.loads((self.directory / record["target"]).read_text())
            if target["profile"] != PROFILE or target["vocabulary_sha256"] != VOCABULARY_SHA256:
                raise ValueError("target codec mismatch")
            decoded = decode(target["tokens"])
            source = (self.directory / record["source"]).read_text()
            if inspect_score(decoded) != inspect_score(source):
                raise ValueError("image/source target semantic mismatch")
            with Image.open(self.directory / record["image"]) as image:
                # Match the existing OMR path: plain RGB [0,1], square resize.
                image = image.convert("RGB").resize((resolution, resolution), Image.Resampling.BILINEAR)
                tensor = torch.from_numpy(np.array(image, dtype=np.float32) / 255).permute(2, 0, 1).unsqueeze(0)
            self.samples.append((tensor, torch.tensor(target["tokens"], dtype=torch.long)))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        image, tokens = self.samples[index]
        return image, tokens[:-1].unsqueeze(0), tokens[1:].unsqueeze(0)
