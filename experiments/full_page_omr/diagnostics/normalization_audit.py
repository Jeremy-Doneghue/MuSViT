"""Differential audit of the MusicXML normalization policy; no renderer/data writes.

Exit 1 means a policy gap or lost distinction; exit 2 means an invalid probe.
This checks the current codec, not a replacement implementation.
"""

import copy
import json
import xml.etree.ElementTree as ET

from experiments.full_page_omr.representation.codec_fixtures import (
    add, horn, note, score, tie, xml,
)
from experiments.full_page_omr.representation.score_codec import canonicalize, decode, encode


def whole():
    root, _, bar = score("Normalization audit", "Horn")
    note(bar, length=4, kind="whole")
    return root


def chord(pitches):
    root, _, bar = score("Normalization audit", "Piano")
    for index, pitch in enumerate(pitches):
        note(bar, pitch, length=4, kind="whole", chord=index > 0)
    return root


def voices(order):
    root, _, bar = score("Normalization audit", "Piano", 2)
    for index, voice in enumerate(order):
        if index:
            add(add(bar, "backup"), "duration", 48)
        note(bar, "C" if voice == 1 else "E", octave=4 if voice == 1 else 3,
             length=4, kind="whole", voice=voice, staff=voice)
    return root


def cases():
    base = ET.fromstring(horn().source)
    scaled = copy.deepcopy(base)
    for node in scaled.iter():
        if node.tag in ("divisions", "duration", "offset"):
            node.text = str(int(node.text) * 7)
    yield "equivalent division scales", True, base, scaled

    # A local divisions change also changes durations/offsets in its scope.
    changed = copy.deepcopy(base)
    bar = changed.findall("part/measure")[1]
    attrs = ET.Element("attributes")
    add(attrs, "divisions", 60)
    bar.insert(1, attrs)  # after the existing print element
    for node in bar.iter():
        if node.tag in ("duration", "offset"):
            node.text = str(int(node.text) * 5)
    yield "equivalent mid-part divisions declarations", True, base, changed

    renamed = copy.deepcopy(base)
    for node in renamed.iter():
        if node.get("id"):
            node.set("id", "other-" + node.get("id"))
        node.attrib = dict(reversed(list(node.attrib.items())))
    yield "source IDs and attribute order", True, base, renamed
    yield "chord member order", True, chord("CEG"), chord("GEC")
    yield "independent voice serialization", True, voices((1, 2)), voices((2, 1))

    base = whole()
    explicit = copy.deepcopy(base)
    pitch = explicit.find(".//note/pitch")
    pitch.insert(1, ET.Element("alter"))
    pitch.find("alter").text = "0"
    yield "absent versus zero pitch alteration", True, base, explicit

    explicit = copy.deepcopy(base)
    explicit.find(".//note").set("print-object", "yes")
    yield "default note visibility", True, base, explicit

    # Same attached text/onset, expressed before versus after the note.
    before, after = copy.deepcopy(base), copy.deepcopy(base)
    for root, offset in ((before, 0), (after, -48)):
        bar = root.find("part/measure")
        direction = ET.Element("direction")
        add(add(direction, "direction-type"), "words", "Solo")
        add(direction, "offset", offset)
        if offset == 0:
            bar.insert(1, direction)
        else:
            bar.append(direction)
    yield "direction cursor placement with equivalent offset", True, before, after

    explicit = copy.deepcopy(base)
    n = explicit.find(".//note")
    accidental = ET.Element("accidental", cautionary="yes", parentheses="yes")
    accidental.text = "natural"
    n.insert(list(n).index(n.find("staff")), accidental)
    yield "visible courtesy accidental", False, base, explicit

    # Same pitches, staff, onset and duration; chord grouping differs.
    left = chord("CE")
    right, _, bar = score("Normalization audit", "Piano")
    note(bar, "C", length=4, kind="whole", voice=1)
    add(add(bar, "backup"), "duration", 48)
    note(bar, "E", length=4, kind="whole", voice=2)
    yield "chord versus independent voices", False, left, right

    tied, _, bar = score("Normalization audit", "Horn")
    tie(note(bar, length=2, kind="half"), "start")
    tie(note(bar, length=2, kind="half"), "stop")
    yield "whole note versus tied halves", False, base, tied

    flat, sharp = copy.deepcopy(base), copy.deepcopy(base)
    for root, step, alter, accidental in ((flat, "D", "-1", "flat"), (sharp, "C", "1", "sharp")):
        n = root.find(".//note")
        n.find("pitch/step").text = step
        n.find("pitch").insert(1, ET.Element("alter"))
        n.find("pitch/alter").text = alter
        a = ET.Element("accidental")
        a.text = accidental
        n.insert(list(n).index(n.find("staff")), a)
    yield "enharmonic written pitch", False, flat, sharp

    for label, tag, content in (("passage instruction", "words", "BRUSHES"),
                                ("rehearsal mark", "rehearsal", "A"),
                                ("dynamic", "dynamics", None)):
        marked = copy.deepcopy(base)
        direction = ET.SubElement(marked.find("part/measure"), "direction")
        marker = add(add(direction, "direction-type"), tag, content)
        if tag == "dynamics":
            add(marker, "mf")
        add(direction, "offset", -48)
        yield label, False, base, marked


def audit():
    rows = []
    for label, equivalent, left, right in cases():
        try:
            sources = [xml(root) for root in (left, right)]
            tokens = [encode(source) for source in sources]
            for source, stream in zip(sources, tokens):
                assert encode(decode(stream)) == stream, "token round trip changed"
                canonical = canonicalize(source)
                assert canonicalize(canonical) == canonical, "normalization not idempotent"
            equal = tokens[0] == tokens[1]
            rows.append(dict(case=label, expected_equal=equivalent, actual_equal=equal,
                             status="satisfied" if equal == equivalent else
                             ("normalization_gap" if equivalent else "lost_distinction"),
                             token_lengths=list(map(len, tokens))))
        except Exception as error:
            rows.append(dict(case=label, status="probe_error", error=str(error)))
    return rows


def main():
    rows = audit()
    counts = {status: sum(row["status"] == status for row in rows)
              for status in ("satisfied", "normalization_gap", "lost_distinction", "probe_error")}
    print(json.dumps(dict(summary=counts, cases=rows), indent=2))
    return 2 if counts["probe_error"] else int(bool(counts["normalization_gap"] or counts["lost_distinction"]))


if __name__ == "__main__":
    raise SystemExit(main())
