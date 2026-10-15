"""Shared pytest fixtures for the site (B1; changes go through the orchestrator).

site_url: builds the root pages from src/ (scripts/build-site.py) and serves this
checkout on a free port, 127.0.0.1 only, for the whole session. It yields the
base URL with no trailing slash, e.g. "http://127.0.0.1:53817".
"""
from __future__ import annotations

import functools
import http.server
import pathlib
import subprocess
import sys
import threading

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        pass


@pytest.fixture(scope="session")
def site_url():
    build = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build-site.py")],
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        pytest.fail(f"scripts/build-site.py failed:\n{build.stdout}{build.stderr}")
    handler = functools.partial(_QuietHandler, directory=str(ROOT))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
