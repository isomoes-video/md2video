#!/usr/bin/env -S uv run --script
# /// script
# dependencies = []
# ///
"""Live read-only dashboard for the md2video pipeline.

Scans ``output/<slug>/`` on every request and reports per-deck stage status,
derived entirely from the filesystem (no database, no build step):

    slides  -> presentation.html + script.json + output.pdf all exist
    audio   -> audio/slide-*.mp3 count vs len(script.json)
    video   -> video.mp4 exists
    intro   -> intro.txt exists

Serves a self-contained dashboard that polls ``/status`` and renders one card
per deck, so you can literally watch decks fill in stage by stage as the agent
writes files.

Usage:
    uv run scripts/dashboard.py            # http://127.0.0.1:8000
    uv run scripts/dashboard.py --port 9000
    python3 scripts/dashboard.py           # stdlib only, plain python works too
"""

from __future__ import annotations

import argparse
import errno
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
DASHBOARD_HTML = ROOT / "dashboard.html"


def scan_decks() -> list[dict]:
    """Return per-deck stage status, sorted by most-recent activity first."""
    decks: list[dict] = []
    if not OUTPUT.is_dir():
        return decks

    for deck_dir in sorted(OUTPUT.iterdir()):
        if not deck_dir.is_dir():
            continue

        script = deck_dir / "script.json"
        presentation = deck_dir / "presentation.html"
        pdf = deck_dir / "output.pdf"
        video = deck_dir / "video.mp4"
        intro = deck_dir / "intro.txt"
        audio_dir = deck_dir / "audio"

        slide_count: int | None = None
        if script.is_file():
            try:
                data = json.loads(script.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    slide_count = len(data)
            except (ValueError, OSError):
                slide_count = None

        audio_done = (
            sum(1 for _ in audio_dir.glob("slide-*.mp3"))
            if audio_dir.is_dir()
            else 0
        )
        audio_total = slide_count or 0

        mtime = 0.0
        for path in (script, presentation, pdf, video, intro):
            if path.is_file():
                mtime = max(mtime, path.stat().st_mtime)
        if audio_dir.is_dir():
            for path in audio_dir.glob("*.mp3"):
                mtime = max(mtime, path.stat().st_mtime)

        decks.append(
            {
                "slug": deck_dir.name,
                "slides_done": presentation.is_file()
                and script.is_file()
                and pdf.is_file(),
                "slide_count": slide_count,
                "audio_done": audio_done,
                "audio_total": audio_total,
                "audio_complete": audio_total > 0 and audio_done >= audio_total,
                "video_done": video.is_file(),
                "intro_done": intro.is_file(),
                "has_presentation": presentation.is_file(),
                "has_pdf": pdf.is_file(),
                "has_video": video.is_file(),
                "has_intro": intro.is_file(),
                "mtime": mtime,
            }
        )

    decks.sort(key=lambda d: d["mtime"], reverse=True)
    return decks


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args) -> None:  # quieter console
        pass

    def handle(self) -> None:
        # A browser routinely drops the socket mid-response (canceling a video
        # Range request, closing a tab). That surfaces as a connection-reset
        # while we are still writing, which is expected for a local file server
        # -- swallow it quietly instead of dumping a scary traceback.
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)

        if path in ("/", "/index.html", "/dashboard.html"):
            self._send_file(DASHBOARD_HTML, fallback_ctype="text/html")
            return

        if path == "/status":
            body = json.dumps({"decks": scan_decks()}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Static artifacts under output/ (videos, slides, pdf, intro, audio).
        # Containment is anchored to OUTPUT so an embedded ".." cannot escape
        # the output tree (e.g. /output/../package.json must not resolve out).
        if path.startswith("/output/"):
            target = (ROOT / path.lstrip("/")).resolve()
            if (target == OUTPUT or OUTPUT in target.parents) and target.is_file():
                self._send_file(target)
                return

        self.send_error(404, "Not found")

    def _send_file(self, file_path: Path, fallback_ctype: str = "application/octet-stream") -> None:
        if not file_path.is_file():
            self.send_error(404, "Not found")
            return

        ctype = mimetypes.guess_type(str(file_path))[0] or fallback_ctype
        # Declare UTF-8 for text formats so Chinese/Unicode renders instead of
        # mojibake (browsers otherwise guess the encoding for charset-less text).
        if "charset" not in ctype and (
            ctype.startswith("text/")
            or ctype in ("application/json", "application/javascript", "image/svg+xml")
        ):
            ctype += "; charset=utf-8"
        size = file_path.stat().st_size
        range_header = self.headers.get("Range")

        # Minimal Range support so videos seek instead of re-downloading.
        if range_header and range_header.startswith("bytes="):
            try:
                start_s, end_s = range_header[len("bytes=") :].split("-", 1)
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else size - 1
            except ValueError:
                start, end = 0, size - 1
            start = max(0, start)
            end = min(end, size - 1)
            length = max(0, end - start + 1)
            self.send_response(206)
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(length))
            self.end_headers()
            with file_path.open("rb") as fh:
                fh.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = fh.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            return

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with file_path.open("rb") as fh:
            while True:
                chunk = fh.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    os.chdir(ROOT)
    try:
        server = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            raise SystemExit(
                f"port {args.port} is already in use on {args.host}.\n"
                f"  - another dashboard may already be running: open "
                f"http://{args.host}:{args.port}\n"
                f"  - or pick a free port: uv run scripts/dashboard.py --port {args.port + 1}"
            )
        raise SystemExit(f"could not start server on {args.host}:{args.port}: {exc}")
    url = f"http://{args.host}:{args.port}"
    print(f"md2video dashboard -> {url}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
