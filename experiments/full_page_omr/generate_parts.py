"""Generate reproducible, complete synthetic horn parts without a model or dataset.

MusicXML is the canonical score; MEI and page images are derived artifacts.
Run: python -m experiments.full_page_omr.generate_parts --help
"""

import argparse
from dataclasses import dataclass, field, replace
from fractions import Fraction
import json
from pathlib import Path
import random
import xml.etree.ElementTree as ET


NS = "http://www.music-encoding.org/ns/mei"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
ET.register_namespace("", NS)


@dataclass
class Event:
    id: str
    # Duration in sixteenth notes; pitch is written pitch, None denotes a rest.
    sixteenths: int
    pitch: str | None
    octave: int = 4
    articulation: str | None = None
    measure_rest: bool = False
    slash: bool = False


@dataclass
class ChordSymbol:
    id: str
    onset: int
    root: str
    alter: int
    kind: str


@dataclass
class Measure:
    id: str
    number: int
    key: int  # signed number of sharps
    meter: tuple[int, int]
    events: list[Event]
    chords: list[ChordSymbol] = field(default_factory=list)


@dataclass
class Slur:
    id: str
    start: str
    end: str


@dataclass
class Simile:
    measures: list[str]
    sources: list[str]


@dataclass
class Part:
    schema_version: int
    seed: int
    instrument: str
    scenario: str
    measures: list[Measure]
    directions: list[dict]
    navigation: dict
    playback: list[str]
    slurs: list[Slur]
    multirests: list[list[str]]
    similes: list[Simile]
    system_breaks: list[str] | None = None
    page_breaks: list[str] | None = None


def make_part(seed=0, scenario="repeat", instrument="Tenor saxophone"):
    """Fixed 24-bar regression fixture; use scenarios.make_scenario for datasets."""
    if scenario not in ("repeat", "ds_coda", "endings"):
        raise ValueError("unknown navigation scenario")
    rng = random.Random(seed)
    keys = rng.sample([0, -1, -2, -3, 1, 2], 3)
    meters = rng.sample([(4, 4), (3, 4), (6, 8), (5, 4)], 3)
    measures = []
    pitch_index = rng.randrange(2, 7)
    for n in range(1, 25):
        section = (n - 1) // 8
        meter = meters[section]
        remaining = meter[0] * 16 // meter[1]
        events = []
        # Repeat phrase rhythms while varying pitch; syncopation arises from
        # eighth-note offsets followed by quarters or dotted quarters.
        motif = ([2, 4, 2, 4, 4], [4, 2, 2, 6, 2], [8, 4, 4],
                 [1, 1, 2, 4, 4, 4])[(n - 1) % 4]
        while remaining:
            length = min(motif[len(events) % len(motif)], remaining)
            pitch_index = max(0, min(10, pitch_index + rng.choice([-2, -1, 0, 1, 2])))
            pitch = "cdefgab"[pitch_index % 7]
            events.append(Event(f"m{n}-e{len(events) + 1}", length,
                                None if rng.random() < .15 else pitch,
                                4 + pitch_index // 7,
                                rng.choice([None, None, None, None, "acc", "stacc", "ten", "marc"])))
            remaining -= length
        measures.append(Measure(f"m{n}", n, keys[section], meter, events))
    # Include actual semibreve notes and duration rests only in meters that fit
    # four quarter-note beats; a full-bar rest is a separate semantic object.
    long_section = rng.choice([i for i, meter in enumerate(meters) if meter[0] * 16 // meter[1] >= 16])
    for offset, pitch in ((1, "c"), (3, None)):
        measure = measures[long_section * 8 + offset]
        total = measure.meter[0] * 16 // measure.meter[1]
        measure.events = [Event(f"{measure.id}-e1", 16, pitch)]
        if total > 16:
            measure.events.append(Event(f"{measure.id}-e2", total - 16, "d"))
    # Guarantee both a semiquaver note and rest in a rhythmically valid measure.
    measure = measures[0]
    index = next(i for i, event in enumerate(measure.events) if event.sixteenths >= 2)
    old = measure.events[index]
    replacement = [Event(old.id, 1, old.pitch or "c", old.octave),
                   Event(old.id + "-rest", 1, None)]
    if old.sixteenths > 2:
        replacement.append(Event(old.id + "-tail", old.sixteenths - 2, old.pitch, old.octave))
    measure.events[index:index + 1] = replacement
    # A quiet passage within one system, clear of signature changes/navigation.
    rest_start = rng.choice((4, 5))  # zero-based: measures 5 or 6
    rest_count = rng.randint(2, 7 - rest_start)
    multirests = [[m.id for m in measures[rest_start:rest_start + rest_count]]]
    for measure in measures[rest_start:rest_start + rest_count]:
        total = measure.meter[0] * 16 // measure.meter[1]
        measure.events = [Event(f"{measure.id}-e1", total, None, measure_rest=True)]
    # An independent full-bar rest outside the compressed passage.
    measure = measures[21]
    measure.events = [Event(f"{measure.id}-e1", measure.meter[0] * 16 // measure.meter[1],
                            None, measure_rest=True)]
    if scenario == "repeat":
        nav = dict(start="m1", end="m16", times=2)
        route = list(range(1, 17)) * 2 + list(range(17, 25))
    elif scenario == "endings":
        nav = dict(start="m1", first_ending=["m15", "m16"],
                   second_ending=["m17", "m18"], times=2)
        route = list(range(1, 17)) + list(range(1, 15)) + list(range(17, 25))
    else:
        nav = dict(segno="m3", to_coda="m10", ds="m16", coda="m19")
        route = list(range(1, 17)) + list(range(3, 11)) + list(range(19, 25))
    directions = [dict(measure="m1", kind="dir", text="Medium swing")]
    for index, n in enumerate((1, 9, 17)):
        directions.extend([dict(measure=f"m{n}", kind="reh", text="ABC"[index]),
                           dict(measure=f"m{n}", kind="dynam", text=["mf", "p", "f"][index])])
    similes = [Simile(["m3"], ["m2"]), Simile(["m13", "m14"], ["m11", "m12"])]
    repeat_bars = {mid for group in similes for mid in group.measures}
    # Improvisation has rhythmic placeholders and written chord symbols, never
    # invented melody pitches. Use dotted-quarter slashes in compound meter.
    from .musicxml_score import key_alter

    tonic = {0: "c", -1: "f", -2: "b", -3: "e", 1: "g", 2: "d"}[keys[2]]
    scale = "cdefgab"
    roots = [scale[(scale.index(tonic) + degree) % 7].upper() for degree in (1, 4, 0)]
    for index, measure in enumerate(measures[22:24]):
        beat = 6 if measure.meter == (6, 8) else 4
        total = measure.meter[0] * 16 // measure.meter[1]
        measure.events = [Event(f"{measure.id}-e{i + 1}", beat, None, slash=True)
                          for i in range(total // beat)]
        if index == 0:
            changes = [(0, roots[0], "minor-seventh"),
                       ((total // beat // 2) * beat, roots[1], "dominant")]
        else:
            changes = [(0, roots[2], "major-seventh")]
        measure.chords = [ChordSymbol(f"{measure.id}-h{i + 1}", onset, root,
                                      key_alter(root, measure.key), kind)
                          for i, (onset, root, kind) in enumerate(changes)]
    directions.append(dict(measure="m23", kind="dir", text="Solo — improvise"))
    slurs = []
    # Phrase fragments span consecutive pitched events, possibly across a bar,
    # but never across rests or four-measure phrase boundaries in this version.
    for offset in range(0, len(measures), 4):
        runs = []
        run = []
        for measure in measures[offset:offset + 4]:
            if measure.id in repeat_bars or measure.id in {mid for g in similes for mid in g.sources}:
                if len(run) >= 2:
                    runs.append(run)
                run = []
                continue
            for event in measure.events:
                if event.pitch is not None:
                    run.append(event)
                else:
                    if len(run) >= 2:
                        runs.append(run)
                    run = []
        if len(run) >= 2:
            runs.append(run)
        if runs and (offset == 0 or rng.random() < .65):
            run = rng.choice(runs)
            length = rng.randint(2, min(len(run), 5))
            start = rng.randrange(len(run) - length + 1)
            phrase = run[start:start + length]
            for event in phrase:
                event.articulation = None
            slurs.append(Slur(f"slur{len(slurs) + 1}", phrase[0].id, phrase[-1].id))
    # Guarantee first-version coverage, at varied positions outside legato groups.
    slurred = set()
    events = [e for m in measures for e in m.events]
    positions = {e.id: i for i, e in enumerate(events)}
    for slur in slurs:
        slurred.update(e.id for e in events[positions[slur.start]:positions[slur.end] + 1])
    detached = [e for m in measures if m.id not in repeat_bars for e in m.events
                if e.pitch and e.id not in slurred]
    rng.shuffle(detached)
    for event, articulation in zip(detached, ("acc", "stacc", "ten", "marc")):
        event.articulation = articulation
    by_id = {m.id: m for m in measures}
    for group in similes:
        for target, source in zip(group.measures, group.sources, strict=True):
            by_id[target].events = [replace(e, id=f"{target}-e{i + 1}")
                                    for i, e in enumerate(by_id[source].events)]
    part = Part(1, seed, instrument, scenario, measures, directions, nav,
                [f"m{n}" for n in route], slurs, multirests, similes)
    validate(part)
    return part


def validate(part):
    ids = set()
    for measure in part.measures:
        expected = Fraction(measure.meter[0] * 16, measure.meter[1])
        if sum(e.sixteenths for e in measure.events) != expected:
            raise ValueError(f"invalid duration in {measure.id}")
        for item in [measure, *measure.events]:
            if item.id in ids:
                raise ValueError(f"duplicate ID {item.id}")
            ids.add(item.id)
        if any(e.sixteenths not in (1, 2, 3, 4, 6, 8, 12, 16) and not e.measure_rest for e in measure.events):
            raise ValueError("unsupported duration")
        if any(e.measure_rest and (e.pitch is not None or len(measure.events) != 1)
               for e in measure.events):
            raise ValueError("full-measure rests must fill a silent measure")
        if any(e.articulation not in (None, "acc", "stacc", "ten", "marc") for e in measure.events):
            raise ValueError("unsupported articulation")
        if any(e.slash and (e.pitch is not None or e.measure_rest or e.articulation)
               for e in measure.events):
            raise ValueError("improvisation slashes must not specify melody pitches or articulations")
        for chord in measure.chords:
            onsets = {sum(e.sixteenths for e in measure.events[:i]) for i in range(len(measure.events))}
            if (chord.id in ids or len(chord.root) != 1 or chord.root not in "ABCDEFG" or chord.alter not in (-1, 0, 1)
                    or chord.kind not in ("minor-seventh", "dominant", "major-seventh")
                    or chord.onset not in onsets):
                raise ValueError("invalid chord symbol")
            ids.add(chord.id)
    events = [e for m in part.measures for e in m.events]
    positions = {e.id: i for i, e in enumerate(events)}
    occupied = set()
    for slur in part.slurs:
        if slur.id in ids or slur.start not in positions or slur.end not in positions:
            raise ValueError("invalid slur identity or endpoint")
        ids.add(slur.id)
        start, end = positions[slur.start], positions[slur.end]
        if start >= end or any(e.pitch is None for e in events[start:end + 1]):
            raise ValueError("slurs must span ordered, consecutive pitched notes")
        span = set(range(start, end + 1))
        if occupied & span:
            raise ValueError("overlapping slurs are not supported yet")
        occupied.update(span)
    if not set(part.playback) <= {m.id for m in part.measures}:
        raise ValueError("playback references missing measures")
    measure_positions = {m.id: i for i, m in enumerate(part.measures)}
    breaks = (set(part.system_breaks or []) | set(part.page_breaks or [])
              if part.system_breaks is not None else
              {m.id for i, m in enumerate(part.measures) if i and i % 4 == 0})
    occupied = set()
    anchors = {d["measure"] for d in part.directions}
    for value in part.navigation.values():
        if isinstance(value, str):
            anchors.add(value)
        elif isinstance(value, list):
            anchors.update(value)
    for group in part.multirests:
        if len(group) < 2 or any(mid not in measure_positions for mid in group):
            raise ValueError("invalid multibar rest members")
        positions = [measure_positions[mid] for mid in group]
        if positions != list(range(positions[0], positions[0] + len(group))):
            raise ValueError("multibar rest members must be consecutive")
        measures = [part.measures[i] for i in positions]
        for offset, measure in enumerate(measures):
            if (measure.id in occupied or measure.id in anchors
                    or (measure.key, measure.meter) != (measures[0].key, measures[0].meter)
                    or len(measure.events) != 1 or not measure.events[0].measure_rest
                    or (offset and measure.id in breaks)):
                raise ValueError("multibar rest must not hide notes, boundaries, or directions")
            occupied.add(measure.id)
    by_id = {m.id: m for m in part.measures}
    for group in part.similes:
        if len(group.measures) not in (1, 2) or len(group.measures) != len(group.sources):
            raise ValueError("simile must repeat one or two measures")
        start = measure_positions[group.measures[0]]
        if (group.sources != [m.id for m in part.measures[start - len(group.measures):start]]
                or group.measures != [m.id for m in part.measures[start:start + len(group.measures)]]):
            raise ValueError("simile must refer to the immediately preceding pattern")
        for target, source in zip(group.measures, group.sources, strict=True):
            a, b = by_id[target], by_id[source]
            if ((a.key, a.meter) != (b.key, b.meter) or
                    [replace(e, id="") for e in a.events] != [replace(e, id="") for e in b.events]):
                raise ValueError("simile underlying music does not match its source")


def to_mei(part):
    """Compatibility helper: always derive MEI through canonical MusicXML."""
    from .musicxml_score import to_musicxml, musicxml_to_mei, normalize_mei, check_conversion

    source = to_musicxml(part)
    mei = normalize_mei(source, musicxml_to_mei(source))
    check_conversion(source, mei)
    return mei


def render_musicxml(source, folder, png=False, *, engraving_options=None, resource_path=None):
    """Render an existing generated MusicXML score without regenerating its music.

    Supports the generator's current single-staff subset; conversion checks fail
    rather than silently accepting unsupported or lost features.
    """
    import verovio
    from .musicxml_score import musicxml_to_mei, normalize_mei, check_conversion, multirest_groups
    from .jazz_notation import simile_groups

    folder = Path(folder)
    mei = normalize_mei(source, musicxml_to_mei(source))
    check_conversion(source, mei)
    measure_ids = [m.get("id") for m in ET.fromstring(source).findall("part/measure")]
    groups = multirest_groups(source)
    similes = simile_groups(source)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "source.musicxml").write_text(source, encoding="utf-8")
    (folder / "source.mei").write_text(mei, encoding="utf-8")
    toolkit = verovio.toolkit()
    if resource_path is not None and not toolkit.setResourcePath(str(resource_path)):
        raise ValueError("Verovio rejected the font resource path")
    options = {"inputFrom": "mei", "breaks": "encoded", "pageWidth": 2100,
               "pageHeight": 2970, "scale": 40, "footer": "none"}
    options.update(engraving_options or {})
    if not toolkit.setOptions(options):
        raise ValueError("Verovio rejected engraving options")
    if not toolkit.loadData(mei):
        raise RuntimeError(f"Verovio rejected derived MEI for {folder}")
    pages = []
    locations = {}
    for page in range(1, toolkit.getPageCount() + 1):
        svg = toolkit.renderToSVG(page).replace('overflow="inherit"', 'overflow="visible"')
        # Some SVG viewers guess a legacy encoding without an XML declaration.
        if not svg.lstrip().startswith("<?xml"):
            svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg
        filename = f"page_{page:02d}.svg"
        (folder / filename).write_text(svg, encoding="utf-8")
        if png:
            import cairosvg

            cairosvg.svg2png(bytestring=svg.encode(), background_color="white",
                            output_width=1400, write_to=str(folder / f"page_{page:02d}.png"))
        svg_ids = {node.get("id") for node in ET.fromstring(svg).iter()}
        # A compressed rest has one visible measure, but every component bar
        # still belongs to that page and remains addressable in playback.
        for leader, members in groups.items():
            if leader in svg_ids:
                svg_ids.update(members)
        for leader, group in similes.items():
            if leader in svg_ids:
                svg_ids.update(group["measures"])
        rendered_measures = [mid for mid in measure_ids if mid in svg_ids]
        for mid in rendered_measures:
            if mid in locations:
                raise RuntimeError(f"measure rendered twice: {mid}")
            locations[mid] = page
        pages.append(dict(page=page, image=f"page_{page:02d}.png" if png else filename,
                          svg=filename, measures=rendered_measures))
    if set(locations) != set(measure_ids):
        raise RuntimeError("rendered measures do not match source MusicXML")
    layout = dict(source="source.musicxml", renderer=toolkit.getVersion(),
                  conversion_checked=True, pages=pages, measure_pages=locations,
                  multibar_rests=[dict(representative=leader, measures=members, page=locations[leader])
                                  for leader, members in groups.items()],
                  similes=[dict(representative=leader, **group, page=locations[leader])
                           for leader, group in similes.items()])
    if engraving_options is not None:
        layout["engraving"] = dict(options=options,
                                   effective_music_font=toolkit.getOptions()["font"])
    (folder / "layout.json").write_text(json.dumps(layout, indent=2), encoding="utf-8")
    return layout


def generate(output_dir, count=20, seed=0, png=False, profile="mixed", features=None,
             measures=None, pages=None, split="train"):
    """Generate feature-driven datasets, or the fixed regression fixtures."""
    import hashlib
    from collections import Counter
    from .musicxml_score import to_musicxml
    from .scenarios import plan_dataset, make_scenario, expand_features, observe_features, HOLDOUTS

    if count < 1:
        raise ValueError("count must be positive")
    if profile == "regression":
        if any(value is not None for value in (features, measures, pages)):
            raise ValueError("regression fixtures have fixed features and length")
        plans = [(seed + i, None) for i in range(count)]
        split = "regression"
    else:
        plans = plan_dataset(count, seed, profile, features, measures, pages, split)
    output = Path(output_dir)
    for path in [output / "manifest.json", *(output / f"part_{i + 1:04d}" for i in range(count))]:
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")
    records = []
    for index, (part_seed, spec) in enumerate(plans):
        part = (make_part(part_seed, ("repeat", "endings", "ds_coda")[index % 3]) if spec is None
                else make_scenario(part_seed, spec))
        source = to_musicxml(part)
        observed = observe_features(source)
        requested = set(observed) if spec is None else set(expand_features(spec.features))
        missing = requested - observed.keys()
        if missing:
            raise RuntimeError(f"scenario failed to generate requested features: {sorted(missing)}")
        if split == "train" and any(pair <= observed.keys() for pair in HOLDOUTS.values()):
            raise RuntimeError("actual training coverage contains a held-out combination")
        folder = output / f"part_{index + 1:04d}"
        layout = render_musicxml(source, folder, png)
        if spec is not None and len(layout["pages"]) != spec.pages:
            raise RuntimeError(f"expected {spec.pages} rendered pages, got {len(layout['pages'])}")
        page_map = layout["measure_pages"]
        nav = part.navigation
        dependency = ((nav.get("segno"), nav.get("ds")) if part.scenario == "ds_coda" else
                      (nav.get("start"), (nav.get("first_ending") or [nav.get("end")])[-1]))
        cross_page = bool(dependency[0] and page_map[dependency[0]] != page_map[dependency[1]])
        if spec is not None and spec.pages > 1 and part.scenario != "plain" and not cross_page:
            raise RuntimeError("requested document navigation did not cross a page boundary")
        metadata = dict(schema_version=3, source="source.musicxml", seed=part.seed,
                        dataset_seed=seed, split=split, profile=profile if spec is None else spec.profile,
                        composition_id=hashlib.sha256(source.encode()).hexdigest(),
                        scenario=part.scenario, requested_features=sorted(requested),
                        actual_features=sorted(observed), coverage=sorted(observed),
                        feature_locations={name: [dict(measure=mid, page=page_map[mid]) for mid in mids]
                                           for name, mids in observed.items()},
                        measure_count=len(part.measures), pages=len(layout["pages"]),
                        note_events=sum(len(m.events) for m in part.measures),
                        cross_page_navigation=cross_page, expected_playback=part.playback)
        (folder / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        records.append(dict(example=folder.name, **metadata))
        print(f"{folder}: {metadata['profile']}, {metadata['measure_count']} measures, {metadata['pages']} pages")
    manifest = dict(schema_version=1, seed=seed, split=split, examples=records,
                    profile_counts=dict(Counter(r["profile"] for r in records)),
                    actual_feature_counts=dict(Counter(f for r in records for f in r["actual_features"])),
                    note_events_by_profile={name: sum(r["note_events"] for r in records if r["profile"] == name)
                                            for name in sorted({r["profile"] for r in records})},
                    held_out_combinations={name: sorted(pair) for name, pair in HOLDOUTS.items()})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parent / "outputs/synthetic_parts_mixture")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--png", action="store_true", help="also rasterize pages (requires Cairo)")
    parser.add_argument("--source", type=Path, help="re-engrave an existing generated MusicXML score")
    parser.add_argument("--profile", choices=["mixed", "focused", "combined", "complete", "regression"], default="mixed")
    parser.add_argument("--features", help="comma-separated feature names; empty string gives ordinary music")
    parser.add_argument("--measures", type=int, help="written measure count for a single profile")
    parser.add_argument("--pages", type=int, help="encoded page count, independent of musical length")
    parser.add_argument("--split", choices=["train", "validation", "test"], default="train")
    args = parser.parse_args()
    if args.source:
        if any(value is not None for value in (args.features, args.measures, args.pages)):
            parser.error("--features, --measures, and --pages apply to generation, not --source")
        render_musicxml(args.source.read_text(encoding="utf-8"), args.output_dir, args.png)
    else:
        features = None if args.features is None else [f.strip() for f in args.features.split(",") if f.strip()]
        generate(args.output_dir, args.count, args.seed, args.png, args.profile,
                 features, args.measures, args.pages, args.split)


if __name__ == "__main__":
    main()
