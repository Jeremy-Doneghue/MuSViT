"""Versioned MusicXML-derived token codec. No renderer or ML dependencies.

This is an explicit, restricted score-partwise profile, not an arbitrary XML
serializer. Unknown notation/attributes fail closed. See SCORE_CODEC.md.
"""

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from math import lcm
import re
import xml.etree.ElementTree as ET


class CodecError(ValueError):
    """Unsupported score, invalid semantics, or malformed token stream."""


PROFILE = "musvit-score-v1"
# Child order is retained: note/backup/forward order determines musical time.
CHILDREN = {
    "score-partwise": "work identification credit part-list part",
    "work": "work-title work-number",
    "identification": "creator rights miscellaneous",
    "miscellaneous": "miscellaneous-field",
    "credit": "credit-type credit-words",
    "part-list": "score-part",
    "score-part": "part-name part-abbreviation score-instrument",
    "score-instrument": "instrument-name instrument-abbreviation",
    "part": "measure",
    "measure": "print attributes direction harmony note backup forward barline",
    "print": "measure-numbering",
    "attributes": "divisions key time staves clef transpose measure-style",
    "key": "fifths mode",
    "time": "beats beat-type",
    "clef": "sign line clef-octave-change",
    "transpose": "diatonic chromatic octave-change",
    "measure-style": "multiple-rest measure-repeat slash",
    "direction": "direction-type offset voice staff sound",
    "direction-type": "words rehearsal dynamics wedge pedal dashes metronome segno coda",
    "dynamics": "p pp ppp f ff fff mp mf sfz fp",
    "metronome": "beat-unit beat-unit-dot per-minute",
    "harmony": "root kind bass offset staff",
    "root": "root-step root-alter",
    "bass": "bass-step bass-alter",
    "note": "cue chord pitch unpitched rest duration tie instrument voice type dot accidental time-modification stem notehead staff beam notations",
    "pitch": "step alter octave",
    "unpitched": "display-step display-octave",
    "rest": "display-step display-octave",
    "time-modification": "actual-notes normal-notes normal-type normal-dot",
    "notations": "tied slur tuplet articulations fermata glissando slide",
    "articulations": "accent staccato tenuto strong-accent falloff doit scoop plop breath-mark caesura",
    "backup": "duration",
    "forward": "duration voice staff",
    "barline": "bar-style ending repeat fermata",
}
ATTRIBUTES = {
    "score-partwise": "version", "creator": "type", "rights": "type",
    "miscellaneous-field": "name", "credit": "page", "score-part": "id",
    "score-instrument": "id", "part": "id", "measure": "id number implicit",
    "print": "new-system new-page", "clef": "number", "transpose": "number",
    "measure-style": "number", "multiple-rest": "use-symbols",
    "measure-repeat": "type slashes", "slash": "type use-stems",
    "direction": "id placement", "direction-type": "id",
    "words": "font-style font-weight enclosure", "rehearsal": "enclosure",
    "wedge": "type number", "pedal": "type number line sign", "dashes": "type number",
    "metronome": "parentheses", "sound": "tempo segno coda dalsegno tocoda time-only",
    "harmony": "id placement", "kind": "text", "note": "id print-object",
    "rest": "measure", "tie": "type", "instrument": "id", "type": "size",
    "accidental": "cautionary editorial parentheses", "notehead": "filled parentheses",
    "beam": "number", "tied": "type number", "slur": "id type number placement",
    "tuplet": "type number bracket show-number",
    "strong-accent": "type", "fermata": "type", "glissando": "type number line-type",
    "slide": "type number line-type", "barline": "location",
    "ending": "number type", "repeat": "direction times",
}
TEXT = set("""work-title work-number creator rights miscellaneous-field credit-type credit-words
part-name part-abbreviation instrument-name instrument-abbreviation measure-numbering divisions
fifths mode beats beat-type staves sign line clef-octave-change diatonic chromatic octave-change
multiple-rest measure-repeat words rehearsal per-minute beat-unit root-step root-alter bass-step
bass-alter kind offset voice staff step alter octave display-step display-octave duration type
accidental actual-notes normal-notes normal-type stem notehead beam fermata glissando slide
bar-style ending breath-mark caesura""".split())
FREE_TEXT = set("""work-title work-number creator rights miscellaneous-field credit-type credit-words
part-name part-abbreviation instrument-name instrument-abbreviation words rehearsal glissando slide ending""".split())
TAGS = sorted(set(CHILDREN) | {c for s in CHILDREN.values() for c in s.split()} | {"sound"})
ATTRS = sorted({a for s in ATTRIBUTES.values() for a in s.split()})
LITERALS = sorted(set(map(str, range(-16, 129))) | set("""yes no start stop continue discontinue
quarter eighth half whole 16th 32nd 64th normal x slash none up down begin end
forward backward regular light-light light-heavy above below major minor 4.0 C D E F G A B""".split()))
VOCABULARY = tuple(["<pad>", "<bos>", "<eos>", PROFILE, "<end>", "<attrs-end>", "<value-end>", "<text>"]
                   + ["E:" + t for t in TAGS] + ["A:" + a for a in ATTRS]
                   + ["V:" + v for v in LITERALS] + [f"B:{b:02x}" for b in range(256)])
W2I = {word: index for index, word in enumerate(VOCABULARY)}
VOCABULARY_SHA256 = hashlib.sha256(json.dumps(VOCABULARY, ensure_ascii=False).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise CodecError(message)


def parse(source):
    require(isinstance(source, str), "score source must be an XML string")
    require(not re.search(r"<!DOCTYPE|<!ENTITY", source, re.I), "DTDs/entities are outside the profile")
    try:
        root = ET.fromstring(source, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True)))
    except ET.ParseError as error:
        raise CodecError(f"invalid XML: {error}") from error
    require(root.tag == "score-partwise" and root.get("version") == "4.0", "expected score-partwise version 4.0")
    _check_tree(root)
    return root


def _check_tree(node, depth=0):
    require(depth < 100, "score nesting exceeds profile limit")
    require(node.tag in TAGS, f"unsupported element {node.tag!r}")
    require(not (set(node.attrib) - set(ATTRIBUTES.get(node.tag, "").split())),
            f"unsupported attributes on {node.tag}: {sorted(node.attrib)}")
    require(not (node.tail or "").strip(), f"mixed content after {node.tag} is unsupported")
    require(node.tag in TEXT or not (node.text or "").strip(), f"unexpected text in {node.tag}")
    allowed = CHILDREN.get(node.tag, "").split()
    for child in node:
        require(child.tag in allowed, f"unsupported {child.tag!r} inside {node.tag}")
        _check_tree(child, depth + 1)
    # Containers with fixed fields cannot repeat a scalar value accidentally.
    repeatable = {"part", "measure", "direction-type", "credit", "score-part", "creator", "rights",
                  "miscellaneous-field", "score-instrument", "clef", "transpose", "measure-style",
                  "credit-type", "dot", "normal-dot", "beat-unit-dot", "tie", "tied", "slur", "beam",
                  "glissando", "slide", "tuplet", "notations"}
    unordered = {"measure", "notations", "articulations", "direction-type", "dynamics"}
    if node.tag not in unordered:
        for tag in allowed:
            require(tag in repeatable or len(node.findall(tag)) <= 1, f"duplicate {tag} in {node.tag}")


def _canonical_root(source):
    root = parse(source)
    from .score_semantics import inspect_root
    inspect_root(root)  # Validate before any normalization; never repair bad rhythms.
    definitions = {}
    for node in root.iter():
        if "id" in node.attrib and node.tag not in ("part", "instrument"):
            identity = node.get("id")
            require(identity not in definitions, f"duplicate ID {identity}")
            definitions[identity] = f"id{len(definitions) + 1}"
    for node in root.iter():
        if "id" in node.attrib:
            require(node.get("id") in definitions, f"unresolved ID {node.get('id')}")
            node.set("id", definitions[node.get("id")])
        node.tail = None
        if node.tag not in TEXT:
            node.text = None
        elif node.tag not in FREE_TEXT:
            node.text = (node.text or "").strip() or None
        ordered = dict(sorted(node.attrib.items()))
        node.attrib.clear()
        node.attrib.update(ordered)
    # Canonical exact timing: smallest common integer divisions for each part.
    for part in root.findall("part"):
        timed = []
        divisions = None
        for measure in part.findall("measure"):
            for child in measure:
                if child.tag == "attributes" and child.find("divisions") is not None:
                    divisions = Fraction(child.findtext("divisions"))
                for node in child.iter():
                    if node.tag in ("duration", "offset"):
                        timed.append((node, Fraction(node.text) / divisions))
        scale = lcm(*(value.denominator for _, value in timed))
        for node, value in timed:
            node.text = str(int(value * scale))
        for node in part.iter("divisions"):
            node.text = str(scale)
    return root, definitions


def _xml(root):
    # Verovio 5.0 incorrectly classifies a sound by its first attribute. XML
    # attribute order is semantically irrelevant; serialize navigation first
    # for compatibility, while token attribute order remains lexicographic.
    for sound in root.iter("sound"):
        ordered = dict(sorted(sound.attrib.items(), key=lambda pair: (pair[0] not in ("segno", "coda", "dalsegno", "tocoda"), pair[0])))
        sound.attrib.clear()
        sound.attrib.update(ordered)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def canonicalize(source):
    """Validate, normalize local IDs/timing/formatting, return editable MusicXML."""
    return _xml(_canonical_root(source)[0])


def _tokens(root):
    output = [W2I["<bos>"], W2I[PROFILE]]
    def value(text):
        if "V:" + text in W2I:
            output.append(W2I["V:" + text])
        else:
            output.extend(W2I[f"B:{byte:02x}"] for byte in text.encode("utf-8"))
        output.append(W2I["<value-end>"])
    def visit(node):
        output.append(W2I["E:" + node.tag])
        for name, text in sorted(node.attrib.items()):
            output.append(W2I["A:" + name])
            value(text)
        output.append(W2I["<attrs-end>"])
        if node.text is not None:
            output.append(W2I["<text>"])
            value(node.text)
        for child in node:
            visit(child)
        output.append(W2I["<end>"])
    visit(root)
    output.append(W2I["<eos>"])
    return output


@dataclass(frozen=True)
class EncodedScore:
    tokens: list[int]
    source_ids: dict[str, str]
    profile: str = PROFILE
    vocabulary_sha256: str = VOCABULARY_SHA256


def encode_with_metadata(source):
    """Keep original→canonical IDs for linking separate source evidence."""
    root, identities = _canonical_root(source)
    return EncodedScore(_tokens(root), identities)


def encode(source):
    return encode_with_metadata(source).tokens


def decode(tokens):
    """Decode one complete canonical sequence; no padding/truncation repairs."""
    ids = list(tokens)
    require(len(ids) <= 1_000_000, "token stream exceeds limit")
    require(all(type(i) is int and 0 <= i < len(VOCABULARY) for i in ids), "invalid token ID")
    words = [VOCABULARY[i] for i in ids]
    require(words[:2] == ["<bos>", PROFILE] and words[-1:] == ["<eos>"], "missing BOS/profile/EOS")
    position = 2
    def take():
        nonlocal position
        require(position < len(words) - 1, "truncated token stream")
        word = words[position]
        position += 1
        return word
    def value():
        word = take()
        if word.startswith("V:"):
            result = word[2:]
            require(take() == "<value-end>", "invalid literal value")
        else:
            data = bytearray()
            while word != "<value-end>":
                require(word.startswith("B:"), "expected UTF-8 value bytes")
                data.append(int(word[2:], 16))
                word = take()
            try:
                result = data.decode("utf-8")
            except UnicodeDecodeError as error:
                raise CodecError("invalid UTF-8 value") from error
        require(all(c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD
                    or 0x10000 <= ord(c) <= 0x10FFFF for c in result), "invalid XML character")
        return result
    def element(depth=0):
        require(depth < 100, "token nesting exceeds limit")
        word = take()
        require(word.startswith("E:"), "expected element token")
        node = ET.Element(word[2:])
        word = take()
        while word != "<attrs-end>":
            require(word.startswith("A:") and word[2:] not in node.attrib, "invalid/duplicate attribute")
            node.set(word[2:], value())
            word = take()
        if position < len(words) and words[position] == "<text>":
            take()
            node.text = value()
        while position < len(words) and words[position] != "<end>":
            node.append(element(depth + 1))
        require(take() == "<end>", "missing element end")
        return node
    root = element()
    require(position == len(words) - 1, "extra tokens after score")
    xml = _xml(root)
    require(encode(xml) == ids, "noncanonical token stream")
    return xml
