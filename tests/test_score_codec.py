from fractions import Fraction
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from experiments.full_page_omr.codec_fixtures import (
    alternatives, cross_staff, drums, fixtures, horn, note, piano, score, validate_all, validate_fixture, xml,
)
from experiments.full_page_omr.score_codec import (
    CodecError, PROFILE, VOCABULARY, VOCABULARY_SHA256, W2I, canonicalize, decode, encode, encode_with_metadata,
)
from experiments.full_page_omr.score_semantics import inspect_score


class ScoreCodecTests(unittest.TestCase):
    def test_all_original_and_generated_fixtures(self):
        for fixture in fixtures():
            with self.subTest(fixture=fixture.name):
                validate_fixture(fixture)

    def test_independent_voice_and_chord_onsets(self):
        part = inspect_score(decode(encode(piano().source)))["parts"][0]
        events = part["measures"][0]["events"]
        self.assertEqual([n["onset"] for n in events], ["0", "0", "2", "0", "0"])
        self.assertEqual([n["duration"] for n in events], ["2", "2", "2", "4", "4"])
        self.assertEqual([(n["voice"], n["staff"]) for n in events], [("1", "1")] * 3 + [("2", "1"), ("3", "2")])
        self.assertEqual([n["chord"] for n in events], [False, True, False, False, False])
        self.assertIn(("pedal", (0, "0"), (0, "4")), part["spans"])

    def test_cross_staff_voice_is_not_a_new_voice(self):
        events = inspect_score(decode(encode(cross_staff().source)))["parts"][0]["measures"][0]["events"]
        self.assertEqual([n["staff"] for n in events], ["2", "2", "1", "1", "1", "2"])
        self.assertEqual([n["voice"] for n in events], ["1"] * 5 + ["2"])
        self.assertEqual([n["onset"] for n in events], ["0", "1/2", "1", "3/2", "2", "0"])

    def test_horn_dots_tuplets_and_endpoint_identities(self):
        part = inspect_score(decode(encode(horn().source)))["parts"][0]
        self.assertEqual([n["duration"] for n in part["measures"][0]["events"]], ["7/4", "1/4", "2"])
        self.assertEqual([n["duration"] for n in part["measures"][1]["events"]], ["2", "1/3", "1/3", "1/3", "1"])
        for endpoint in [("tie", 2, 3), ("slur", 0, 6), ("glissando", 0, 1), ("tuplet", 4, 6)]:
            self.assertIn(endpoint, part["spans"])

    def test_drum_appearance_and_passage_instructions_without_sound_mapping(self):
        decoded = decode(encode(drums().source))
        root = ET.fromstring(decoded)
        self.assertEqual(len(root.findall(".//unpitched")), 6)
        self.assertEqual([n.text for n in root.findall(".//notehead")], ["x"] * 5)
        self.assertFalse(root.findall(".//score-instrument"))
        bars = root.findall("part/measure")
        self.assertEqual(bars[0].findtext("direction/direction-type/words"), "BRUSHES — light swing")
        self.assertEqual(bars[1].findtext("direction/direction-type/words"), "RIDE CYM. / B.D. on 1; fill →")

    def test_alternative_passes_and_page_breaks(self):
        decoded = decode(encode(alternatives().source))
        part = inspect_score(decoded)["parts"][0]
        self.assertEqual(part["playback"], ["1", "2", "3", "4", "5", "6"])
        self.assertEqual(len(ET.fromstring(decoded).findall(".//print[@new-page='yes']")), 1)
        self.assertEqual([bar["events"][0]["pitch"][0] for bar in part["measures"]], ["C", "D", "D", "E", "E", "A"])

    def test_unseen_unicode_and_literal_token_text(self):
        root = ET.fromstring(horn().source)
        instruction = root.find(".//words")
        instruction.text = '  Unseen: Māori 🎺 <eos> & "quoted"\nsecond line  '
        source = ET.tostring(root, encoding="unicode")
        encoded = encode(source)
        self.assertEqual(ET.fromstring(decode(encoded)).findtext(".//words"), instruction.text)
        self.assertEqual(len(VOCABULARY), len(W2I))

    def test_renderer_retains_coda_with_canonical_attribute_tokens(self):
        from experiments.full_page_omr.generate_parts import make_part
        from experiments.full_page_omr.musicxml_score import to_musicxml, musicxml_to_mei, normalize_mei, check_conversion
        source = decode(encode(to_musicxml(make_part(seed=7, scenario="ds_coda"))))
        check_conversion(source, normalize_mei(source, musicxml_to_mei(source)))

    def test_cue_and_direction_offset_preserved(self):
        root, _, bar = score("Cue", "Tenor")
        note(bar, "G", 5, 1, "quarter", voice=2, cue=True)
        note(bar, length=3, kind="half", dots=1, voice=2, rest=True)
        ET.SubElement(ET.SubElement(bar, "backup"), "duration").text = "48"
        note(bar, length=4, kind="whole", rest=True)
        direction = ET.SubElement(bar, "direction")
        ET.SubElement(ET.SubElement(direction, "direction-type"), "words").text = "Trumpet cue"
        ET.SubElement(direction, "offset").text = "-48"
        source = xml(root)
        decoded = decode(encode(source))
        self.assertEqual(inspect_score(source), inspect_score(decoded))
        self.assertIsNotNone(ET.fromstring(decoded).find(".//cue"))
        self.assertEqual(inspect_score(decoded)["parts"][0]["measures"][0]["directions"][0]["onset"], "0")

    def test_canonical_ids_attribute_order_and_division_scale(self):
        root = ET.fromstring(horn().source)
        expected = encode(xml(root))
        for node in root.iter():
            if node.get("id"):
                node.set("id", "renamed-" + node.get("id"))
            if node.tag in ("divisions", "duration", "offset"):
                node.text = str(Fraction(node.text) * 2)
            node.attrib = dict(reversed(list(node.attrib.items())))
        self.assertEqual(encode(xml(root)), expected)
        encoded = encode_with_metadata(horn().source)
        self.assertEqual(encoded.source_ids["source-part"], "id1")
        self.assertEqual(encoded.profile, PROFILE)
        self.assertEqual(encoded.vocabulary_sha256, VOCABULARY_SHA256)
        self.assertEqual(canonicalize(canonicalize(horn().source)), canonicalize(horn().source))

    def test_vocabulary_is_process_and_hash_seed_independent(self):
        hashes = []
        for seed in ("1", "1234"):
            process = subprocess.run([sys.executable, "-c",
                                      "from experiments.full_page_omr.score_codec import VOCABULARY_SHA256; print(VOCABULARY_SHA256)"],
                                     env={**os.environ, "PYTHONHASHSEED": seed}, capture_output=True, text=True, check=True)
            hashes.append(process.stdout.strip())
        self.assertEqual(hashes, [VOCABULARY_SHA256] * 2)
        self.assertEqual(W2I["<pad>"], 0)

    def test_three_staves_and_part_specific_instrument_references(self):
        root, _, bar = score("Three staves", "Keyboard", 3)
        note(bar, length=4, kind="whole", staff=3)
        self.assertEqual(inspect_score(decode(encode(xml(root))))["parts"][0]["measures"][0]["events"][0]["staff"], "3")
        root = ET.fromstring(drums().source)
        definition = root.find("part-list/score-part")
        instrument = ET.SubElement(definition, "score-instrument", id="ride")
        ET.SubElement(instrument, "instrument-name").text = "Ride cymbal"
        first = root.find("part/measure/note")
        first.insert(2, ET.Element("instrument", id="ride"))
        result = inspect_score(decode(encode(xml(root))))
        self.assertEqual(result["parts"][0]["measures"][0]["events"][0]["instrument"], "Ride cymbal")

    def test_unknown_elements_attributes_mixed_content_and_dtd_rejected(self):
        for change in ("unknown-tag", "unknown-attr", "mixed", "dtd"):
            root = ET.fromstring(piano().source)
            if change == "unknown-tag":
                ET.SubElement(root.find("part/measure/note"), "ornaments")
            elif change == "unknown-attr":
                root.find("part/measure/note").set("default-x", "10")
            elif change == "mixed":
                root.find("part/measure/note/pitch").tail = "lost text"
            source = xml(root)
            if change == "dtd":
                source = '<!DOCTYPE score-partwise [<!ENTITY test "value">]>' + source.split("?>", 1)[1]
            with self.subTest(change=change), self.assertRaises(CodecError):
                encode(source)

    def test_bad_rhythm_chords_staff_ids_and_spans_rejected(self):
        for change in ("duration", "overlap", "chord", "staff", "fractional-staff", "id", "slur", "tie", "backup", "pitch", "duplicate", "order"):
            root = ET.fromstring(piano().source)
            bar = root.find("part/measure")
            first = bar.find("note")
            if change == "duration":
                first.find("duration").text = "25"
            elif change == "overlap":
                for n in bar.findall("note"):
                    n.find("voice").text = "1"
            elif change == "chord":
                first.insert(0, ET.Element("chord"))
            elif change == "staff":
                first.find("staff").text = "3"
            elif change == "fractional-staff":
                first.find("staff").text = "1.0"
            elif change == "id":
                root.find("part").set("id", "missing")
            elif change in ("slur", "tie"):
                ET.SubElement(ET.SubElement(first, "notations"), "slur" if change == "slur" else "tied", type="start")
            elif change == "backup":
                bar.find("backup/duration").text = "99"
            elif change == "pitch":
                first.find("pitch/step").text = "H"
            elif change == "duplicate":
                ET.SubElement(first, "duration").text = "24"
            else:
                first.append(first.find("pitch"))
                first.remove(first.find("pitch"))
            with self.subTest(change=change), self.assertRaises(CodecError):
                encode(xml(root))

    def test_missing_navigation_target_and_unmatched_ending_rejected(self):
        for change in ("jump", "ending"):
            root = ET.fromstring(alternatives().source)
            if change == "jump":
                ET.SubElement(root.find("part/measure/direction"), "sound", dalsegno="missing")
            else:
                root.find(".//ending").set("number", "2")
            with self.subTest(change=change), self.assertRaises(CodecError):
                encode(xml(root))

    def test_malformed_streams_rejected(self):
        tokens = encode(piano().source)
        for bad in (tokens[:-1], tokens + [0], tokens[1:], tokens + tokens, [*tokens[:-1], len(VOCABULARY), tokens[-1]],
                    [*tokens[:1], W2I["<eos>"], *tokens[2:]], [True, *tokens[1:]]):
            with self.subTest(prefix=bad[:3], length=len(bad)), self.assertRaises(CodecError):
                decode(bad)
        index = tokens.index(W2I["V:quarter"]) if W2I["V:quarter"] in tokens else tokens.index(W2I["V:half"])
        bad = tokens[:index] + [W2I["B:ff"]] + tokens[index + 1:]
        with self.assertRaisesRegex(CodecError, "UTF-8"):
            decode(bad)
        literal = VOCABULARY[tokens[index]][2:]
        alternate = tokens[:index] + [W2I[f"B:{b:02x}"] for b in literal.encode()] + tokens[index + 1:]
        with self.assertRaisesRegex(CodecError, "noncanonical"):
            decode(alternate)

    def test_export_refuses_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "keep.txt"
            marker.write_text("preserve")
            with self.assertRaises(FileExistsError):
                validate_all(directory)
            self.assertEqual(marker.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
