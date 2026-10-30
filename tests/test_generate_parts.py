import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from experiments.full_page_omr.generate_parts import make_part, to_mei, generate, validate, NS, render_musicxml, Slur, Event, Measure
from experiments.full_page_omr.musicxml_score import to_musicxml, check_conversion, key_alter, multirest_groups, beam_plan
from experiments.full_page_omr.jazz_notation import simile_groups


class SyntheticPartTests(unittest.TestCase):
    def test_duration_changes_and_reproducibility(self):
        for seed in range(100):
            part = make_part(seed)
            validate(part)
            self.assertEqual(part, make_part(seed))
            self.assertEqual(len({m.key for m in part.measures}), 3)
            self.assertEqual(len({m.meter for m in part.measures}), 3)
        part.measures[0].events[0].sixteenths += 1
        with self.assertRaises(ValueError):
            validate(part)

    def test_written_endings_and_playback(self):
        part = make_part(scenario="endings")
        self.assertEqual(part.playback.count("m1"), 2)
        self.assertEqual(part.playback.count("m15"), 1)
        self.assertEqual(part.playback.count("m17"), 1)
        root = ET.fromstring(to_mei(part))
        endings = root.findall(f".//{{{NS}}}ending")
        self.assertEqual([e.get("label") for e in endings], ["1.", "2."])
        self.assertEqual([e.get("type") for e in endings],
                         ["mscore-ending-1", "mscore-ending-2"])
        self.assertEqual([len(e.findall(f"{{{NS}}}measure")) for e in endings], [2, 2])

    def test_coda_route_skips_tail_after_return(self):
        route = make_part(scenario="ds_coda").playback
        self.assertEqual(route[15:19], ["m16", "m3", "m4", "m5"])
        self.assertEqual(route[23:26], ["m10", "m19", "m20"])
        self.assertNotIn("m17", route)

    def test_musescore_compatible_definitions(self):
        part = make_part(scenario="ds_coda")
        root = ET.fromstring(to_mei(part))
        definitions = root.findall(f".//{{{NS}}}scoreDef")
        for definition, measure in zip(definitions, part.measures[::8], strict=True):
            staff = definition.find(f".//{{{NS}}}staffDef")
            if staff is None:
                staff = definition
            meter = staff if definition is definitions[0] else definition
            self.assertEqual((int(meter.get("meter.count")), int(meter.get("meter.unit"))),
                             measure.meter)
            key = "0" if not measure.key else f"{abs(measure.key)}{'s' if measure.key > 0 else 'f'}"
            self.assertEqual(staff.get("keysig"), key)
        self.assertFalse(root.findall(f".//{{{NS}}}note[@artic]"))
        self.assertTrue(root.findall(f".//{{{NS}}}note/{{{NS}}}artic"))
        marks = root.findall(f".//{{{NS}}}repeatMark")
        self.assertEqual([m.get("func") for m in marks], ["segno", "coda", "dalSegno", "coda"])
        self.assertEqual(root.findall(f".//{{{NS}}}measure")[-1].get("right"), "end")

    def test_rendered_page_coverage_and_navigation(self):
        with tempfile.TemporaryDirectory() as directory:
            generate(directory, count=3, profile="regression")
            for index in range(1, 4):
                folder = Path(directory) / f"part_{index:04d}"
                layout = json.loads((folder / "layout.json").read_text())
                self.assertTrue((folder / "source.musicxml").exists())
                self.assertFalse((folder / "target.json").exists())
                metadata = json.loads((folder / "metadata.json").read_text())
                self.assertIn("expected_playback", metadata)
                self.assertNotIn("measures", metadata)
                self.assertEqual(len(layout["pages"]), 3)
                self.assertEqual(len(layout["measure_pages"]), 24)
                self.assertEqual(layout["measure_pages"]["m3"], 1)
                self.assertEqual(layout["measure_pages"]["m16"], 2)
                self.assertEqual(layout["measure_pages"]["m19"], 3)
                svg = (folder / "page_01.svg").read_text()
                self.assertIn("clef", svg)
                if index == 3:
                    # SMuFL segno must be an actual glyph, not a missing-font box.
                    self.assertIn("E047", svg)

    def test_musicxml_pitches_and_navigation(self):
        for scenario in ("repeat", "endings", "ds_coda"):
            part = make_part(4, scenario)
            root = ET.fromstring(to_musicxml(part))
            for bar, measure in zip(root.findall("part/measure"), part.measures, strict=True):
                for note, event in zip(bar.findall("note"), measure.events, strict=True):
                    if event.pitch:
                        self.assertEqual(int(note.findtext("pitch/alter")), key_alter(event.pitch, measure.key))
            self.assertEqual(root.findtext("part/measure/attributes/transpose/octave-change"), "-1")
            if scenario == "ds_coda":
                sounds = [(b.get("id"), s.attrib) for b in root.findall("part/measure")
                          for s in b.findall("direction/sound")]
                self.assertEqual(sounds, [("m3", {"segno": "segno-1"}),
                    ("m10", {"tocoda": "coda-1", "time-only": "2"}),
                    ("m16", {"dalsegno": "segno-1"}), ("m19", {"coda": "coda-1"})])

    def test_conversion_checks_reject_lost_features(self):
        part = make_part(scenario="ds_coda")
        source = to_musicxml(part)
        mei = to_mei(part)
        for feature in ("duration", "pitch", "meter", "navigation", "final"):
            root = ET.fromstring(mei)
            if feature == "duration":
                root.find(f".//{{{NS}}}note").set("dur", "1")
            elif feature == "pitch":
                root.find(f".//{{{NS}}}note").set("pname", "b")
            elif feature == "meter":
                root.find(f".//{{{NS}}}staffDef").set("meter.count", "11")
            elif feature == "navigation":
                root.find(f".//{{{NS}}}repeatMark").set("func", "fine")
            else:
                root.findall(f".//{{{NS}}}measure")[-1].set("right", "single")
            with self.subTest(feature=feature), self.assertRaises(ValueError):
                check_conversion(source, ET.tostring(root, encoding="unicode"))

    def test_conversion_across_feature_combinations(self):
        for seed in range(12):
            for scenario in ("repeat", "endings", "ds_coda"):
                with self.subTest(seed=seed, scenario=scenario):
                    part = make_part(seed, scenario)
                    check_conversion(to_musicxml(part), to_mei(part))

    def test_articulation_coverage_and_slur_fidelity(self):
        for seed in range(12):
            part = make_part(seed)
            validate(part)
            source = ET.fromstring(to_musicxml(part))
            articulations = {n.tag for n in source.findall("part/measure/note/notations/articulations/*")}
            self.assertEqual(articulations, {"accent", "staccato", "tenuto", "strong-accent"})
            self.assertTrue(part.slurs)
            mei = ET.fromstring(to_mei(part))
            self.assertEqual(sorted((s.get("startid"), s.get("endid")) for s in mei.findall(f".//{{{NS}}}slur")),
                             sorted(("#" + s.start, "#" + s.end) for s in part.slurs))
            first = mei.find(f".//{{{NS}}}slur")
            first.set("endid", "#missing-note")
            with self.assertRaisesRegex(ValueError, "slur endpoints"):
                check_conversion(to_musicxml(part), ET.tostring(mei, encoding="unicode"))

    def test_cross_page_slur_and_invalid_endpoint(self):
        part = make_part()
        start, end = part.measures[7].events[-1], part.measures[8].events[0]
        start.pitch = end.pitch = "c"
        part.slurs = [Slur("cross-page", start.id, end.id)]
        validate(part)
        check_conversion(to_musicxml(part), to_mei(part))
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "cross-page"
            render_musicxml(to_musicxml(part), folder)
            for page in (1, 2):
                svg = ET.fromstring((folder / f"page_{page:02d}.svg").read_text())
                self.assertTrue(any("slur" in n.get("class", "").split() for n in svg.iter()))
        end.pitch = None
        with self.assertRaisesRegex(ValueError, "pitched notes"):
            validate(part)

    def test_new_duration_and_rest_coverage(self):
        for seed in range(20):
            part = make_part(seed)
            source = ET.fromstring(to_musicxml(part))
            notes = source.findall("part/measure/note")
            for kind in ("16th", "whole"):
                self.assertTrue(any(n.findtext("type") == kind and n.find("pitch") is not None for n in notes))
                self.assertTrue(any(n.findtext("type") == kind and n.find("rest") is not None for n in notes))
            # A full-measure rest takes the current bar length, not always four beats.
            full = source.find("part/measure[@id='m22']/note")
            self.assertIsNotNone(full.find("rest[@measure='yes']"))
            self.assertIsNone(full.find("type"))
            meter = part.measures[21].meter
            self.assertEqual(int(full.findtext("duration")), meter[0] * 16 // meter[1])
            check_conversion(ET.tostring(source, encoding="unicode"), to_mei(part))

    def test_multibar_rest_keeps_canonical_bars_and_page_mapping(self):
        part = make_part()
        source = to_musicxml(part)
        groups = multirest_groups(source)
        self.assertEqual(list(groups.values()), part.multirests)
        self.assertEqual(len(ET.fromstring(source).findall("part/measure")), 24)
        mei = ET.fromstring(to_mei(part))
        compressed = mei.find(f".//{{{NS}}}multiRest")
        self.assertEqual(int(compressed.get("num")), len(part.multirests[0]))
        compressed.set("num", "99")
        with self.assertRaisesRegex(ValueError, "multibar rest count"):
            check_conversion(source, ET.tostring(mei, encoding="unicode"))
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "rest-variant"
            layout = render_musicxml(source, folder)
            for group in layout["multibar_rests"]:
                for mid in group["measures"]:
                    self.assertEqual(layout["measure_pages"][mid], group["page"])
                    self.assertIn(mid, layout["pages"][group["page"] - 1]["measures"])
            self.assertEqual(part.playback.count("m6"), 2)

    def test_multibar_rest_rejects_hidden_notes_and_changes(self):
        part = make_part()
        hidden = part.multirests[0][1]
        for feature in ("note", "signature", "page_break", "direction"):
            source = ET.fromstring(to_musicxml(part))
            bar = source.find(f"part/measure[@id='{hidden}']")
            if feature == "note":
                bar.find("note/rest").tag = "pitch"
            elif feature == "signature":
                ET.SubElement(bar, "attributes")
            elif feature == "page_break":
                ET.SubElement(bar, "print", {"new-page": "yes"})
            else:
                ET.SubElement(bar, "direction")
            with self.subTest(feature=feature), self.assertRaisesRegex(ValueError, "multibar rest hides"):
                multirest_groups(source)

    def test_reengrave_saved_score(self):
        with tempfile.TemporaryDirectory() as directory:
            source = to_musicxml(make_part(scenario="endings"))
            # Edits to the canonical score must survive re-engraving.
            source = source.replace("Medium swing", "Straight sixteenths")
            folder = Path(directory) / "variant"
            layout = render_musicxml(source, folder)
            self.assertEqual((folder / "source.musicxml").read_text(), source)
            self.assertIn("Straight sixteenths", (folder / "source.mei").read_text())
            self.assertEqual(len(layout["pages"]), 3)

    def test_svg_declares_utf8_and_preserves_unicode_title(self):
        source = to_musicxml(make_part()).replace("Synthetic jazz study", "Jazz étude")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "unicode"
            render_musicxml(source, folder)
            data = (folder / "page_01.svg").read_bytes()
            self.assertTrue(data.startswith(b'<?xml version="1.0" encoding="UTF-8"?>'))
            root = ET.fromstring(data)
            self.assertIn("Jazz étude — 0", "".join(root.itertext()))
            self.assertIn("étude —".encode("utf-8"), data)

    def test_beaming_respects_meter_and_rests(self):
        cases = [
            ((4, 4), [2] * 8, set(), [[0, 1], [2, 3], [4, 5], [6, 7]]),
            ((3, 4), [1] * 12, set(), [list(range(i, i + 4)) for i in (0, 4, 8)]),
            ((6, 8), [2] * 6, set(), [[0, 1, 2], [3, 4, 5]]),
            ((5, 4), [2] * 10, set(), [[i, i + 1] for i in (0, 2, 4, 6, 8)]),
            ((4, 4), [1, 1, 1, 1, 4, 4, 4], {1}, [[2, 3]]),
            ((4, 4), [2, 3, 1, 2, 8], set(), [[2, 3]]),
        ]
        for meter, durations, rests, expected in cases:
            with self.subTest(meter=meter, durations=durations, rests=rests):
                events = [Event(f"e{i}", d, None if i in rests else "c") for i, d in enumerate(durations)]
                plan = beam_plan(Measure("bar", 1, 0, meter, events))
                groups = []
                for i, event in enumerate(events):
                    value = dict(plan.get(event.id, [])).get(1)
                    if value == "begin":
                        groups.append([i])
                    elif value:
                        groups[-1].append(i)
                self.assertEqual(groups, expected)

    def test_mixed_beams_and_hooks(self):
        patterns = [
            ([1, 1, 2], {0: "begin", 1: "end"}),
            ([2, 1, 1], {1: "begin", 2: "end"}),
            ([1, 2, 1], {0: "forward hook", 2: "backward hook"}),
            ([3, 1], {1: "backward hook"}),
            ([1, 3], {0: "forward hook"}),
            ([1, 1, 1, 1], {0: "begin", 1: "continue", 2: "continue", 3: "end"}),
        ]
        for durations, expected in patterns:
            events = [Event(f"e{i}", d, "c") for i, d in enumerate(durations)]
            plan = beam_plan(Measure("bar", 1, 0, (4, 4), events))
            self.assertEqual({i: dict(plan.get(e.id, []))[2] for i, e in enumerate(events) if e.sixteenths == 1}, expected)

    def test_beam_conversion_and_rendering(self):
        part = make_part()
        source = to_musicxml(part)
        root = ET.fromstring(to_mei(part))
        beam = root.find(f".//{{{NS}}}beam")
        self.assertIsNotNone(beam)
        # Removing a beam while retaining its notes must fail the conversion check.
        for parent in root.iter():
            if beam in list(parent):
                index = list(parent).index(beam)
                parent.remove(beam)
                for offset, child in enumerate(list(beam)):
                    parent.insert(index + offset, child)
                break
        with self.assertRaisesRegex(ValueError, "beam groups"):
            check_conversion(source, ET.tostring(root, encoding="unicode"))
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "beamed"
            render_musicxml(source, folder)
            svg = ET.fromstring((folder / "page_01.svg").read_text())
            self.assertTrue(any("beam" in n.get("class", "").split() for n in svg.iter()))

    def test_similes_keep_music_and_render_correct_pattern(self):
        part = make_part()
        source = to_musicxml(part)
        groups = simile_groups(source)
        self.assertEqual(groups, {"m3": {"measures": ["m3"], "sources": ["m2"]},
                                 "m13": {"measures": ["m13", "m14"], "sources": ["m11", "m12"]}})
        mei = ET.fromstring(to_mei(part))
        self.assertEqual(len(mei.findall(f".//{{{NS}}}mRpt")), 1)
        symbol = mei.find(f".//{{{NS}}}multiRpt")
        self.assertEqual(symbol.get("num"), "2")
        symbol.set("num", "3")
        with self.assertRaisesRegex(ValueError, "simile pattern size"):
            check_conversion(source, ET.tostring(mei, encoding="unicode"))
        damaged = ET.fromstring(source)
        damaged.find("part/measure[@id='m14']/note/duration").text = "999"
        with self.assertRaisesRegex(ValueError, "underlying music"):
            simile_groups(damaged)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "similes"
            layout = render_musicxml(source, folder)
            for group in layout["similes"]:
                for mid in group["measures"]:
                    self.assertEqual(layout["measure_pages"][mid], group["page"])
            self.assertIn("E501", (folder / "page_02.svg").read_text())

    def test_improvisation_chords_and_slashes(self):
        for seed in range(12):
            part = make_part(seed)
            source = to_musicxml(part)
            mx = ET.fromstring(source)
            for bar in mx.findall("part/measure")[22:]:
                notes = bar.findall("note")
                self.assertTrue(all(n.find("pitch") is None and n.find("rest") is None for n in notes))
                self.assertTrue(all(n.findtext("notehead") == "slash" for n in notes))
                self.assertTrue(bar.findall("harmony"))
            mei = ET.fromstring(to_mei(part))
            chords = mei.findall(f".//{{{NS}}}harm")
            self.assertEqual(len(chords), 3)
            for feature in ("chord_text", "chord_position", "slash"):
                damaged = ET.fromstring(to_mei(part))
                chord = damaged.find(f".//{{{NS}}}harm")
                if feature == "chord_text":
                    chord.text = "Cwrong"
                elif feature == "chord_position":
                    chord.set("tstamp", "99")
                else:
                    damaged.find(f".//{{{NS}}}note[@head.shape='slash']").set("head.shape", "quarter")
                with self.subTest(seed=seed, feature=feature), self.assertRaises(ValueError):
                    check_conversion(source, ET.tostring(damaged, encoding="unicode"))


if __name__ == "__main__":
    unittest.main()
