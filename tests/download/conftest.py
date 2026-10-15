"""Fixtures for the homepage header's download (A9).

dl_site: this checkout (built by the shared site_url fixture) served on a free
127.0.0.1 port by a server that also answers /dl/<os>/<label> the way the live
site does for the Mac: a 200 with worker.js's attachment headers (worker.js
macDownload, content-disposition at :287) and a few bytes. Windows is a 302 to
GitHub on the live site (_redirects); here it gets the same stub, so no test
ever reaches a release URL. Every /dl/ request path (with any query) is
recorded in dl_site.hits.
"""
from __future__ import annotations

import functools
import http.server
import pathlib
import threading
from types import SimpleNamespace

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FILES = {"mac": "Freelance-Easy.dmg", "win": "Freelance-Easy-Setup.exe"}


class _Handler(http.server.SimpleHTTPRequestHandler):
    hits: list = []

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        pass

    def do_GET(self):  # noqa: N802 - stdlib name
        if not self.path.startswith("/dl/"):
            return super().do_GET()
        self.hits.append(self.path)
        os_ = self.path.split("/")[2]
        body = b"DMGBYTES"
        self.send_response(200)
        self.send_header("content-type", "application/x-apple-diskimage")
        self.send_header("content-disposition", f'attachment; filename="{FILES.get(os_, "download.bin")}"')
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store, no-transform")
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="session")
def dl_site(site_url):  # site_url builds the root pages first
    hits: list = []
    handler = functools.partial(type("H", (_Handler,), {"hits": hits}), directory=str(ROOT))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield SimpleNamespace(url=f"http://127.0.0.1:{server.server_address[1]}", hits=hits)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
