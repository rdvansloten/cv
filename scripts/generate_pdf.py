#!/usr/bin/env python3
"""Render index.html to cv.pdf using headless Chromium via Playwright.

Local use:
    pip install -r scripts/requirements.txt
    python -m playwright install chromium
    python scripts/generate_pdf.py
"""
from __future__ import annotations

import http.server
import socketserver
import sys
import threading
from contextlib import contextmanager
from functools import partial
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "cv.pdf"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_, **__):
        pass


@contextmanager
def local_server(directory: Path):
    """Serve `directory` on an ephemeral port — needed because the renderer
    fetches content.md, and fetch() doesn't work from file:// URLs."""
    handler = partial(_QuietHandler, directory=str(directory))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        httpd.shutdown()
        httpd.server_close()


def main() -> int:
    with local_server(ROOT) as port, sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            # The renderer clears aria-busy on #cv once content is mounted.
            page.wait_for_function(
                "() => { const el = document.getElementById('cv');"
                "        return el && !el.hasAttribute('aria-busy'); }"
            )
            page.pdf(
                path=str(OUTPUT),
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
        finally:
            browser.close()

    size = OUTPUT.stat().st_size
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
