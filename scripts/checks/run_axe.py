#!/usr/bin/env python3
"""F3 axe runner: `run_axe.py <url> --theme dark|light [--widths 390,1440] [--json]`.

Exits 0 at 0 serious/critical violations, 1 otherwise, 2 on usage error.
Only 127.0.0.1/localhost is ever loaded; other hosts are aborted.

axe-core: pinned, vendored at scripts/checks/vendor/axe.min.js (injected into the
page; no network, no npm).
  version: 4.10.2
  source:  https://cdn.jsdelivr.net/npm/axe-core@4.10.2/axe.min.js
  sha256:  b511cd9dec01c76f4b2ad1723b66b6db37d4c2eb4ed199076e1829d9ee7b75e3
The sha256 is verified on every run.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

AXE_PATH = Path(__file__).resolve().parent / "vendor" / "axe.min.js"
AXE_SHA256 = "b511cd9dec01c76f4b2ad1723b66b6db37d4c2eb4ed199076e1829d9ee7b75e3"
LOCAL = {"127.0.0.1", "localhost"}


def axe_source() -> str:
    data = AXE_PATH.read_bytes()
    got = hashlib.sha256(data).hexdigest()
    if got != AXE_SHA256:
        raise SystemExit(f"run_axe: vendored axe.min.js sha256 mismatch ({got})")
    return data.decode("utf-8")


def _local_only(route):
    if urlparse(route.request.url).hostname in LOCAL:
        route.continue_()
    else:
        route.abort()


def run_axe(browser, url: str, theme: str, width: int) -> list[dict]:
    """Serious/critical violations for url at width in the given theme."""
    ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=theme)
    try:
        ctx.route("**/*", _local_only)
        ctx.add_init_script(
            "try{localStorage.setItem('fe-theme'," + json.dumps(theme) + ")}catch(e){}")
        page = ctx.new_page()
        page.goto(url, wait_until="load")
        page.wait_for_timeout(600)
        page.evaluate("document.fonts ? document.fonts.ready.then(() => true) : true")
        page.add_script_tag(content=axe_source())
        res = page.evaluate("axe.run(document, {resultTypes: ['violations']})")
    finally:
        ctx.close()
    out = []
    for v in res["violations"]:
        if v.get("impact") in ("serious", "critical"):
            out.append({"width": width, "theme": theme, "id": v["id"], "impact": v["impact"],
                        "nodes": len(v["nodes"]),
                        "target": [n["target"] for n in v["nodes"][:3]]})
    return out


def main(argv: list[str]) -> int:
    args = argv[1:]
    url, theme, widths, as_json = None, None, [390, 1440], False
    bad = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--theme":
            i += 1
            theme = args[i] if i < len(args) else None
        elif a == "--widths":
            i += 1
            widths = [int(w) for w in args[i].split(",")]
        elif a == "--json":
            as_json = True
        elif not a.startswith("-") and url is None:
            url = a
        else:
            bad = True
        i += 1
    if bad or not url or theme not in ("dark", "light") or urlparse(url).hostname not in LOCAL:
        print("usage: run_axe.py <http://127.0.0.1:PORT/path> --theme dark|light "
              "[--widths 390,1440] [--json]", file=sys.stderr)
        return 2
    from playwright.sync_api import sync_playwright
    found: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for w in widths:
                found += run_axe(browser, url, theme, w)
        finally:
            browser.close()
    if as_json:
        print(json.dumps(found, indent=1))
    else:
        for v in found:
            print(f"{v['impact']} {v['id']} x{v['nodes']} @{v['width']} {v['theme']}: {v['target']}")
        print(f"run_axe: {len(found)} serious/critical violation(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
