"""MusicXML serialization and checked Verovio conversion for synthetic horn parts."""

from fractions import Fraction
import xml.etree.ElementTree as ET

MEI_NS = "http://www.music-encoding.org/ns/mei"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
ARTICULATIONS = {"acc": "accent", "stacc": "staccato", "ten": "tenuto", "marc": "strong-accent"}


def add(parent, tag, text=None, **attrs):
    child = ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})
    if text is not None:
        child.text = str(text)
    return child


def key_alter(step, fifths):
    order = "FCGDAEB" if fifths > 0 else "BEADGCF"
    return (1 if fifths > 0 else -1) if step.upper() in order[:abs(fifths)] else 0


def beam_plan(measure):
    """Conservative metrical beams; rests and beat crossings break a run.

    Simple meters use quarter-note beats, 6/8 uses dotted-quarter beats.
    5/4 currently uses five quarter beats rather than a chosen 3+2 accent pattern.
    The result maps event IDs to (beam level, MusicXML value) pairs.
    """
    beat = 6 if measure.meter == (6, 8) else 4
    groups = []
    run = []
    position = 0
    run_beat = None
    for event in measure.events:
        current_beat = position // beat
        eligible = (event.pitch is not None and not event.measure_rest
                    and event.sixteenths in (1, 2, 3)
                    and position + event.sixteenths <= (current_beat + 1) * beat)
        if not eligible or current_beat != run_beat:
            if len(run) >= 2:
                groups.append(run)
            run = []
        if eligible:
            run.append((event, position))
            run_beat = current_beat
        position += event.sixteenths
    if len(run) >= 2:
        groups.append(run)
    plan = {}
    for group in groups:
        for index, (event, onset) in enumerate(group):
            values = [(1, "begin" if index == 0 else "end" if index == len(group) - 1 else "continue")]
            if event.sixteenths == 1:
                previous = index > 0 and group[index - 1][0].sixteenths == 1
                following = index + 1 < len(group) and group[index + 1][0].sixteenths == 1
                if previous or following:
                    value = "continue" if previous and following else "end" if previous else "begin"
                elif index == 0:
                    value = "forward hook"
                elif index == len(group) - 1:
                    value = "backward hook"
                else:
                    value = "forward hook" if onset % 2 == 0 else "backward hook"
                values.append((2, value))
            plan[event.id] = values
    return plan


def to_musicxml(part):
    """Serialize written pitches, notation, and executable navigation to MusicXML 4."""
    root = ET.Element("score-partwise", version="4.0")
    display_seed = str(part.seed) if part.schema_version == 1 else f"{part.seed & 0xffffffff:08x}"
    add(add(root, "work"), "work-title", f"Synthetic jazz study — {display_seed}")
    score_part = add(add(root, "part-list"), "score-part", id="P1")
    add(score_part, "part-name", part.instrument + " (written pitch)")
    instrument = add(score_part, "score-instrument", id="I1")
    add(instrument, "instrument-name", part.instrument)
    body = add(root, "part", id="P1")
    previous = None
    for index, measure in enumerate(part.measures):
        beams = beam_plan(measure)
        n = measure.number
        bar = add(body, "measure", number=n, id=measure.id)
        if part.system_breaks is None:
            page_break = n > 1 and (n - 1) % 8 == 0
            system_break = n > 1 and (n - 1) % 4 == 0
        else:
            page_break = measure.id in (part.page_breaks or [])
            system_break = measure.id in part.system_breaks
        if index == 0 and part.system_breaks is not None:
            add(bar, "print", **{"new-page": "yes"})
        elif page_break or system_break:
            add(bar, "print", **{"new-page" if page_break else "new-system": "yes"})
        if previous is None or (measure.key, measure.meter) != (previous.key, previous.meter):
            attributes = add(bar, "attributes")
            if previous is None:
                add(attributes, "divisions", 4)  # one tick per sixteenth note
            if previous is None or measure.key != previous.key:
                add(add(attributes, "key"), "fifths", measure.key)
            if previous is None or measure.meter != previous.meter:
                time = add(attributes, "time")
                add(time, "beats", measure.meter[0])
                add(time, "beat-type", measure.meter[1])
            if previous is None:
                clef = add(attributes, "clef")
                add(clef, "sign", "G")
                add(clef, "line", 2)
                # Notes are written pitches. Tenor sax sounds a major ninth lower.
                if part.instrument == "Tenor saxophone":
                    transpose = add(attributes, "transpose")
                    add(transpose, "diatonic", -1)
                    add(transpose, "chromatic", -2)
                    add(transpose, "octave-change", -1)
        group = next((g for g in part.multirests if g[0] == measure.id), None)
        if group:
            attributes = bar.find("attributes")
            if attributes is None:
                attributes = add(bar, "attributes")
            add(add(attributes, "measure-style"), "multiple-rest", len(group), **{"use-symbols": "no"})
        repeat_start = next((g for g in part.similes if g.measures[0] == measure.id), None)
        repeat_stop = any(index and g.measures[-1] == part.measures[index - 1].id for g in part.similes)
        slash_start = any(e.slash for e in measure.events) and (index == 0 or not any(e.slash for e in part.measures[index - 1].events))
        slash_stop = not any(e.slash for e in measure.events) and index > 0 and any(e.slash for e in part.measures[index - 1].events)
        if repeat_start or repeat_stop or slash_start or slash_stop:
            attributes = bar.find("attributes")
            if attributes is None:
                attributes = add(bar, "attributes")
            if repeat_stop:
                add(add(attributes, "measure-style"), "measure-repeat", type="stop")
            if repeat_start:
                size = len(repeat_start.measures)
                add(add(attributes, "measure-style"), "measure-repeat", size, type="start", slashes=size)
            if slash_start or slash_stop:
                add(add(attributes, "measure-style"), "slash", type="start" if slash_start else "stop", **{"use-stems": "no"})
        if part.scenario in ("repeat", "endings") and measure.id == part.navigation["start"]:
            add(add(bar, "barline", location="left"), "repeat", direction="forward")
        if part.scenario == "endings":
            for number, name in ((1, "first_ending"), (2, "second_ending")):
                if measure.id == part.navigation[name][0]:
                    add(add(bar, "barline", location="left"), "ending", number=number, type="start")
        for direction in part.directions:
            if direction["measure"] != measure.id:
                continue
            node = add(bar, "direction", placement="below" if direction["kind"] == "dynam" else "above")
            kind = add(node, "direction-type")
            if direction["kind"] == "dynam":
                add(add(kind, "dynamics"), direction["text"])
            else:
                add(kind, "rehearsal" if direction["kind"] == "reh" else "words", direction["text"])
        if part.scenario == "ds_coda" and measure.id in (part.navigation["segno"], part.navigation["coda"]):
            kind = "segno" if measure.id == part.navigation["segno"] else "coda"
            direction = add(bar, "direction", placement="above")
            add(add(direction, "direction-type"), kind)
            add(direction, "sound", **{kind: kind + "-1"})
        onset = 0
        for event in measure.events:
            for chord in measure.chords:
                if chord.onset == onset:
                    harmony = add(bar, "harmony", id=chord.id, placement="above")
                    root_node = add(harmony, "root")
                    add(root_node, "root-step", chord.root)
                    if chord.alter:
                        add(root_node, "root-alter", chord.alter)
                    kind_node = add(harmony, "kind", chord.kind)
                    kind_node.set("text", {"minor-seventh": "m7", "dominant": "7", "major-seventh": "maj7"}[chord.kind])
            note = add(bar, "note", id=event.id)
            if event.slash:
                unpitched = add(note, "unpitched")
                add(unpitched, "display-step", "B")
                add(unpitched, "display-octave", 4)
            elif event.pitch is None:
                add(note, "rest", **({"measure": "yes"} if event.measure_rest else {}))
            else:
                pitch = add(note, "pitch")
                add(pitch, "step", event.pitch.upper())
                # MusicXML pitch alterations are explicit even when the key
                # signature supplies the accidental visually.
                add(pitch, "alter", key_alter(event.pitch, measure.key))
                add(pitch, "octave", event.octave)
            add(note, "duration", event.sixteenths)
            if not event.measure_rest:
                add(note, "type", {1: "16th", 2: "eighth", 3: "eighth", 4: "quarter",
                                   6: "quarter", 8: "half", 12: "half", 16: "whole"}[event.sixteenths])
                if event.sixteenths in (3, 6, 12):
                    add(note, "dot")
            if event.slash:
                add(note, "stem", "none")
                add(note, "notehead", "slash")
            for level, value in beams.get(event.id, []):
                add(note, "beam", value, number=level)
            endpoints = [(slur, "start" if event.id == slur.start else "stop")
                         for slur in part.slurs if event.id in (slur.start, slur.end)]
            if (event.pitch is not None and event.articulation) or endpoints:
                notations = add(note, "notations")
                if event.articulation:
                    attrs = {"type": "up"} if event.articulation == "marc" else {}
                    add(add(notations, "articulations"), ARTICULATIONS[event.articulation], **attrs)
                for slur, kind in endpoints:
                    add(notations, "slur", type=kind, number=1,
                        id=slur.id if kind == "start" else slur.id + "-stop")
            onset += event.sixteenths
        if part.scenario == "ds_coda" and measure.id in (part.navigation["to_coda"], part.navigation["ds"]):
            is_coda = measure.id == part.navigation["to_coda"]
            direction = add(bar, "direction", placement="above")
            add(add(direction, "direction-type"), "words", "To Coda" if is_coda else "D.S. al Coda")
            add(direction, "sound", **({"tocoda": "coda-1", "time-only": "2"} if is_coda else {"dalsegno": "segno-1"}))
        repeat_end = part.scenario == "repeat" and measure.id == part.navigation["end"]
        ending_number = None
        if part.scenario == "endings":
            for number, name in ((1, "first_ending"), (2, "second_ending")):
                if measure.id == part.navigation[name][-1]:
                    ending_number = number
            repeat_end = ending_number == 1
        if repeat_end or ending_number or measure is part.measures[-1]:
            line = add(bar, "barline", location="right")
            add(line, "bar-style", "light-heavy" if repeat_end or measure is part.measures[-1] else "regular")
            if ending_number:
                add(line, "ending", number=ending_number, type="stop" if ending_number == 1 else "discontinue")
            if repeat_end:
                add(line, "repeat", direction="backward", times=part.navigation["times"])
        previous = measure
    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def musicxml_to_mei(source):
    """Convert the saved canonical score; no independently generated MEI score."""
    import verovio

    toolkit = verovio.toolkit()
    toolkit.setOptions({"inputFrom": "musicxml", "breaks": "encoded"})
    if not toolkit.loadData(source):
        raise ValueError("Verovio rejected MusicXML")
    return toolkit.getMEI()


def multirest_groups(source):
    """Return compressed-rest membership without discarding canonical measures.

    Restrict runs to silent, equal-meter measures with no hidden musical or
    layout changes. This avoids suppressing navigation or annotation targets.
    """
    root = ET.fromstring(source) if isinstance(source, str) else source
    bars = root.findall("part/measure")
    states = []
    key = meter = divisions = None
    for bar in bars:
        attr = bar.find("attributes")
        if attr is not None:
            key = attr.findtext("key/fifths", key)
            if attr.find("time") is not None:
                meter = (int(attr.findtext("time/beats")), int(attr.findtext("time/beat-type")))
            divisions = int(attr.findtext("divisions", str(divisions)))
        states.append((key, meter, divisions))
    groups = {}
    used = set()
    for index, bar in enumerate(bars):
        marker = bar.find("attributes/measure-style/multiple-rest")
        if marker is None:
            continue
        count = int(marker.text)
        if count < 2 or index + count > len(bars):
            raise ValueError("multibar rest must cover at least two existing measures")
        members = bars[index:index + count]
        for offset, member in enumerate(members):
            notes = member.findall("note")
            _, meter, divisions = states[index + offset]
            full = Fraction(meter[0] * 4 * divisions, meter[1])
            if (member.get("id") in used or states[index + offset] != states[index]
                    or len(notes) != 1 or notes[0].find("rest[@measure='yes']") is None
                    or Fraction(notes[0].findtext("duration")) != full
                    or member.find("direction") is not None or member.find("barline") is not None
                    or member.find("harmony") is not None
                    or (offset and (member.find("attributes") is not None or member.find("print") is not None))):
                raise ValueError("multibar rest hides notes, boundaries, changes, or directions")
            used.add(member.get("id"))
        groups[bar.get("id")] = [m.get("id") for m in members]
    return groups


def normalize_mei(source, converted):
    """Normalize Verovio's import for interchange and reliable rendering.

    Slash noteheads require MEI All's unpitched staff-location attributes.
    Retain the signature and navigation encodings also used by MuseScore.
    """
    root = ET.fromstring(converted)
    from .jazz_notation import normalize_jazz

    similes = normalize_jazz(source, root)
    root.set("meiversion", "5.1")
    q = lambda name: f"{{{MEI_NS}}}{name}"
    for owner in root.iter():
        owner.attrib.pop("dur.ppq", None)  # MEI All performance attribute
        owner.attrib.pop("vgrp", None)  # MEI All vertical-layout hint
        if owner.tag == q("note"):
            accidental = owner.attrib.pop("accid.ges", None)
            if accidental is not None:
                child = owner.find(q("accid"))
                if child is None:
                    child = ET.Element(q("accid"))
                    owner.insert(0, child)
                child.set("accid.ges", accidental)
        if owner.tag == q("ending"):
            number = owner.attrib.pop("n")
            owner.set("label", number + ".")
            owner.set("type", f"mscore-ending-{number}")
        for child in list(owner):
            if child.tag == q("encodingDesc"):
                owner.remove(child)  # converter provenance lives in layout.json
            elif child.tag == q("keySig"):
                owner.set("keysig", child.get("sig"))
                owner.remove(child)
            elif child.tag == q("meterSig"):
                owner.set("meter.count", child.get("count"))
                owner.set("meter.unit", child.get("unit"))
                owner.remove(child)
    mx = ET.fromstring(source)
    # Verovio 5.0 can drop a signature change at the start of a compressed rest.
    # Rebuild effective signature definitions directly from the canonical score.
    definitions = list(root.iter(q("scoreDef")))
    initial_definition = definitions[0]
    for parent in root.iter():
        for child in list(parent):
            if child.tag == q("scoreDef") and child is not initial_definition:
                parent.remove(child)
    initial_staff = initial_definition.find(f".//{q('staffDef')}")
    parents = {child: parent for parent in root.iter() for child in parent}
    visible = {bar.get(XML_ID): bar for bar in root.iter(q("measure"))}
    key = meter = None
    for index, bar in enumerate(mx.findall("part/measure")):
        new_key = bar.findtext("attributes/key/fifths", key)
        time = bar.find("attributes/time")
        new_meter = (time.findtext("beats"), time.findtext("beat-type")) if time is not None else meter
        if index == 0 or new_key != key or new_meter != meter:
            fifths = int(new_key)
            sig = "0" if not fifths else f"{abs(fifths)}{'s' if fifths > 0 else 'f'}"
            attrs = {"keysig": sig, "meter.count": new_meter[0], "meter.unit": new_meter[1]}
            if index == 0:
                initial_staff.attrib.update(attrs)
            else:
                target = visible[bar.get("id")]
                parent = parents[target]
                parent.insert(list(parent).index(target), ET.Element(q("scoreDef"), attrs))
        key, meter = new_key, new_meter
    transpose = mx.find("part/measure/attributes/transpose")
    if transpose is not None:
        staff = root.find(f".//{q('staffDef')}")
        octaves = int(transpose.findtext("octave-change", "0"))
        # Verovio 5.0 imports the compound diatonic interval off by one.
        staff.set("trans.diat", str(int(transpose.findtext("diatonic")) + 7 * octaves))
        staff.set("trans.semi", str(int(transpose.findtext("chromatic")) + 12 * octaves))
    bars = {m.get(XML_ID): m for m in root.iter(q("measure"))}
    groups = multirest_groups(mx)
    hidden = ({mid for members in groups.values() for mid in members[1:]}
              | {mid for group in similes.values() for mid in group["measures"][1:]})
    meter = None
    for measure in mx.findall("./part/measure"):
        time = measure.find("attributes/time")
        if time is not None:
            meter = (int(time.findtext("beats")), int(time.findtext("beat-type")))
        if measure.get("id") in hidden:
            continue
        bar = bars[measure.get("id")]
        for direction in list(bar):
            kind = direction.get("type")
            if direction.tag != q("dir") or kind not in ("segno", "coda", "tocoda", "dalsegno"):
                continue
            direction.tag = q("repeatMark")
            for child in list(direction):
                direction.remove(child)
            direction.set("func", {"segno": "segno", "coda": "coda", "tocoda": "coda", "dalsegno": "dalSegno"}[kind])
            if kind in ("segno", "coda"):
                direction.attrib.pop("type", None)
                direction.set("tstamp", "1")
                direction.text = None
            else:
                direction.set("type", "mscore-marker-to-coda" if kind == "tocoda" else "mscore-jump-ds-al-coda")
                direction.set("tstamp", str(meter[0] + 1))
                direction.text = "To Coda" if kind == "tocoda" else "D.S. al Coda"
    ET.indent(root)
    # Other SVG exporters share ElementTree's process-global namespace registry.
    # Verovio's importer expects unprefixed MEI elements under the default namespace.
    ET.register_namespace("", MEI_NS)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def check_conversion(source, mei):
    """Fail closed when a currently supported musical feature is lost in conversion.

    This deliberately checks our single-staff generated subset, not arbitrary
    MusicXML (polyphony, ties, tuplets, etc. need additional checks when added).
    """
    mx = ET.fromstring(source)
    from .jazz_notation import simile_groups, check_harmonies

    similes = simile_groups(mx)
    simile_members = {mid for group in similes.values() for mid in group["measures"]}
    root = ET.fromstring(mei)
    q = lambda name: f"{{{MEI_NS}}}{name}"
    source_bars = mx.findall("./part/measure")
    groups = multirest_groups(mx)
    hidden = ({mid for members in groups.values() for mid in members[1:]}
              | {mid for group in similes.values() for mid in group["measures"][1:]})
    visible_bars = [b for b in source_bars if b.get("id") not in hidden]
    converted_bars = list(root.iter(q("measure")))
    if len(visible_bars) != len(converted_bars):
        raise ValueError("conversion changed the measure count")
    states = {}
    key = meter = None
    for node in root.iter():
        if node.tag in (q("scoreDef"), q("staffDef")):
            key = node.get("keysig", key)
            if node.get("meter.count"):
                meter = (int(node.get("meter.count")), int(node.get("meter.unit")))
        elif node.tag == q("measure"):
            states[node.get(XML_ID)] = (key, meter)
    fifths = time = divisions = None
    for before, after in zip(visible_bars, converted_bars, strict=True):
        mid = before.get("id")
        def require(condition, feature):
            if not condition:
                raise ValueError(f"conversion lost {feature} in {mid}")
        require(after.get(XML_ID) == mid, "measure identity")
        attr = before.find("attributes")
        if attr is not None:
            if attr.find("key") is not None:
                fifths = int(attr.findtext("key/fifths"))
            if attr.find("time") is not None:
                time = (int(attr.findtext("time/beats")), int(attr.findtext("time/beat-type")))
            if attr.find("divisions") is not None:
                divisions = int(attr.findtext("divisions"))
        sig = "0" if not fifths else f"{abs(fifths)}{'s' if fifths > 0 else 'f'}"
        require(states[mid] == (sig, time), "key or meter")
        notes = before.findall("note")
        require(sum(Fraction(n.findtext("duration")) for n in notes) ==
                Fraction(time[0] * 4 * divisions, time[1]), "measure duration")
        check_harmonies(before, after, divisions, time)
        events = [n for n in after.iter() if n.tag in (q("note"), q("rest"), q("mRest"), q("multiRest"), q("mRpt"), q("multiRpt"))]
        if mid in groups:
            require(len(events) == 1 and events[0].tag == q("multiRest") and
                    events[0].get("num") == str(len(groups[mid])), "multibar rest count")
            notes = []  # Its canonical component measures were checked above.
            events = []
        else:
            require(not any(e.tag == q("multiRest") for e in events), "unexpected multibar rest")
        if mid in similes:
            size = len(similes[mid]["measures"])
            require(len(events) == 1 and events[0].tag == q("mRpt" if size == 1 else "multiRpt")
                    and (size == 1 or events[0].get("num") == "2"), "simile pattern size")
            notes = []
            events = []
        else:
            require(not any(e.tag in (q("mRpt"), q("multiRpt")) for e in events), "unexpected simile")
        require(len(notes) == len(events), "event count")
        for note, event in zip(notes, events, strict=True):
            require(note.get("id") == event.get(XML_ID), "event identity")
            if event.tag == q("mRest"):
                duration = Fraction(time[0] * 16, time[1])
            else:
                duration = Fraction(16, int(event.get("dur"))) * sum(
                    (Fraction(1, 2**i) for i in range(int(event.get("dots", "0")) + 1)), Fraction())
            require(Fraction(note.findtext("duration")) * 4 / divisions == duration, "duration")
            require((note.find("rest") is not None) == (event.tag in (q("rest"), q("mRest"))), "note/rest")
            if note.find("rest[@measure='yes']") is not None:
                require(event.tag == q("mRest"), "full-measure rest")
            if note.find("unpitched") is not None:
                require(note.findtext("notehead") == "slash" and event.get("head.shape") == "slash"
                        and event.get("stem.visible") == "false" and event.get("pname") is None,
                        "improvisation slash")
            if note.find("pitch") is not None:
                require(note.findtext("pitch/step").lower() == event.get("pname") and
                        note.findtext("pitch/octave") == event.get("oct"), "written pitch")
                accidental = event.get("accid.ges") or event.get("accid")
                accid_child = event.find(q("accid"))
                if accid_child is not None:
                    accidental = accid_child.get("accid.ges") or accid_child.get("accid")
                alter = {"s": 1, "f": -1, "n": 0, None: key_alter(event.get("pname"), fifths)}[accidental]
                require(alter == int(note.findtext("pitch/alter", "0")), "pitch alteration")
            reverse_artic = {value: key for key, value in ARTICULATIONS.items()}
            expected_artic = [reverse_artic[n.tag] for n in note.findall("notations/articulations/*")]
            actual_artic = [n.get("artic") for n in event.findall(q("artic"))]
            require(expected_artic == actual_artic, "articulation")
        for kind, tag in (("words", "dir"), ("rehearsal", "reh"), ("dynamics", "dynam")):
            expected = ["".join(d.itertext()).strip() if kind != "dynamics" else list(d)[0].tag
                        for d in before.findall(f"direction/direction-type/{kind}")]
            # Navigation words are checked as repeatMark below.
            expected = [t for t in expected if t not in ("To Coda", "D.S. al Coda")]
            actual = ["".join(d.itertext()).strip() for d in after.findall(q(tag))]
            require(expected == actual, kind)
        for side, attribute in (("left", "left"), ("right", "right")):
            line = before.find(f"barline[@location='{side}']")
            if line is not None:
                repeat = line.find("repeat")
                if repeat is not None:
                    require(after.get(attribute) == ("rptstart" if side == "left" else "rptend"), "repeat barline")
                elif line.findtext("bar-style") == "light-heavy":
                    require(after.get(attribute) == "end", "final barline")
        sounds = before.findall("direction/sound")
        expected = []
        for sound in sounds:
            if sound.get("segno"):
                expected.append(("segno", None, "1"))
            elif sound.get("dalsegno"):
                expected.append(("dalSegno", "mscore-jump-ds-al-coda", str(time[0] + 1)))
            elif sound.get("tocoda"):
                expected.append(("coda", "mscore-marker-to-coda", str(time[0] + 1)))
            elif sound.get("coda"):
                expected.append(("coda", None, "1"))
            else:
                raise ValueError("unsupported MusicXML sound direction")
        marks = after.findall(q("repeatMark"))
        require([(m.get("func"), m.get("type"), m.get("tstamp")) for m in marks] == expected, "navigation")
    endings = list(root.iter(q("ending")))
    expected_endings = []
    active = None
    for bar in source_bars:
        for line in bar.findall("barline"):
            end = line.find("ending")
            if end is not None and end.get("type") == "start":
                active = (end.get("number"), [])
        if active:
            active[1].append(bar.get("id"))
        if any(e.get("type") in ("stop", "discontinue") for e in bar.findall("barline/ending")):
            expected_endings.append(active)
            active = None
    actual_endings = [(e.get("n") or e.get("label", "").rstrip("."),
                       [b.get(XML_ID) for b in e.iter(q("measure"))]) for e in endings]
    if actual_endings != expected_endings:
        raise ValueError("conversion changed ending numbers or extents")
    expected_slurs = []
    active_slurs = {}
    for note in mx.findall("part/measure/note"):
        for slur in note.findall("notations/slur"):
            number = slur.get("number", "1")
            if slur.get("type") == "start":
                if number in active_slurs:
                    raise ValueError("overlapping slur number")
                active_slurs[number] = note.get("id")
            elif slur.get("type") == "stop":
                if number not in active_slurs:
                    raise ValueError("unmatched slur stop")
                expected_slurs.append(("#" + active_slurs.pop(number), "#" + note.get("id")))
            else:
                raise ValueError("unsupported slur continuation")
    if active_slurs:
        raise ValueError("unclosed MusicXML slur")
    actual_slurs = [(s.get("startid"), s.get("endid")) for s in root.iter(q("slur"))]
    if sorted(actual_slurs) != sorted(expected_slurs):
        raise ValueError("conversion changed slur endpoints")
    expected_beams = []
    for bar in source_bars:
        if bar.get("id") in simile_members:
            continue
        run = None
        for note in bar.findall("note"):
            beam = note.find("beam[@number='1']")
            if beam is None:
                if run is not None:
                    raise ValueError("unclosed MusicXML beam")
                continue
            if beam.text == "begin":
                if run is not None:
                    raise ValueError("overlapping MusicXML beams")
                run = [note.get("id")]
            elif beam.text in ("continue", "end") and run is not None:
                run.append(note.get("id"))
                if beam.text == "end":
                    expected_beams.append(run)
                    run = None
            else:
                raise ValueError("invalid MusicXML primary beam")
        if run is not None:
            raise ValueError("beam crosses a barline")
    actual_beams = [[n.get(XML_ID) for n in beam.iter(q("note"))]
                    for beam in root.iter(q("beam"))]
    if actual_beams != expected_beams:
        raise ValueError("conversion changed beam groups")
    transpose = mx.find("part/measure/attributes/transpose")
    if transpose is not None:
        staff = root.find(f".//{q('staffDef')}")
        octaves = int(transpose.findtext("octave-change", "0"))
        if (int(staff.get("trans.diat")), int(staff.get("trans.semi"))) != (
                int(transpose.findtext("diatonic")) + 7 * octaves,
                int(transpose.findtext("chromatic")) + 12 * octaves):
            raise ValueError("conversion changed instrument transposition")
