"""Exercise the annotation boundary: drafts, approval, persistence and export."""

import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from PIL import Image, ImageDraw

import server
from segmentation import detect_regions


XML = ('<score-partwise version="4.0"><part-list><score-part id="P1">'
       '<part-name>Alto sax</part-name></score-part></part-list><part id="P1">'
       '<measure number="1"><attributes><divisions>1</divisions></attributes>'
       '<note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration>'
       '<type>quarter</type></note></measure></part></score-partwise>')


def page_image():
    image = Image.new("RGB", (800, 300), "white")
    draw = ImageDraw.Draw(image)
    for y in range(80, 121, 10):
        draw.line((50, y, 750, y), fill="black", width=2)
    for x in [250, 450, 750]:
        draw.line((x, 80, x, 121), fill="black", width=2)
    # A note stem should not become a bar boundary.
    draw.line((310, 92, 310, 116), fill="black", width=2)
    return image


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = server.DATA
        server.DATA = Path(self.temp.name) / "data"
        server.initialize()
        self.source = Path(self.temp.name) / "scan.png"
        page_image().save(self.source)
        self.original = self.source.read_bytes()
        self.doc = server.import_scan(self.source)
        self.region = self.doc["regions"][0]

    def tearDown(self):
        server.DATA = self.previous
        self.temp.cleanup()

    def test_segmentation_ignores_short_note_stem(self):
        regions = detect_regions(page_image())
        self.assertEqual(len(regions), 3)
        self.assertTrue(all(r["detection"] == "unverified" for r in regions))

    def test_reimport_reuses_document_without_changing_original(self):
        self.assertEqual(server.import_scan(self.source)["id"], self.doc["id"])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_draft_persists_but_is_not_exported_as_training_pair(self):
        server.update_region(self.doc["id"], self.region["id"],
                             {"musicxml": XML, "notes": "Check the accidental"})
        restored = server.get_document(self.doc["id"])
        self.assertEqual(restored["regions"][0]["notes"], "Check the accidental")
        with zipfile.ZipFile(io.BytesIO(server.export_dataset(restored))) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["examples"], [])
            self.assertFalse(any(n.startswith("examples/") for n in archive.namelist()))

    def test_approval_requires_transcription_and_confirmed_context(self):
        for payload in [{"status": "reviewed"}, {"status": "reviewed", "musicxml": XML}]:
            with self.assertRaises(ValueError):
                server.update_region(self.doc["id"], self.region["id"], payload)
        self.assertEqual(server.get_document(self.doc["id"])["regions"][0]["status"], "pending")

    def test_reviewed_pair_export_includes_image_musicxml_and_context(self):
        context = {**server.DEFAULT_CONTEXT, "instrument": "Alto sax", "transpose": -9, "confirmed": True}
        updated = server.update_region(self.doc["id"], self.region["id"],
            {"status": "reviewed", "musicxml": XML, "context": context, "box": [55, 20, 245, 160]})
        with zipfile.ZipFile(io.BytesIO(server.export_dataset(updated))) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            example = manifest["examples"][0]
            self.assertEqual(example["context"]["transpose"], -9)
            self.assertEqual(archive.read(example["musicxml"]).decode(), XML)
            with Image.open(io.BytesIO(archive.read(example["image"]))) as image:
                self.assertEqual(image.size, (190, 140))

    def test_bad_crop_and_skip_never_become_approved(self):
        for status in ["bad_crop", "skipped", "unclear"]:
            updated = server.update_region(self.doc["id"], self.region["id"], {"status": status})
            self.assertEqual(updated["regions"][0]["status"], status)
        with self.assertRaises(ValueError):
            server.update_region(self.doc["id"], self.region["id"], {"box": [-1, 0, 100, 100]})

    def test_invalid_xml_does_not_replace_saved_draft(self):
        server.update_region(self.doc["id"], self.region["id"], {"musicxml": XML})
        with self.assertRaises(ValueError):
            server.update_region(self.doc["id"], self.region["id"], {"musicxml": "<html/>"})
        self.assertEqual(server.get_document(self.doc["id"])["regions"][0]["musicxml"], XML)

    def test_editing_reviewed_notation_requires_approval_again(self):
        context = {**server.DEFAULT_CONTEXT, "confirmed": True}
        server.update_region(self.doc["id"], self.region["id"],
                             {"status": "reviewed", "musicxml": XML, "context": context})
        updated = server.update_region(self.doc["id"], self.region["id"],
                                       {"musicxml": XML.replace("<step>C", "<step>D")})
        self.assertEqual(updated["regions"][0]["status"], "pending")

    def test_approval_rejects_unapplied_context_change(self):
        context = {**server.DEFAULT_CONTEXT, "confirmed": True, "fifths": -2}
        with self.assertRaisesRegex(ValueError, "Apply the changed musical context"):
            server.update_region(self.doc["id"], self.region["id"],
                {"status": "reviewed", "musicxml": XML, "context": context,
                 "editor_context": server.DEFAULT_CONTEXT.copy()})


if __name__ == "__main__":
    unittest.main()
