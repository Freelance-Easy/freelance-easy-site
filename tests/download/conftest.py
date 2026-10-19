"""Fixtures for the homepage header's download (A9).

dl_site: this checkout (built by the shared site_url fixture) served on a free
127.0.0.1 port by a server that also answers /dl/<os>/<label> the way the live
site does for the Mac: a 200 with worker.js's attachment headers (worker.js
macDownload, content-disposition at :287) and a few bytes. Windows is a 302 to
GitHub on the live site (_redirects); here it is a 302 to a second local server
on another port (another origin, like GitHub) that answers with the attachment,
so no test ever reaches a release URL. Every /dl/ request path (with any query)
is recorded in dl_site.hits.

dl_site.mode switches the answers for one test (cleared after each test):
  mode["mac"] = "502"   /dl/mac/* answers like worker.js's 502 (HTML, no attachment)
  mode["win"] = "404"   /dl/win/* redirects to a 404 HTML page on the other origin
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


def _send(handler, code: int, ctype: str, body: bytes, extra: dict | None = None):
    handler.send_response(code)
    handler.send_header("content-type", ctype)
    for k, v in (extra or {}).items():
        handler.send_header(k, v)
    handler.send_header("content-length", str(len(body)))
    handler.send_header("cache-control", "no-store, no-transform")
    handler.end_headers()
    handler.wfile.write(body)


def _attachment(name: str) -> dict:
    return {"content-disposition": 'attachment; filename="' + name + '"'}


ERROR_PAGE = b"<!doctype html><title>Download unavailable</title><h1>Download unavailable</h1>"


class _Releases(http.server.BaseHTTPRequestHandler):
    """The GitHub stand-in, on its own port: /asset/<file> is the attachment, anything else a 404 page."""

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        pass

    def do_GET(self):  # noqa: N802 - stdlib name
        if self.path.startswith("/asset/"):
            return _send(self, 200, "application/octet-stream", b"EXEBYTES", _attachment(self.path.rsplit("/", 1)[-1]))
        return _send(self, 404, "text/html; charset=utf-8", b"<!doctype html><title>Not Found</title><h1>Not Found</h1>")


class _Handler(http.server.SimpleHTTPRequestHandler):
    hits: list = []
    mode: dict = {}
    releases: str = ""

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        pass

    def do_GET(self):  # noqa: N802 - stdlib name
        if not self.path.startswith("/dl/"):
            return super().do_GET()
        self.hits.append(self.path)
        os_ = self.path.split("/")[2]
        mode = self.mode.get(os_, "ok")
        if os_ == "win":  # _redirects: a 302 to the release asset on another origin
            target = "/missing" if mode == "404" else "/asset/" + FILES["win"]
            self.send_response(302)
            self.send_header("location", self.releases + target)
            self.send_header("content-length", "0")
            self.end_headers()
            return None
        if mode == "502":  # worker.js downloadUnavailable: an HTML page, no attachment
            return _send(self, 502, "text/html; charset=utf-8", ERROR_PAGE)
        return _send(self, 200, "application/x-apple-diskimage", b"DMGBYTES", _attachment(FILES.get(os_, "download.bin")))


@pytest.fixture(scope="session")
def dl_site(site_url):  # site_url builds the root pages first
    hits: list = []
    mode: dict = {}
    releases = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Releases)
    origin = "http://127.0.0.1:%d" % releases.server_address[1]
    cls = type("H", (_Handler,), dict(hits=hits, mode=mode, releases=origin))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(cls, directory=str(ROOT)))
    servers = (server, releases)
    threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in servers]
    for t in threads:
        t.start()
    try:
        yield SimpleNamespace(url="http://127.0.0.1:%d" % server.server_address[1], hits=hits, mode=mode, releases=origin)
    finally:
        for s in servers:
            s.shutdown()
            s.server_close()
        for t in threads:
            t.join(timeout=5)


@pytest.fixture(autouse=True)
def _clear_mode(request):
    yield
    if "dl_site" in request.fixturenames:
        request.getfixturevalue("dl_site").mode.clear()
