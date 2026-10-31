"""Original synthetic score fixtures and an inspectable codec/render validation CLI.

No scan transcriptions or datasets. Outputs require a new directory.
"""

import argparse
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from .score_codec import PROFILE, VOCABULARY, VOCABULARY_SHA256, canonicalize, decode, encode, encode_with_metadata
from .score_semantics import inspect_score


def add(parent, tag, text=None, **attrs):
    child = ET.SubElement(parent, tag, {key: str(value) for key, value in attrs.items()})
    child.text = None if text is None else str(text)
    return child


def score(title, instrument, staves=1):
    root = ET.Element("score-partwise", version="4.0")
    add(add(root, "work"), "work-title", title)
    identity = add(root, "identification")
    add(identity, "creator", "Zoë — Fixture Composer", type="composer")
    add(identity, "creator", "Fixture Arranger", type="arranger")
    add(identity, "rights", "Original synthetic fixture © 2026")
    add(add(identity, "miscellaneous"), "miscellaneous-field", "LIB-364", name="library-reference")
    add(add(root, "credit"), "credit-words", title)
    definition = add(add(root, "part-list"), "score-part", id="source-part")
    add(definition, "part-name", instrument)
    part = add(root, "part", id="source-part")
    bar = add(part, "measure", number="1", id="source-bar-1")
    attributes = add(bar, "attributes")
    add(attributes, "divisions", 12)
    add(add(attributes, "key"), "fifths", 0)
    time = add(attributes, "time")
    add(time, "beats", 4)
    add(time, "beat-type", 4)
    if staves > 1:
        add(attributes, "staves", staves)
    for staff in range(1, staves + 1):
        clef = add(attributes, "clef", **({"number": staff} if staves > 1 else {}))
        add(clef, "sign", "percussion" if instrument == "Drums" else ("F" if staff == 2 else "G"))
        if instrument != "Drums":
            add(clef, "line", 4 if staff == 2 else 2)
    return root, part, bar


def note(bar, step="C", octave=4, length=1, kind="quarter", voice=1, staff=1,
         dots=0, chord=False, rest=False, unpitched=False, head=None, alter=None, cue=False):
    node = add(bar, "note")
    if cue:
        add(node, "cue")
    if chord:
        add(node, "chord")
    if rest:
        add(node, "rest")
    else:
        pitch = add(node, "unpitched" if unpitched else "pitch")
        add(pitch, "display-step" if unpitched else "step", step)
        if alter is not None and not unpitched:
            add(pitch, "alter", alter)
        add(pitch, "display-octave" if unpitched else "octave", octave)
    duration = Fraction(length) * 12
    assert duration.denominator == 1
    add(node, "duration", int(duration))
    add(node, "voice", voice)
    add(node, "type", kind)
    for _ in range(dots):
        add(node, "dot")
    if alter not in (None, 0):
        add(node, "accidental", {1: "sharp", -1: "flat", 2: "double-sharp", -2: "flat-flat"}[alter])
    if head:
        add(node, "notehead", head)
    add(node, "staff", staff)
    return node


def direction(bar, tag, text=None, staff=1, **attrs):
    node = add(bar, "direction", placement="above")
    marker = add(add(node, "direction-type"), tag, text, **attrs)
    add(node, "staff", staff)
    return node, marker


def notation(node, tag, **attrs):
    container = node.find("notations")
    if container is None:
        container = add(node, "notations")
    return add(container, tag, **attrs)


def tie(node, kind):
    # Sounding tie belongs before voice/type; notation belongs at the end.
    node.insert(2, ET.Element("tie", type=kind))
    notation(node, "tied", type=kind)


def xml(root):
    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


@dataclass
class Fixture:
    name: str
    source: str
    playback: list[str]
    note_count: int
    description: str


def horn():
    root, part, bar = score("Horn: text, dots and spans", "Tenor 2 (B♭)")
    direction(bar, "rehearsal", "A")
    direction(bar, "words", "Solo — café <end> & cue")
    metronome, marking = direction(bar, "metronome")
    add(marking, "beat-unit", "quarter")
    add(marking, "per-minute", 160)
    add(metronome, "sound", tempo=160)
    _, dynamic = direction(bar, "dynamics")
    add(dynamic, "mf")
    direction(bar, "wedge", type="crescendo", number=1)
    first = note(bar, "F", length=Fraction(7, 4), dots=2, alter=1)
    notation(first, "slur", type="start", number=1)
    notation(first, "glissando", type="start", number=1)
    add(notation(first, "articulations"), "accent")
    second = note(bar, "G", length=Fraction(1, 4), kind="16th")
    notation(second, "glissando", type="stop", number=1)
    last = note(bar, "G", length=2, kind="half")
    tie(last, "start")
    direction(bar, "wedge", type="stop", number=1)
    bar = add(part, "measure", number=2)
    add(bar, "print", **{"new-page": "yes"})
    continued = note(bar, "G", length=2, kind="half")
    tie(continued, "stop")
    for index, pitch in enumerate(("A", "B", "C")):
        triplet = note(bar, pitch, octave=5, length=Fraction(1, 3), kind="eighth")
        modification = ET.Element("time-modification")
        add(modification, "actual-notes", 3)
        add(modification, "normal-notes", 2)
        triplet.insert(list(triplet).index(triplet.find("staff")), modification)
        if index in (0, 2):
            notation(triplet, "tuplet", type="start" if index == 0 else "stop", number=1, bracket="yes")
    notation(triplet, "slur", type="stop", number=1)
    notation(triplet, "fermata")
    add(notation(triplet, "articulations"), "falloff")
    note(bar, rest=True)
    direction(bar, "words", "Tacet after this phrase; rit.")
    add(add(bar, "barline", location="right"), "bar-style", "light-heavy")
    return Fixture("horn", xml(root), ["1", "2"], 8, "Double dot, tuplet, tie, slur/gliss, fall, metadata and arbitrary Unicode text")


def piano():
    root, part, bar = score("Piano: independent voices", "Piano", 2)
    direction(bar, "pedal", staff=2, type="start")
    note(bar, octave=5, length=2, kind="half")
    note(bar, "E", octave=5, length=2, kind="half", chord=True)
    note(bar, "D", octave=5, length=2, kind="half")
    add(add(bar, "backup"), "duration", 48)
    note(bar, "G", length=4, kind="whole", voice=2)
    add(add(bar, "backup"), "duration", 48)
    note(bar, octave=3, length=4, kind="whole", voice=3, staff=2)
    direction(bar, "pedal", staff=2, type="stop")
    return Fixture("piano", xml(root), ["1"], 5, "Chord, two independent upper-staff voices, bass voice and pedal")


def cross_staff():
    root, _, bar = score("Piano: cross-staff voice", "Piano", 2)
    for i, (pitch, octave, staff) in enumerate((("C", 4, 2), ("E", 4, 2), ("G", 4, 1), ("C", 5, 1))):
        node = note(bar, pitch, octave, Fraction(1, 2), "eighth", staff=staff)
        add(node, "beam", "begin" if i == 0 else "end" if i == 3 else "continue", number=1)
    note(bar, length=2, kind="half", rest=True)
    add(add(bar, "backup"), "duration", 48)
    note(bar, "C", 3, 4, "whole", voice=2, staff=2)
    return Fixture("cross_staff", xml(root), ["1"], 6, "One beamed voice changes staff without changing voice identity")


def drums():
    root, part, bar = score("Drums: notation and instructions", "Drums")
    direction(bar, "words", "BRUSHES — light swing")
    direction(bar, "rehearsal", "12")
    for _ in range(4):
        note(bar, "G", 5, unpitched=True, head="x")
    add(add(bar, "backup"), "duration", 48)
    note(bar, "F", 4, 2, "half", voice=2, unpitched=True)
    note(bar, "F", 4, 2, "half", voice=2, rest=True)
    bar = add(part, "measure", number=2)
    add(bar, "print", **{"new-system": "yes"})
    direction(bar, "words", "RIDE CYM. / B.D. on 1; fill →")
    note(bar, "G", 5, 4, "whole", unpitched=True, head="x")
    return Fixture("drums", xml(root), ["1", "2"], 7, "Unpitched mixed heads, independent rhythm and changing passage instructions; no sound mappings")


def alternatives():
    root, part, bar = score("Conditional passages — normalized", "Tenor saxophone")
    direction(bar, "words", "Intro — once")
    note(bar, length=4, kind="whole")
    for number, pitch, ending in ((2, "D", 1), (4, "E", 2)):
        for offset in range(2):
            bar = add(part, "measure", number=number + offset)
            if (ending, offset) == (2, 0):
                add(bar, "print", **{"new-page": "yes"})
            if offset == 0:
                left = add(bar, "barline", location="left")
                add(left, "ending", number=ending, type="start")
                if ending == 1:
                    add(left, "repeat", direction="forward")
                direction(bar, "words", "First pass" if ending == 1 else "Second pass")
            first = note(bar, pitch, length=2, kind="half")
            if offset == 0:
                notation(first, "slur", type="start", number=1)
            last = note(bar, "G", length=2, kind="half")
            if offset == 1:
                notation(last, "slur", type="stop", number=1)
                right = add(bar, "barline", location="right")
                add(right, "ending", number=ending, type="stop" if ending == 1 else "discontinue")
                if ending == 1:
                    add(right, "repeat", direction="backward", times=2)
    bar = add(part, "measure", number=6)
    direction(bar, "words", "Common continuation")
    note(bar, "A", length=4, kind="whole")
    return Fixture("alternatives", xml(root), ["1", "2", "3", "4", "5", "6"], 10,
                   "Intro once, pass-specific branches and shared continuation across pages; not a Charmaine transcription or historical layout replica")


def fixtures():
    from .generate_parts import make_part
    from .musicxml_score import to_musicxml
    result = [horn(), piano(), cross_staff(), drums(), alternatives()]
    for scenario in ("repeat", "endings", "ds_coda"):
        part = make_part(seed=7, scenario=scenario)
        result.append(Fixture("generated_" + scenario, to_musicxml(part),
                              [mid.removeprefix("m") for mid in part.playback],
                              sum(len(m.events) for m in part.measures),
                              "Existing seed-7 regression with written abbreviations, harmony/slashes and navigation"))
    return result


def validate_fixture(fixture):
    encoded = encode_with_metadata(fixture.source)
    decoded = decode(encoded.tokens)
    before, after = inspect_score(fixture.source), inspect_score(decoded)
    assert before == after, fixture.name + ": score semantics changed"
    assert encode(decoded) == encoded.tokens
    assert decoded == canonicalize(fixture.source)
    part = after["parts"][0]
    assert part["playback"] == fixture.playback, (fixture.name, part["playback"], fixture.playback)
    assert sum(len(bar["events"]) for bar in part["measures"]) == fixture.note_count
    return decoded, encoded, after


def validate_all(output, png=False):
    """Export review artifacts to a new directory; never overwrite an export."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    import verovio
    results = []
    for fixture in fixtures():
        decoded, encoded, semantics = validate_fixture(fixture)
        folder = output / fixture.name
        folder.mkdir()
        (folder / "source.musicxml").write_text(fixture.source)
        (folder / "decoded.musicxml").write_text(decoded)
        (folder / "tokens.json").write_text(json.dumps(asdict(encoded), ensure_ascii=False, indent=2))
        (folder / "semantics.json").write_text(json.dumps(semantics, ensure_ascii=False, indent=2))
        pages = []
        for label, source in (("source", fixture.source), ("decoded", decoded)):
            toolkit = verovio.toolkit()
            input_format = "musicxml"
            if fixture.name.startswith("generated_"):
                from .musicxml_score import musicxml_to_mei, normalize_mei, check_conversion
                converted = normalize_mei(source, musicxml_to_mei(source))
                check_conversion(source, converted)
                source, input_format = converted, "mei"
            toolkit.setOptions({"inputFrom": input_format, "pageWidth": 2100, "pageHeight": 2970,
                                "scale": 40, "breaks": "encoded" if "<print" in fixture.source else "auto",
                                "header": "encoded", "footer": "none"})
            if not toolkit.loadData(source):
                raise ValueError(f"renderer rejected {fixture.name}/{label}")
            count = toolkit.getPageCount()
            pages.append(count)
            for page in range(1, count + 1):
                svg = toolkit.renderToSVG(page).replace('overflow="inherit"', 'overflow="visible"')
                if png:
                    from importlib.util import find_spec
                    from .font_resources import outline_text
                    font = Path(find_spec("matplotlib").origin).parent / "mpl-data/fonts/ttf/DejaVuSerif.ttf"
                    svg, _ = outline_text(svg, font, font, output / "text_fonts", "Leipzig")
                (folder / f"{label}_{page:02d}.svg").write_text(svg)
                if png:
                    from cairosvg import svg2png
                    svg2png(bytestring=svg.encode(), write_to=str(folder / f"{label}_{page:02d}.png"),
                            output_width=900, background_color="white")
        assert pages[0] == pages[1], fixture.name + ": page count changed"
        pixels_equal = None
        if png:
            from PIL import Image, ImageChops
            pixels_equal = True
            for page in range(1, pages[0] + 1):
                with Image.open(folder / f"source_{page:02d}.png") as a, Image.open(folder / f"decoded_{page:02d}.png") as b:
                    equal = a.size == b.size and ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is None
                    pixels_equal = pixels_equal and equal
            assert pixels_equal, fixture.name + ": source/decoded raster mismatch"
        results.append(dict(name=fixture.name, description=fixture.description, tokens=len(encoded.tokens),
                            notes=fixture.note_count, pages=pages[1], source_decoded_pixels_equal=pixels_equal,
                            source_sha256=hashlib.sha256(fixture.source.encode()).hexdigest(),
                            decoded_sha256=hashlib.sha256(decoded.encode()).hexdigest()))
    report = dict(profile=PROFILE, vocabulary_size=len(VOCABULARY), vocabulary_sha256=VOCABULARY_SHA256,
                  verovio=verovio.toolkit().getVersion(), fixtures=results)
    (output / "report.json").write_text(json.dumps(report, indent=2))
    (output / "vocabulary.json").write_text(json.dumps(VOCABULARY, ensure_ascii=False, indent=2))
    print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args()
    validate_all(args.output, args.png)


if __name__ == "__main__":
    main()
