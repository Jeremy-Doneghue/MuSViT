"""Feature-driven musical scenarios, sampling recipes, and measured coverage."""

from dataclasses import dataclass, replace
import random
import xml.etree.ElementTree as ET

from .generate_parts import ChordSymbol, Event, Measure, Part, Simile, Slur, validate
from .musicxml_score import key_alter

FEATURES = frozenset({
    "key_changes", "meter_changes", "accent", "staccato", "tenuto", "marcato",
    "slurs", "beams", "semiquavers", "semibreves", "duration_rests", "measure_rests",
    "multibar_rests", "one_bar_simile", "two_bar_simile", "chord_symbols",
    "improvisation_slashes", "repeat", "endings", "ds_coda",
})
ALIASES = {"articulations": {"accent", "staccato", "tenuto", "marcato"},
           "similes": {"one_bar_simile", "two_bar_simile"},
           "improvisation": {"improvisation_slashes", "chord_symbols"}}
NAVIGATION = {"repeat", "endings", "ds_coda"}
# Neither pair may occur anywhere in the training mixture, including long parts.
HOLDOUTS = {"validation": frozenset({"meter_changes", "two_bar_simile"}),
            "test": frozenset({"ds_coda", "improvisation_slashes"})}


def expand_features(features):
    result = set()
    for feature in features:
        result.update(ALIASES.get(feature, {feature}))
    unknown = result - FEATURES
    if unknown:
        raise ValueError(f"unknown features: {', '.join(sorted(unknown))}")
    if len(result & NAVIGATION) > 1:
        raise ValueError("choose at most one structural navigation feature")
    if "improvisation_slashes" in result:
        result.add("chord_symbols")
    return frozenset(result)


@dataclass(frozen=True)
class ScenarioSpec:
    profile: str
    features: tuple[str, ...]
    measures: int
    pages: int = 1

    def __post_init__(self):
        expand_features(self.features)
        if self.profile not in ("focused", "combined", "complete"):
            raise ValueError("unknown scenario profile")
        if self.measures < 4 or not 1 <= self.pages <= self.measures // 2:
            raise ValueError("need at least four measures and at least two measures per page")


def _place_blocks(rng, count, requested):
    sizes = {}
    for name, size in (("semiquavers", 1), ("semibreves", 2), ("measure_rests", 1),
                       ("multibar_rests", 2), ("one_bar_simile", 2), ("two_bar_simile", 4),
                       ("improvisation_slashes", 2)):
        if name in requested:
            sizes[name] = size
    if "chord_symbols" in requested and "improvisation_slashes" not in requested:
        sizes["chord_symbols"] = 1
    navigation = next(iter(requested & NAVIGATION), "plain")
    needed = sum(sizes.values()) + {"plain": 1, "repeat": 2, "endings": 5, "ds_coda": 4}[navigation] + 1
    if count < needed:
        raise ValueError(f"requested features need at least {max(4, needed)} measures")
    for _ in range(128):
        anchors = {}
        if navigation == "repeat":
            anchors = dict(start=rng.randrange(max(1, count // 4)),
                           end=rng.randrange(max(2, count * 2 // 3), count))
        elif navigation == "ds_coda":
            # Jittered ordered anchors span the part, with room for a return jump.
            choices = sorted(rng.sample(range(count), 4))
            anchors = dict(zip(("segno", "to_coda", "ds", "coda"), choices))
        elif navigation == "endings":
            first = rng.randrange(0, max(1, count // 4))
            ending = rng.randrange(max(first + 2, count // 2), count - 3)
            anchors = dict(start=first, first=ending, first_end=ending + 1,
                           second=ending + 2, second_end=ending + 3)
        occupied = {0, *anchors.values()}
        blocks = {}
        items = list(sizes.items())
        rng.shuffle(items)
        # Largest blocks first reduces fragmentation without fixing their location.
        items.sort(key=lambda item: -item[1])
        for name, size in items:
            candidates = [i for i in range(1, count - size + 1)
                          if not (set(range(i, i + size)) & occupied)
                          and (name not in ("multibar_rests", "one_bar_simile", "two_bar_simile") or i + size < count)]
            if not candidates:
                break
            start = rng.choice(candidates)
            blocks[name] = list(range(start, start + size))
            occupied.update(blocks[name])
        if len(blocks) == len(sizes):
            return navigation, anchors, blocks
    raise ValueError("features cannot fit safely at this length; increase --measures")


def make_scenario(seed, spec):
    rng = random.Random(seed)
    requested = expand_features(spec.features)
    navigation, anchors, blocks = _place_blocks(rng, spec.measures, requested)
    count = spec.measures
    interiors = {i for block in blocks.values() for i in block[1:]}
    boundaries = [i for i in range(1, count) if i not in interiors]
    key_change = rng.choice(boundaries) if "key_changes" in requested else count
    meter_change = rng.choice(boundaries) if "meter_changes" in requested else count
    initial_key = rng.choice([0, -1, -2, -3, 1, 2])
    next_key = rng.choice([k for k in (0, -1, -2, -3, 1, 2) if k != initial_key])
    initial_meter = (4, 4) if "semibreves" in requested else rng.choice([(4, 4), (3, 4), (6, 8), (5, 4)])
    next_meter = (5, 4) if "semibreves" in requested else rng.choice(
        [m for m in ((4, 4), (3, 4), (6, 8), (5, 4)) if m != initial_meter])
    if next_meter == initial_meter:
        next_meter = (4, 4)
    measures = []
    pitch_index = rng.randrange(3, 7)
    # Phrase motifs are shared within each four-bar phrase, rather than sampled
    # independently for every event. Ordinary passages have no rare decorations.
    motifs = [rng.choice(([4, 4, 4, 4], [2, 2, 4, 2, 2, 4], [4, 2, 2, 4, 4]))
              for _ in range((count + 3) // 4)]
    for index in range(count):
        key = initial_key if index < key_change else next_key
        meter = initial_meter if index < meter_change else next_meter
        remaining = meter[0] * 16 // meter[1]
        events = []
        motif = motifs[index // 4]
        while remaining:
            duration = min(motif[len(events) % len(motif)], remaining)
            pitch_index = max(0, min(10, pitch_index + rng.choice([-1, 0, 1, 1, 2])))
            events.append(Event(f"m{index + 1}-e{len(events) + 1}", duration,
                                None if rng.random() < .1 else "cdefgab"[pitch_index % 7],
                                4 + pitch_index // 7))
            remaining -= duration
        measures.append(Measure(f"m{index + 1}", index + 1, key, meter, events))

    def fill(index, durations, pitches):
        measure = measures[index]
        measure.events = [Event(f"{measure.id}-e{i + 1}", duration, pitch)
                          for i, (duration, pitch) in enumerate(zip(durations, pitches, strict=True))]

    def full_rest(index):
        measure = measures[index]
        measure.events = [Event(f"{measure.id}-e1", measure.meter[0] * 16 // measure.meter[1],
                                None, measure_rest=True)]

    if "semiquavers" in blocks:
        index = blocks["semiquavers"][0]
        total = measures[index].meter[0] * 16 // measures[index].meter[1]
        durations = [1, 1, 1, 1] + [4] * ((total - 4) // 4)
        fill(index, durations, ["c", "d", None, "e"] + ["f"] * (len(durations) - 4))
    for index, pitch in zip(blocks.get("semibreves", []), ("c", None)):
        total = measures[index].meter[0] * 16 // measures[index].meter[1]
        fill(index, [16] + ([4] if total > 16 else []), [pitch] + (["d"] if total > 16 else []))
    for index in blocks.get("measure_rests", []):
        full_rest(index)
    multirests = []
    if "multibar_rests" in blocks:
        members = blocks["multibar_rests"]
        for index in members:
            full_rest(index)
        multirests = [[measures[i].id for i in members]]
    similes = []
    for name, size in (("one_bar_simile", 1), ("two_bar_simile", 2)):
        if name in blocks:
            members = blocks[name]
            similes.append(Simile([measures[i].id for i in members[size:]],
                                  [measures[i].id for i in members[:size]]))
    directions = [dict(measure="m1", kind="dir", text=rng.choice(["Medium swing", "Swing", "Straight eighths"]))]
    if "improvisation_slashes" in blocks or "chord_symbols" in blocks:
        members = blocks.get("improvisation_slashes", blocks.get("chord_symbols"))
        for number, index in enumerate(members):
            measure = measures[index]
            total = measure.meter[0] * 16 // measure.meter[1]
            beat = 6 if measure.meter == (6, 8) else 4
            if "improvisation_slashes" in requested:
                measure.events = [Event(f"{measure.id}-e{i + 1}", beat, None, slash=True) for i in range(total // beat)]
            tonic = {0: "c", -1: "f", -2: "b", -3: "e", 1: "g", 2: "d"}[measure.key]
            degree = (1, 4, 0)[number % 3] if len(members) > 2 else (1 if number == 0 else 0)
            root = "cdefgab"[("cdefgab".index(tonic) + degree) % 7].upper()
            kind = "minor-seventh" if number == 0 else "major-seventh"
            measure.chords = [ChordSymbol(f"{measure.id}-h1", 0, root, key_alter(root, measure.key), kind)]
            if number == 0 and "improvisation_slashes" in requested:
                root = "cdefgab"[("cdefgab".index(tonic) + 4) % 7].upper()
                onset = (total // beat // 2) * beat
                measure.chords.append(ChordSymbol(f"{measure.id}-h2", onset, root, key_alter(root, measure.key), "dominant"))
        directions.append(dict(measure=measures[members[0]].id, kind="dir", text="Solo — improvise" if "improvisation_slashes" in requested else "Melody"))
    allocated = {i for block in blocks.values() for i in block}
    ordinary = [i for i in range(count) if i not in allocated]
    if "beams" in requested:
        index = rng.choice(ordinary)
        total = measures[index].meter[0] * 16 // measures[index].meter[1]
        fill(index, [2] * (total // 2), ["c", "d"] * (total // 4))
    slurs = []
    if "slurs" in requested:
        measure = measures[rng.choice(ordinary)]
        for event in measure.events[:2]:
            event.pitch = event.pitch or "c"
        slurs = [Slur("slur1", measure.events[0].id, measure.events[1].id)]
    slurred_ids = {mid for s in slurs for mid in (s.start, s.end)}
    simile_targets = {mid for group in similes for mid in group.measures}
    detached = [e for m in measures if m.id not in simile_targets
                for e in m.events if e.pitch and e.id not in slurred_ids]
    rng.shuffle(detached)
    for name, code in (("accent", "acc"), ("staccato", "stacc"), ("tenuto", "ten"), ("marcato", "marc")):
        if name in requested:
            if not detached:
                raise ValueError("not enough detached notes for requested articulations")
            detached.pop().articulation = code
    if "duration_rests" in requested and not any(e.pitch is None and not e.slash and not e.measure_rest for m in measures for e in m.events):
        measure = measures[rng.choice(ordinary)]
        event = next(e for e in reversed(measure.events) if e.id not in slurred_ids and e.articulation is None)
        event.pitch = None
    by_id = {m.id: m for m in measures}
    for group in similes:
        for target, source in zip(group.measures, group.sources, strict=True):
            by_id[target].events = [replace(e, id=f"{target}-e{i + 1}") for i, e in enumerate(by_id[source].events)]
    nav = {}
    route = list(range(count))
    if navigation == "repeat":
        start, end = anchors["start"], anchors["end"]
        nav = dict(start=measures[start].id, end=measures[end].id, times=2)
        route = list(range(end + 1)) + list(range(start, end + 1)) + list(range(end + 1, count))
    elif navigation == "ds_coda":
        segno, to_coda, ds, coda = (anchors[k] for k in ("segno", "to_coda", "ds", "coda"))
        nav = {k: measures[v].id for k, v in anchors.items()}
        route = list(range(ds + 1)) + list(range(segno, to_coda + 1)) + list(range(coda, count))
    elif navigation == "endings":
        start, first, second = (anchors[k] for k in ("start", "first", "second"))
        nav = dict(start=measures[start].id,
                   first_ending=[measures[i].id for i in range(first, anchors["first_end"] + 1)],
                   second_ending=[measures[i].id for i in range(second, anchors["second_end"] + 1)], times=2)
        route = list(range(anchors["first_end"] + 1)) + list(range(start, first)) + list(range(second, count))
    # Musical dependencies and page count are independent. Page breaks cannot
    # split compressed symbols; navigation scenarios with multiple pages force
    # at least one of their relationships to cross a page boundary.
    collapsed_interiors = set(blocks.get("multibar_rests", [])[1:])
    if "two_bar_simile" in blocks:
        collapsed_interiors.add(blocks["two_bar_simile"][-1])
    allowed = [i for i in range(1, count) if i not in collapsed_interiors]
    page_breaks = []
    if spec.pages > 1 and navigation != "plain":
        lower = min(anchors.values())
        upper = anchors.get("ds", anchors.get("end", anchors.get("first")))
        candidates = [i for i in allowed if lower < i <= upper and 2 <= i <= count - 2]
        if not candidates:
            candidates = [i for i in allowed if lower < i <= upper]
        page_breaks.append(rng.choice(sorted(candidates, key=lambda i: abs(i - count / spec.pages))[:3]))
    while len(page_breaks) < spec.pages - 1:
        slot = (len(page_breaks) + 1) * count / spec.pages
        candidates = [i for i in allowed if all(abs(i - edge) >= 2 for edge in [0, count, *page_breaks])]
        if not candidates:
            raise ValueError("not enough safe page-break locations for requested page count")
        nearest = sorted(candidates, key=lambda i: abs(i - slot))[:max(1, count // 5)]
        page_breaks.append(rng.choice(nearest))
    systems = []
    cursor = rng.randint(3, 4)
    while cursor < count:
        if cursor in allowed:
            systems.append(cursor)
        cursor += rng.randint(3, 4)
    part = Part(2, seed, "Tenor saxophone", navigation, measures, directions, nav,
                [measures[i].id for i in route], slurs, multirests, similes,
                [measures[i].id for i in sorted(set(systems) | set(page_breaks))],
                [measures[i].id for i in sorted(page_breaks)])
    validate(part)
    return part


def observe_features(source):
    """Measure coverage from the exported score, not from the requested recipe."""
    root = ET.fromstring(source)
    from .musicxml_score import multirest_groups
    from .jazz_notation import simile_groups

    # Underlying notes in abbreviated bars are not visible recognition targets.
    hidden_notes = {mid for group in multirest_groups(root).values() for mid in group}
    hidden_notes.update(mid for group in simile_groups(root).values() for mid in group["measures"])
    locations = {}

    def found(name, mid):
        if mid not in locations.setdefault(name, []):
            locations[name].append(mid)

    key = meter = None
    for bar in root.findall("part/measure"):
        mid = bar.get("id")
        new_key = bar.findtext("attributes/key/fifths", key)
        time = bar.find("attributes/time")
        new_meter = (time.findtext("beats"), time.findtext("beat-type")) if time is not None else meter
        if key is not None and key != new_key:
            found("key_changes", mid)
        if meter is not None and meter != new_meter:
            found("meter_changes", mid)
        key, meter = new_key, new_meter
        for note in ([] if mid in hidden_notes else bar.findall("note")):
            if note.find("pitch") is not None:
                found("notes", mid)
            kind = note.findtext("type")
            if kind in ("16th", "whole", "eighth", "quarter"):
                found({"16th": "semiquavers", "whole": "semibreves", "eighth": "quavers", "quarter": "crotchets"}[kind], mid)
            if note.find("rest") is not None:
                found("measure_rests" if note.find("rest").get("measure") == "yes" else "duration_rests", mid)
            if note.findtext("notehead") == "slash":
                found("improvisation_slashes", mid)
            for name in ("accent", "staccato", "tenuto", "strong-accent"):
                if note.find(f"notations/articulations/{name}") is not None:
                    found("marcato" if name == "strong-accent" else name, mid)
            if note.find("notations/slur") is not None:
                found("slurs", mid)
            if note.find("beam") is not None:
                found("beams", mid)
        if bar.find("harmony") is not None:
            found("chord_symbols", mid)
        if bar.find("attributes/measure-style/multiple-rest") is not None:
            found("multibar_rests", mid)
        repeat = bar.find("attributes/measure-style/measure-repeat[@type='start']")
        if repeat is not None:
            found("one_bar_simile" if repeat.text == "1" else "two_bar_simile", mid)
        if bar.find("barline/repeat") is not None:
            found("repeat", mid)
        if bar.find("barline/ending") is not None:
            found("endings", mid)
        if any("dalsegno" in s.attrib for s in bar.findall("direction/sound")):
            found("ds_coda", mid)
    return dict(sorted(locations.items()))


def plan_dataset(count, seed=0, profile="mixed", features=None, measures=None, pages=None, split="train"):
    """Reproducible 50/35/15 sampling with composition-level split seed domains."""
    import hashlib
    import math

    if count < 1 or split not in ("train", "validation", "test"):
        raise ValueError("count must be positive; split must be train, validation, or test")
    if profile not in ("mixed", "focused", "combined", "complete"):
        raise ValueError("unknown dataset profile")
    if profile == "mixed" and any(value is not None for value in (features, measures, pages)):
        raise ValueError("select a single --profile when specifying features, measures, or pages")
    domain_seed = int.from_bytes(hashlib.sha256(f"{seed}:{split}".encode()).digest()[:8], "big")
    rng = random.Random(domain_seed)
    if profile == "mixed":
        weights = {"focused": .5, "combined": .35, "complete": .15}
        amounts = {name: math.floor(count * weight) for name, weight in weights.items()}
        order = sorted(weights, key=lambda name: -(count * weights[name] - amounts[name]))
        for name in order[:count - sum(amounts.values())]:
            amounts[name] += 1
        profiles = [name for name, amount in amounts.items() for _ in range(amount)]
        rng.shuffle(profiles)
    else:
        profiles = [profile] * count
    recipes = [
        ("key_changes", "multibar_rests"), ("semiquavers", "slurs"),
        ("tenuto", "marcato", "beams"), ("improvisation_slashes", "key_changes"),
        ("one_bar_simile", "semiquavers"), ("repeat", "slurs"),
        ("meter_changes", "multibar_rests"), ("endings", "accent"),
        ("semibreves", "one_bar_simile"),
    ]
    focused_count = 0
    result = []
    for index, group in enumerate(profiles):
        for _ in range(128):
            if features is not None:
                selected = expand_features(features)
            elif group == "focused":
                selected = frozenset() if focused_count % 5 == 0 else expand_features([rng.choice(sorted(FEATURES))])
            elif group == "combined":
                selected = expand_features(HOLDOUTS[split] if split != "train" else rng.choice(recipes))
            else:
                pool = sorted(FEATURES - NAVIGATION)
                chosen = set(rng.sample(pool, rng.randint(3, 6)))
                if rng.random() < .75:
                    chosen.add(rng.choice(sorted(NAVIGATION)))
                if split != "train":
                    chosen.difference_update(NAVIGATION)
                    chosen.update(HOLDOUTS[split])
                selected = expand_features(chosen)
            if split != "train" or not any(pair <= selected for pair in HOLDOUTS.values()):
                break
            if features is not None:
                raise ValueError("requested combination is reserved for validation/test; choose that --split")
        else:
            raise ValueError("could not sample a compatible feature combination")
        if group == "focused":
            focused_count += 1
        # Allow room for plain context and safely separated symbols.
        budget = (1 if "semiquavers" in selected else 0) + (2 if "semibreves" in selected else 0)
        budget += sum(size for name, size in (("measure_rests", 1), ("multibar_rests", 2),
                      ("one_bar_simile", 2), ("two_bar_simile", 4), ("improvisation_slashes", 2)) if name in selected)
        budget += 1 if "chord_symbols" in selected and "improvisation_slashes" not in selected else 0
        budget += 8 if selected & NAVIGATION else 4
        length = measures if measures is not None else (
            max(budget, rng.choice([4, 6, 8])) if group == "focused" else
            max(budget, rng.choice([12, 16, 20])) if group == "combined" else rng.choice([32, 40, 48, 64]))
        page_count = pages if pages is not None else (
            rng.choice([3, 4]) if group == "complete" else
            2 if selected & NAVIGATION or (group == "combined" and rng.random() < .35) else 1)
        part_seed = int.from_bytes(hashlib.sha256(f"{seed}:{split}:{index}".encode()).digest()[:8], "big")
        result.append((part_seed, ScenarioSpec(group, tuple(sorted(selected)), length, page_count)))
    return result
