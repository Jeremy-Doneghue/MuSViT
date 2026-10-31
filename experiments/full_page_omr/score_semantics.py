"""Exact timing, attachment and navigation checks for score_codec's v1 profile.

This is deliberately not a complete MusicXML validator or performance engine.
Nested repeats, combined D.S./repeats and partial/open score fragments are rejected.
"""

from fractions import Fraction
import re

from .score_codec import CodecError, CHILDREN, FREE_TEXT, parse, require


NOTE_LENGTHS = {"whole": Fraction(4), "half": Fraction(2), "quarter": Fraction(1),
                "eighth": Fraction(1, 2), "16th": Fraction(1, 4), "32nd": Fraction(1, 8),
                "64th": Fraction(1, 16), "breve": Fraction(8)}


def number(value, label, *, positive=False):
    try:
        result = Fraction(value)
    except (ValueError, TypeError, ZeroDivisionError) as error:
        raise CodecError(f"invalid {label}: {value!r}") from error
    require(not positive or result > 0, f"{label} must be positive")
    return result


def integer(value, label, minimum=None):
    require(isinstance(value, str) and re.fullmatch(r"[+-]?[0-9]+", value.strip()) is not None,
            f"invalid integer spelling for {label}: {value!r}")
    result = number(value, label)
    require(result.denominator == 1 and (minimum is None or result >= minimum), f"invalid integer {label}")
    return int(result)


def shape(node):
    """Written structure without source IDs or division-dependent tick values."""
    if node.tag in ("divisions", "duration", "offset"):
        return None
    return (node.tag, tuple(sorted((k, v) for k, v in node.attrib.items() if k != "id")),
            node.text if node.tag in FREE_TEXT else (node.text or "").strip(),
            tuple(shape(child) for child in node if child.tag not in ("duration", "divisions", "offset")))


def _fields(root):
    required = {"score-partwise": ["part-list", "part"], "part-list": ["score-part"],
                "score-part": ["part-name"], "part": ["measure"], "key": ["fifths"],
                "time": ["beats", "beat-type"], "clef": ["sign"], "transpose": ["chromatic"],
                "pitch": ["step", "octave"], "unpitched": ["display-step", "display-octave"],
                "note": ["duration"], "backup": ["duration"], "forward": ["duration"],
                "direction": ["direction-type"], "metronome": ["beat-unit", "per-minute"],
                "time-modification": ["actual-notes", "normal-notes"], "harmony": ["root", "kind"],
                "root": ["root-step"], "bass": ["bass-step"]}
    unordered = {"measure", "notations", "articulations", "direction-type", "dynamics"}
    for node in root.iter():
        if node.get("placement") is not None:
            require(node.get("placement") in ("above", "below"), "invalid placement")
        for attr in ("implicit", "new-system", "new-page", "print-object", "measure", "use-symbols",
                     "use-stems", "filled", "parentheses", "line", "sign", "cautionary", "editorial", "bracket"):
            if node.get(attr) is not None:
                require(node.get(attr) in ("yes", "no"), f"invalid boolean {attr}")
        if node.get("number") is not None and node.tag not in ("measure", "ending"):
            integer(node.get("number"), f"{node.tag} number", 1)
        for tag in required.get(node.tag, []):
            require(node.find(tag) is not None, f"missing {tag} in {node.tag}")
        if node.tag in CHILDREN and node.tag not in unordered:
            positions = [CHILDREN[node.tag].split().index(child.tag) for child in node]
            require(positions == sorted(positions), f"unsupported child order in {node.tag}")
        if node.tag in ("step", "root-step", "bass-step", "display-step"):
            require(node.text in tuple("CDEFGAB"), f"invalid pitch step in {node.tag}")
        if node.tag in ("octave", "display-octave"):
            require(0 <= integer(node.text, node.tag) <= 9, "octave outside 0–9")
        if node.tag in ("alter", "root-alter", "bass-alter"):
            require(-2 <= integer(node.text, node.tag) <= 2, "microtones/out-of-range alterations unsupported")
        if node.tag in ("voice", "staff", "staves", "actual-notes", "normal-notes"):
            integer(node.text, node.tag, 1)
        if node.tag in ("diatonic", "chromatic", "octave-change", "clef-octave-change", "line"):
            integer(node.text, node.tag)
        if node.tag in ("divisions", "duration"):
            integer(node.text, node.tag, 1)
        if node.tag == "offset":
            number(node.text, "offset")
        if node.tag == "type":
            require(node.text in NOTE_LENGTHS, f"unsupported note type {node.text}")
        if node.tag == "notehead":
            require(node.text in ("normal", "x", "diamond", "slash", "circle-x"), "unsupported notehead")
        if node.tag == "accidental":
            require(node.text in ("sharp", "flat", "natural", "double-sharp", "flat-flat"), "unsupported accidental")
        if node.tag == "stem":
            require(node.text in ("up", "down", "none", "double"), "invalid stem")
        if node.tag == "fifths":
            require(-7 <= integer(node.text, "fifths") <= 7, "unsupported key signature")
        if node.tag == "sign":
            require(node.text in ("G", "F", "C", "percussion"), "unsupported clef")
        if node.tag in ("per-minute",):
            number(node.text, "metronome tempo", positive=True)
        if node.tag == "sound" and node.get("tempo") is not None:
            number(node.get("tempo"), "playback tempo", positive=True)
        if node.tag == "direction-type":
            require(len(node) > 0 and len({n.tag for n in node}) == 1, "one direction-type family required")
        if node.tag in ("tie", "tied", "slur", "tuplet", "glissando", "slide", "dashes"):
            require(node.get("type") in ("start", "stop"), f"unsupported {node.tag} type")
        if node.tag == "wedge":
            require(node.get("type") in ("crescendo", "diminuendo", "stop"), "unsupported wedge type")
        if node.tag == "pedal":
            require(node.get("type") in ("start", "stop"), "unsupported pedal type")
        if node.tag == "beam":
            require(node.text in ("begin", "continue", "end", "forward hook", "backward hook"), "invalid beam")
        if node.tag in ("multiple-rest", "measure-repeat") and node.text:
            integer(node.text, node.tag, 1)
        if node.tag == "ending":
            require(node.get("type") in ("start", "stop", "discontinue"), "invalid ending type")
            passes(node.get("number"))
        if node.tag == "repeat":
            require(node.get("direction") in ("forward", "backward"), "invalid repeat direction")
            integer(node.get("times", "2"), "repeat times", 2)


def passes(text):
    require(bool(text), "missing ending/pass numbers")
    return {integer(x.strip(), "pass number", 1) for x in text.split(",")}


def navigation(measures):
    """Resolve the explicitly supported repeat/ending or D.S.-coda route."""
    pairs, endings, markers = {}, {}, {}
    start, active, used_endings = None, None, set()
    for index, bar in enumerate(measures):
        # Left starts apply before this measure, right stops after it.
        for line in bar.findall("barline"):
            repeat = line.find("repeat")
            if repeat is not None and repeat.get("direction") == "forward":
                require(start is None, "nested repeats unsupported")
                start = index
            end = line.find("ending")
            if end is not None and end.get("type") == "start":
                require(active is None, "overlapping endings unsupported")
                active = (index, passes(end.get("number")))
            if end is not None and end.get("type") != "start":
                require(active is not None and active[1] == passes(end.get("number")), "unmatched ending stop")
                first, allowed = active
                for member in range(first, index + 1):
                    require(member not in used_endings, "overlapping endings")
                    endings[member] = (index + 1, allowed)
                    used_endings.add(member)
                active = None
            if repeat is not None and repeat.get("direction") == "backward":
                pairs[index] = (start if start is not None else 0, int(repeat.get("times", "2")))
                start = None
        for sound in bar.findall("direction/sound"):
            for kind in ("segno", "coda"):
                if sound.get(kind):
                    key = kind, sound.get(kind)
                    require(key not in markers, "duplicate navigation marker")
                    markers[key] = index
    require(start is None and active is None, "unclosed repeat or ending")
    require(not endings or pairs, "endings without a repeat outside v1")
    sounds = [s for bar in measures for s in bar.findall("direction/sound")]
    jumps = [s for s in sounds if s.get("dalsegno")]
    require(len(jumps) <= 1 and not (jumps and pairs), "combined/multiple D.S. and repeats unsupported")
    for sound in sounds:
        for attr, target in (("dalsegno", "segno"), ("tocoda", "coda")):
            if sound.get(attr):
                require((target, sound.get(attr)) in markers, f"unresolved {attr} target")
    counters = {}
    repeat_starts = {first: last for last, (first, _) in pairs.items()}
    route, index, pass_number, jumped, coda_taken = [], 0, 1, False, False
    for _ in range(max(100, len(measures) * 32)):
        if index >= len(measures):
            return route
        if index in repeat_starts:
            pass_number = counters.get(repeat_starts[index], 1)
        if index in endings and pass_number not in endings[index][1]:
            index = endings[index][0]
            continue
        route.append(index)
        bar_sounds = measures[index].findall("direction/sound")
        destination = None
        for sound in bar_sounds:
            if sound.get("time-only") and pass_number not in passes(sound.get("time-only")):
                continue
            if sound.get("dalsegno") and not jumped:
                jumped, pass_number = True, 2
                destination = markers["segno", sound.get("dalsegno")]
            elif sound.get("tocoda") and jumped and not coda_taken:
                coda_taken = True
                destination = markers["coda", sound.get("tocoda")]
        if destination is not None:
            index = destination
        elif index in pairs:
            first, times = pairs[index]
            count = counters.get(index, 1)
            if count < times:
                counters[index] = count + 1
                pass_number, index = count + 1, first
            else:
                index += 1
        else:
            index += 1
    raise CodecError("navigation exceeded bounded traversal limit")


def inspect_root(root):
    _fields(root)
    declared = [p.get("id") for p in root.findall("part-list/score-part")]
    actual = [p.get("id") for p in root.findall("part")]
    require(all(declared) and declared == actual and len(set(declared)) == len(declared), "part IDs/order must match part-list")
    result = {"metadata": [shape(n) for n in root if n.tag != "part"], "parts": []}
    for part in root.findall("part"):
        descriptor = next(p for p in root.findall("part-list/score-part") if p.get("id") == part.get("id"))
        instruments = {n.get("id"): n.findtext("instrument-name") for n in descriptor.findall("score-instrument")}
        divisions, meter, staves = None, None, 1
        spans, ties, beams, note_index = {}, {}, {}, 0
        origin = Fraction()
        bars, endpoints = [], []
        def span(kind, key, start_stop, anchor):
            identity = kind, key
            if start_stop in ("start", "crescendo", "diminuendo"):
                require(identity not in spans, f"overlapping {kind} {key}")
                spans[identity] = anchor
            else:
                require(identity in spans, f"unmatched {kind} stop")
                endpoints.append((kind, spans.pop(identity), anchor))
        for mi, bar in enumerate(part.findall("measure")):
            require(bar.get("number") is not None, "missing printed measure number")
            cursor, end = Fraction(), Fraction()
            previous, last_end, events, directions = None, {}, [], []
            for child in bar:
                if child.tag == "attributes":
                    require(not events and cursor == 0, "mid-measure attribute changes outside v1")
                    if child.find("divisions") is not None:
                        divisions = number(child.findtext("divisions"), "divisions", positive=True)
                    if child.find("time") is not None:
                        beats = integer(child.findtext("time/beats"), "beats", 1)
                        unit = integer(child.findtext("time/beat-type"), "beat-type", 1)
                        require(unit & (unit - 1) == 0, "non-power-of-two beat unit")
                        meter = Fraction(beats * 4, unit)
                    staves = integer(child.findtext("staves", str(staves)), "staves", 1)
                elif child.tag in ("backup", "forward"):
                    require(divisions is not None, "missing divisions")
                    delta = number(child.findtext("duration"), "cursor duration", positive=True) / divisions
                    cursor += delta if child.tag == "forward" else -delta
                    require(cursor >= 0, "backup before measure start")
                    require(meter is None or cursor <= meter, "cursor beyond measure end")
                    previous = None
                elif child.tag == "note":
                    require(divisions is not None and meter is not None, "initial divisions/time required")
                    require(sum(child.find(t) is not None for t in ("pitch", "rest", "unpitched")) == 1, "note needs one pitch/rest/unpitched")
                    voice, staff = child.findtext("voice", "1"), child.findtext("staff", "1")
                    require(1 <= int(staff) <= staves, "note assigned to nonexistent staff")
                    duration = number(child.findtext("duration"), "note duration", positive=True) / divisions
                    chord = child.find("chord") is not None
                    if chord:
                        require(previous is not None and previous["voice"] == voice and previous["pitch"] is not None,
                                "chord needs preceding sounding note in same voice")
                        require(child.find("rest") is None and duration <= Fraction(previous["duration"]), "invalid chord duration/rest")
                        onset = Fraction(previous["onset"])
                    else:
                        onset = cursor
                        require(onset >= last_end.get(voice, 0), "overlapping notes require chord or independent voices")
                        cursor += duration
                        last_end[voice] = cursor
                    full_rest = child.find("rest[@measure='yes']") is not None
                    if full_rest:
                        require(onset == 0 and duration == meter, "invalid measure rest")
                    else:
                        kind = child.findtext("type")
                        require(kind in NOTE_LENGTHS, "written note type required")
                        expected = NOTE_LENGTHS[kind] * sum((Fraction(1, 2**i) for i in range(len(child.findall("dot")) + 1)), Fraction())
                        modification = child.find("time-modification")
                        if modification is not None:
                            expected *= Fraction(int(modification.findtext("normal-notes")), int(modification.findtext("actual-notes")))
                        require(duration == expected, "duration disagrees with written type/dots/tuplet")
                    pitch = child.find("pitch")
                    unpitched = child.find("unpitched")
                    written = ((pitch.findtext("step"), pitch.findtext("alter", "0"), pitch.findtext("octave")) if pitch is not None
                               else (("unpitched", unpitched.findtext("display-step"), unpitched.findtext("display-octave")) if unpitched is not None else None))
                    instrument = child.find("instrument")
                    if instrument is not None:
                        require(instrument.get("id") in instruments, "unknown score-instrument")
                    event = dict(index=note_index, onset=str(onset), duration=str(duration), voice=voice, staff=staff,
                                 pitch=written, chord=chord, written=shape(child),
                                 instrument=instruments.get(instrument.get("id")) if instrument is not None else None)
                    events.append(event)
                    previous, note_index = event, note_index + 1
                    end = max(end, onset + duration)
                    for marker in child.findall("notations/*"):
                        if marker.tag in ("slur", "tuplet", "glissando", "slide"):
                            span(marker.tag, marker.get("number", "1"), marker.get("type"), event["index"])
                    tie_types = {n.get("type") for n in child.findall("tie")}
                    drawn_ties = {n.get("type") for n in child.findall("notations/tied")}
                    require(not (tie_types and drawn_ties) or tie_types == drawn_ties, "tie/tied disagreement")
                    for kind in sorted(tie_types | drawn_ties, reverse=True):  # stop before start on a continuation
                        key = voice, written
                        if kind == "stop":
                            require(key in ties, "unmatched tie stop or changed pitch/voice")
                            first, expected_onset = ties.pop(key)
                            require(origin + onset == expected_onset, "noncontiguous tie")
                            endpoints.append(("tie", first, event["index"]))
                        else:
                            require(key not in ties and written is not None, "overlapping tie or tied rest")
                            ties[key] = event["index"], origin + onset + duration
                    for beam in child.findall("beam"):
                        key = voice, beam.get("number", "1")
                        if beam.text == "begin":
                            require(key not in beams, "overlapping beam")
                            beams[key] = event["index"]
                        elif beam.text in ("continue", "end"):
                            require(key in beams, "unmatched beam")
                            if beam.text == "end":
                                endpoints.append(("beam", beams.pop(key), event["index"]))
                elif child.tag in ("direction", "harmony"):
                    require(divisions is not None, "direction before divisions is outside profile")
                    onset = cursor + number(child.findtext("offset", "0"), "direction offset") / divisions
                    require(onset >= 0 and (meter is None or onset <= meter), "direction outside measure")
                    staff = child.findtext("staff", "1")
                    require(1 <= int(staff) <= staves, "direction on nonexistent staff")
                    directions.append(dict(onset=str(onset), staff=staff, written=shape(child)))
                    for marker in child.findall("direction-type/*"):
                        if marker.tag in ("wedge", "pedal", "dashes"):
                            span(marker.tag, (staff, marker.get("number", "1")), marker.get("type"), (mi, str(onset)))
            require(events and meter is not None, "empty measure or missing meter")
            extent = max(end, cursor)
            require(extent == meter or (bar.get("implicit") == "yes" and 0 < extent <= meter), "measure under/overfilled")
            bars.append(dict(number=bar.get("number"), length=str(extent), events=events, directions=directions,
                             structure=[shape(n) for n in bar if n.tag not in ("note", "backup", "forward", "direction", "harmony")]))
            origin += extent
        require(not spans and not ties and not beams, f"unclosed spans/ties/beams: {list(spans)}, {list(ties)}, {list(beams)}")
        route = navigation(part.findall("measure"))
        result["parts"].append(dict(name=descriptor.findtext("part-name"), measures=bars, spans=endpoints,
                                    playback=[bars[i]["number"] for i in route]))
    return result


def inspect_score(source):
    """Independent raw-score timing/structure summary, before canonicalization."""
    return inspect_root(parse(source))
