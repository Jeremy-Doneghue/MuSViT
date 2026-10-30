"""Checked MusicXML simile and chord/slash notation support for generated parts."""

from copy import deepcopy
from fractions import Fraction
import xml.etree.ElementTree as ET

NS = "http://www.music-encoding.org/ns/mei"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


def q(name):
    return f"{{{NS}}}{name}"


def simile_groups(source):
    root = ET.fromstring(source) if isinstance(source, str) else source
    bars = root.findall("part/measure")
    states = []
    key = meter = None
    active = None
    groups = {}
    for index, bar in enumerate(bars):
        attr = bar.find("attributes")
        if attr is not None:
            key = attr.findtext("key/fifths", key)
            if attr.find("time") is not None:
                meter = (attr.findtext("time/beats"), attr.findtext("time/beat-type"))
        states.append((key, meter))
        for marker in bar.findall("attributes/measure-style/measure-repeat"):
            if marker.get("type") == "start":
                if active:
                    raise ValueError("overlapping simile patterns")
                size = int(marker.text)
                if size not in (1, 2) or index < size:
                    raise ValueError("simile has no preceding one- or two-bar source")
                active = (index, size)
            elif marker.get("type") == "stop":
                if active is None:
                    raise ValueError("unmatched simile stop")
                start, size = active
                if index - start != size:
                    raise ValueError("only one complete simile pattern per group is supported")
                groups[bars[start].get("id")] = dict(
                    measures=[b.get("id") for b in bars[start:index]],
                    sources=[b.get("id") for b in bars[start - size:start]])
                active = None
    if active:
        raise ValueError("simile patterns must have an explicit stop")
    by_id = {b.get("id"): b for b in bars}
    state_by_id = {b.get("id"): state for b, state in zip(bars, states, strict=True)}

    def notes(bar):
        result = []
        for note in bar.findall("note"):
            copied = deepcopy(note)
            for node in copied.iter():
                node.attrib.pop("id", None)
                node.text = (node.text or "").strip() or None
                node.tail = None
            result.append(ET.tostring(copied, encoding="unicode"))
        return result

    for group in groups.values():
        for offset, (target, original) in enumerate(zip(group["measures"], group["sources"], strict=True)):
            bar = by_id[target]
            if state_by_id[target] != state_by_id[original] or notes(bar) != notes(by_id[original]):
                raise ValueError("simile underlying music differs from its source")
            if offset and (bar.find("direction") is not None or bar.find("print") is not None
                           or bar.find("barline") is not None or bar.find("harmony") is not None
                           or bar.find("attributes") is not None):
                raise ValueError("two-bar simile hides a boundary or direction")
    return groups


def harmonies(bar, divisions, meter):
    """Read chord text and beat position from the canonical MusicXML stream."""
    cursor = Fraction()
    result = []
    for node in bar:
        if node.tag == "note":
            cursor += Fraction(node.findtext("duration"))
        elif node.tag == "harmony":
            root = node.findtext("root/root-step")
            alter = int(node.findtext("root/root-alter", "0"))
            kind = node.find("kind")
            if (root not in "ABCDEFG" or alter not in (-1, 0, 1) or
                    kind.text not in ("minor-seventh", "dominant", "major-seventh")):
                raise ValueError("unsupported chord symbol")
            suffix = kind.get("text") or {"minor-seventh": "m7", "dominant": "7", "major-seventh": "maj7"}[kind.text]
            label = root + {-1: "♭", 0: "", 1: "♯"}[alter] + suffix
            beat = 1 + (cursor + Fraction(node.findtext("offset", "0"))) * meter[1] / (4 * divisions)
            result.append((node.get("id"), label, beat))
    return result


def normalize_jazz(source, root):
    mx = ET.fromstring(source)
    groups = simile_groups(mx)
    bars = {b.get(XML_ID): b for b in root.iter(q("measure"))}
    for leader, group in groups.items():
        size = len(group["measures"])
        if size == 2:
            layer = bars[leader].find(f".//{q('layer')}")
            for child in list(layer):
                layer.remove(child)
            ET.SubElement(layer, q("multiRpt"), {XML_ID: leader + "-simile", "num": "2"})
            for parent in root.iter():
                for child in list(parent):
                    if child is bars[group["measures"][1]]:
                        parent.remove(child)
    divisions = meter = None
    for bar in mx.findall("part/measure"):
        if bar.find("attributes/divisions") is not None:
            divisions = int(bar.findtext("attributes/divisions"))
        if bar.find("attributes/time") is not None:
            meter = (int(bar.findtext("attributes/time/beats")), int(bar.findtext("attributes/time/beat-type")))
        expected = harmonies(bar, divisions, meter)
        actual = bars[bar.get("id")].findall(q("harm")) if bar.get("id") in bars else []
        if len(actual) != len(expected):
            raise ValueError("conversion lost chord symbols")
        for node, (identity, label, beat) in zip(actual, expected, strict=True):
            if Fraction(node.get("tstamp")) != beat:
                raise ValueError("conversion moved a chord symbol")
            node.set(XML_ID, identity)
            # Preserve exact root spelling and the requested chord suffix.
            for child in list(node):
                node.remove(child)
            node.text = label
    return groups


def check_harmonies(source_bar, mei_bar, divisions, meter):
    expected = harmonies(source_bar, divisions, meter)
    actual = [(h.get(XML_ID), "".join(h.itertext()).strip(), Fraction(h.get("tstamp")))
              for h in mei_bar.findall(q("harm"))]
    if actual != expected:
        raise ValueError("conversion changed chord symbols or positions")
