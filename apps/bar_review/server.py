"""Local transcription queue. Run: uv run python apps/bar_review/server.py.

The service binds only to loopback. Source scans are read-only; working copies,
page images and annotations live in outputs/. No cloud services are used.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import threading
from urllib.parse import parse_qs, unquote, urlsplit
import uuid
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image, ImageOps
from segmentation import detect_regions


APP = Path(__file__).resolve().parent
DATA = APP / "outputs"
SCAN_DIR = ""
LOCK = threading.RLock()
STATUSES = {"pending", "reviewed", "skipped", "unclear", "bad_crop"}
DEFAULT_CONTEXT = {"instrument": "", "clef": "treble", "fifths": 0,
                   "beats": 4, "beat_type": 4, "transpose": 0, "confirmed": False}


def now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    db = sqlite3.connect(DATA / "annotations.sqlite3")
    db.row_factory = sqlite3.Row
    return db


def initialize():
    DATA.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")


def get_documents():
    with connect() as db:
        return [json.loads(row[0]) for row in db.execute("SELECT payload FROM documents ORDER BY rowid")]


def get_document(document_id):
    with connect() as db:
        row = db.execute("SELECT payload FROM documents WHERE id=?", (document_id,)).fetchone()
    if row is None:
        raise ValueError("Document not found")
    return json.loads(row[0])


def put_document(document):
    with connect() as db:
        db.execute("INSERT INTO documents VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                   (document["id"], json.dumps(document)))


def validate_context(context):
    result = {**DEFAULT_CONTEXT, **context}
    if result["clef"] not in {"treble", "bass", "alto", "tenor", "percussion"}:
        raise ValueError("Unknown clef")
    for name, low, high in [("fifths", -7, 7), ("beats", 1, 32),
                            ("beat_type", 1, 64), ("transpose", -36, 36)]:
        result[name] = int(result[name])
        if not low <= result[name] <= high:
            raise ValueError(f"Invalid {name}")
    if result["beat_type"] not in {1, 2, 4, 8, 16, 32, 64}:
        raise ValueError("Time signature denominator must be a power of two")
    result["instrument"] = str(result["instrument"])[:200]
    result["confirmed"] = bool(result["confirmed"])
    return result


def validate_musicxml(xml):
    if not isinstance(xml, str) or len(xml) > 2_000_000:
        raise ValueError("Invalid MusicXML")
    # Exports from Smoosic contain a public DOCTYPE. ElementTree does not fetch it.
    if "<!ENTITY" in xml.upper():
        raise ValueError("XML entity declarations are not accepted")
    root = ET.fromstring(xml)
    if root.tag != "score-partwise" or root.find("part/measure") is None:
        raise ValueError("Expected partwise MusicXML containing a measure")
    return root


def import_scan(path, start_page=1, pages=1):
    source = Path(path).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        raise ValueError("Choose an existing PDF, PNG, JPEG or TIFF")
    if not 1 <= pages <= 10 or start_page < 1:
        raise ValueError("Import 1–10 pages at a time, starting at page 1 or later")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    for existing in get_documents():
        if existing.get("sha256") == digest and existing.get("start_page") == start_page and existing.get("requested_pages") == pages:
            return existing
    doc_id = uuid.uuid4().hex
    folder = DATA / doc_id
    folder.mkdir()
    shutil.copy2(source, folder / ("source" + source.suffix.lower()))
    document = {"id": doc_id, "title": source.stem, "source_name": source.name,
                "sha256": digest, "start_page": start_page, "requested_pages": pages,
                "created_at": now(), "pages": [], "regions": []}
    try:
        with tempfile.TemporaryDirectory() as temp:
            if source.suffix.lower() == ".pdf":
                if not shutil.which("pdftoppm"):
                    raise ValueError("PDF import requires Poppler (brew install poppler)")
                subprocess.run(["pdftoppm", "-f", str(start_page), "-l", str(start_page+pages-1),
                                "-scale-to", "2200", "-png", str(source), str(Path(temp)/"page")],
                               check=True, capture_output=True, timeout=120)
                files = sorted(Path(temp).glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
                images = [(int(p.stem.split("-")[-1]), p) for p in files]
            else:
                images = [(1, source)]
            if not images:
                raise ValueError("No pages found in the selected range")
            for page_number, filename in images:
                with Image.open(filename) as opened:
                    image = ImageOps.exif_transpose(opened).convert("RGB")
                    image.thumbnail((2200, 2200))
                    image.save(folder / f"page-{page_number}.png")
                    page = {"number": page_number, "width": image.width, "height": image.height,
                            "image": f"/data/{doc_id}/page-{page_number}.png",
                            "context": DEFAULT_CONTEXT.copy()}
                    document["pages"].append(page)
                    for candidate in detect_regions(image):
                        document["regions"].append({**candidate, "id": uuid.uuid4().hex,
                            "page": page_number, "status": "pending", "notes": "",
                            "bar_count": 1, "context": None, "score": None, "musicxml": None, "editor_context": None,
                            "updated_at": None})
        if not document["regions"]:
            raise ValueError("No staff regions detected. Try a clearer page; this prototype cannot segment this scan yet.")
        put_document(document)
        return document
    except Exception:
        shutil.rmtree(folder)
        raise


def update_region(doc_id, region_id, payload):
    document = get_document(doc_id)
    region = next((r for r in document["regions"] if r["id"] == region_id), None)
    if region is None:
        raise ValueError("Region not found")
    if region["status"] == "reviewed" and "status" not in payload:
        changed_fields = ["score", "musicxml", "context", "box", "bar_count"]
        if any(field in payload and payload[field] != region.get(field) for field in changed_fields):
            region["status"] = "pending"
    page = next(p for p in document["pages"] if p["number"] == region["page"])
    if "page_context" in payload:
        page["context"] = validate_context(payload["page_context"])
    for field in ["notes", "score", "musicxml", "context", "editor_context"]:
        if field in payload:
            region[field] = payload[field]
    if region["context"] is not None:
        region["context"] = validate_context(region["context"])
    if region.get("editor_context") is not None:
        region["editor_context"] = validate_context(region["editor_context"])
    if "box" in payload:
        box = [int(x) for x in payload["box"]]
        if len(box) != 4 or not (0 <= box[0] < box[2] <= page["width"] and 0 <= box[1] < box[3] <= page["height"]):
            raise ValueError("Crop must be inside the page")
        region["box"] = box
        region["detection"] = "adjusted"
    if "bar_count" in payload:
        region["bar_count"] = int(payload["bar_count"])
        if not 1 <= region["bar_count"] <= 128:
            raise ValueError("Bar count must be between 1 and 128")
    if "status" in payload:
        if payload["status"] not in STATUSES:
            raise ValueError("Unknown review status")
        region["status"] = payload["status"]
    if region["musicxml"]:
        validate_musicxml(region["musicxml"])
    if region["status"] == "reviewed":
        if not region["musicxml"]:
            raise ValueError("Enter a transcription before approving")
        if not (region["context"] or page["context"])["confirmed"]:
            raise ValueError("Confirm the clef, key, time and instrument context before approving")
        if region.get("editor_context"):
            declared = region["context"] or page["context"]
            if any(declared[key] != region["editor_context"][key]
                   for key in ["clef", "fifths", "beats", "beat_type", "transpose", "instrument"]):
                raise ValueError("Apply the changed musical context to the editor before approving")
    region["updated_at"] = now()
    put_document(document)
    return document


def export_dataset(document):
    buffer = io.BytesIO()
    manifest = {"schema_version": 1, "document": document, "examples": []}
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for page in document["pages"]:
            archive.write(DATA / document["id"] / f"page-{page['number']}.png", f"pages/page-{page['number']}.png")
        for region in document["regions"]:
            if region["status"] != "reviewed":
                continue
            validate_musicxml(region["musicxml"])
            page = next(p for p in document["pages"] if p["number"] == region["page"])
            prefix = f"examples/{region['id']}"
            with Image.open(DATA / document["id"] / f"page-{region['page']}.png") as image:
                crop = io.BytesIO()
                image.crop(region["box"]).save(crop, format="PNG")
                archive.writestr(prefix + ".png", crop.getvalue())
            archive.writestr(prefix + ".musicxml", region["musicxml"])
            manifest["examples"].append({"region_id": region["id"], "image": prefix + ".png",
                "musicxml": prefix + ".musicxml", "context": region["context"] or page["context"],
                "page": region["page"], "box": region["box"], "bar_count": region["bar_count"]})
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
    return buffer.getvalue()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP / "public"), **kwargs)

    def send_bytes(self, data, content_type="application/json", status=200, filename=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def json(self, data, status=200):
        self.send_bytes(json.dumps(data).encode(), status=status)

    def local_host(self):
        port = self.server.server_port
        if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            self.json({"error": "Use the local loopback URL"}, 403)
            return False
        return True

    def do_GET(self):
        if not self.local_host():
            return
        path = urlsplit(self.path).path
        try:
            if path == "/api/settings":
                self.json({"scan_dir": SCAN_DIR})
            elif path == "/api/documents":
                self.json(get_documents())
            elif path == "/api/files":
                root = Path(parse_qs(urlsplit(self.path).query).get("root", [""])[0]).expanduser()
                if not root.is_dir():
                    raise ValueError("Folder not found")
                paths = sorted(str(p) for p in root.rglob("*") if p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"} and p.is_file())
                self.json(paths[:2000])
            elif path.startswith("/api/export/"):
                doc_id = path.rsplit("/", 1)[-1]
                self.send_bytes(export_dataset(get_document(doc_id)), "application/zip", filename="reviewed-transcriptions.zip")
            elif path.startswith("/data/") or path.startswith("/vendor/") or path.startswith("/styles/"):
                is_data = path.startswith("/data/")
                root = (DATA if is_data else APP / "node_modules" / "smoosic" / "src" / "styles"
                        if path.startswith("/styles/") else APP / "node_modules")
                relative = unquote(path.split("/", 2)[2])
                file = (root / relative).resolve()
                if not file.is_relative_to(root.resolve()) or not file.is_file():
                    self.send_error(404)
                    return
                if is_data and not (file.name.startswith("page-") and file.suffix == ".png"):
                    self.send_error(404)
                    return
                self.send_bytes(file.read_bytes(), self.guess_type(str(file)))
            else:
                super().do_GET()
        except (ValueError, OSError, ET.ParseError) as error:
            self.json({"error": str(error)}, 400)

    def do_POST(self):
        if not self.local_host():
            return
        try:
            # Browsers on other origins must not be able to operate this local service.
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{self.headers.get('Host')}":
                self.json({"error": "Cross-origin requests are not permitted"}, 403)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length < 5_000_000:
                raise ValueError("Request too large or empty")
            payload = json.loads(self.rfile.read(length))
            with LOCK:
                if self.path == "/api/import":
                    result = import_scan(payload["path"], int(payload.get("start_page", 1)), int(payload.get("pages", 1)))
                elif self.path == "/api/region":
                    result = update_region(payload["document_id"], payload["region_id"], payload)
                else:
                    self.send_error(404)
                    return
            self.json(result)
        except (ValueError, KeyError, OSError, ET.ParseError, subprocess.SubprocessError) as error:
            self.json({"error": str(error)}, 400)


def main():
    global DATA, SCAN_DIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--scan-dir", type=Path, help="Initial folder for the import dialog")
    args = parser.parse_args()
    DATA = args.data_dir.expanduser().resolve()
    SCAN_DIR = str(args.scan_dir.expanduser().resolve()) if args.scan_dir else ""
    initialize()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Bar Review: http://127.0.0.1:{args.port}\nData: {DATA}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
