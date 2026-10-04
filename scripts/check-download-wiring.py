#!/usr/bin/env python3
"""Check the download buttons' campaign wiring and analytics events on a preview.

For each campaign page it loads the page as a Mac visitor in headless Chromium,
records the analytics calls instead of sending them (window.plausible is
replaced before the page's own snippet runs, and the page snippet keeps an
existing function), cancels link navigation (no download starts), clicks the
Mac button and the other link, and compares the button links and the recorded
events with what the weekly report expects:

  * /mac?utm_campaign=f1 (the flight-1 ad URL) -> the button goes to /dl/mac/f1;
  * a campaign value not on script.js's CAMPAIGNS allowlist falls back to the
    page's own label;
  * Download Click carries exactly {os, campaign, page, placement};
  * the Windows link on Mac-only pages sends nothing;
  * no other analytics event fires (the compatibility help is opened too).

It refuses production hostnames: there, a click would put a fake download into
the statistics. Run it against a branch preview or a local server (a local
`python3 -m http.server` serves /mac as /mac.html; that's detected). A page the
deploy doesn't have yet (/mac before its branch lands) is reported as skipped.

Usage (from the repo root):
  uv run --with playwright python3 scripts/check-download-wiring.py <base-url>
"""
from __future__ import annotations

import sys
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

PRODUCTION = {"freelance-easy.com", "www.freelance-easy.com"}

AD = "utm_source=google&utm_medium=demandgen&utm_campaign=f1"


def ev(os_: str, campaign: str, page: str) -> list:
    return ["Download Click", {"os": os_, "campaign": campaign, "page": page, "placement": "hero"}]


# (page, query, Mac button href, other link href, events in click order: Mac button, other link)
CASES = [
    ("/mac", AD + "&utm_content=ta", "/dl/mac/f1", "/", [ev("mac", "f1", "mac")]),
    ("/mac", AD + "&utm_content=tb", "/dl/mac/f1", "/", [ev("mac", "f1", "mac")]),
    ("/mac", "", "/dl/mac/mac", "/", [ev("mac", "mac", "mac")]),
    ("/mac", "utm_campaign=jane-doe", "/dl/mac/mac", "/", [ev("mac", "mac", "mac")]),
    ("/", "utm_campaign=f1", "/dl/mac/f1", "/dl/win/f1", [ev("mac", "f1", "home"), ev("win", "f1", "home")]),
    ("/", "utm_campaign=gclid_abc123", "/dl/mac/site", "/dl/win/site", [ev("mac", "site", "home"), ev("win", "site", "home")]),
    ("/mac-audio", "utm_campaign=F1", "/dl/mac/f1", "/", [ev("mac", "f1", "mac-audio")]),
    ("/audio", "utm_campaign=nope", "/dl/mac/audio", "/dl/win/audio", [ev("mac", "audio", "audio"), ev("win", "audio", "audio")]),
]

# Runs before any page script: the page's snippet keeps this function
# (window.plausible || …), so calls are recorded and nothing is sent; link
# clicks are cancelled after the page's own listeners have run.
RECORDER = """
window.__calls = [];
window.plausible = function (name, opts) { window.__calls.push([name, (opts && opts.props) || null]); };
window.plausible.init = function () {};
document.addEventListener('click', function (e) {
  var a = e.target.closest && e.target.closest('a');
  if (a) e.preventDefault();
}, false);
"""


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    base = sys.argv[1].rstrip("/")
    host = urlsplit(base).hostname or ""
    if host in PRODUCTION:
        print(f"refusing {host}: a click here would count as a real download. Use a preview or a local server.")
        return 2

    failures = 0
    checked = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.add_init_script(RECORDER)
        # Every request goes through the browser: Cloudflare answers 403 to a
        # plain script client. A local http.server has no pretty URLs (/mac is
        # /mac.html there).
        probe = context.new_page()
        first = probe.goto(base + "/mac-audio")
        suffix = "" if first and first.status == 200 else ".html"
        for page_path, query, want_primary, want_alt, want_events in CASES:
            path = page_path if page_path == "/" else page_path + suffix
            url = base + path + ("?" + query if query else "")
            label = f"{page_path}{'?' + query if query else ''}"
            page = context.new_page()
            resp = page.goto(url, wait_until="load")
            code = resp.status if resp else 0
            if code == 404:
                print(f"SKIP {label}: not on this deploy")
                page.close()
                continue
            if code != 200:
                failures += 1
                print(f"FAIL {label}: HTTP {code}")
                page.close()
                continue
            checked += 1
            help_ = page.locator("[data-compat-help]").first
            if help_.count():
                help_.evaluate("d => { d.open = true; d.dispatchEvent(new Event('toggle')); }")
            primary = page.locator('[data-role="primary"]').first
            alt = page.locator('[data-role="alt"]').first
            got_primary = primary.get_attribute("href")
            got_alt = alt.get_attribute("href")
            primary.click()
            alt.click()
            page.wait_for_timeout(100)
            got_events = page.evaluate("window.__calls")
            problems = []
            if got_primary != want_primary:
                problems.append(f"Mac button {got_primary!r}, want {want_primary!r}")
            if got_alt != want_alt:
                problems.append(f"other link {got_alt!r}, want {want_alt!r}")
            if got_events != want_events:
                problems.append(f"events {got_events}, want {want_events}")
            if problems:
                failures += 1
                print(f"FAIL {label}: " + "; ".join(problems))
            else:
                print(f"ok   {label}: {got_primary}, {len(got_events)} event(s)")
            page.close()
        # The Worker's analytics route: a preview must answer the empty "off"
        # script. (A local http.server has no Worker, so there is no such route.)
        resp = probe.goto(base + "/js/script.js")
        if resp and resp.status == 200:
            script = (resp.text() or "")[:60].strip()
        else:
            script = f"HTTP {resp.status if resp else 0} (no Worker here)"
        print(f"/js/script.js here: {script!r}")
        browser.close()
    if not checked:
        print("NOTHING CHECKED")
        return 1
    print(f"ALL PASS ({checked} cases)" if not failures else f"{failures} FAILED")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
