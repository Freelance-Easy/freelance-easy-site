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
  * no other analytics event fires (the compatibility help is opened too);
  * the homepage header's Download (A9), as a Mac, a Windows and a phone
    visitor: /dl/<os>/<campaign> with placement "header" and a status line
    linking the install help, or on a phone the jump to the download block,
    labelled "Get it on Mac", and no event; a Mac-only link
    (FEDownload.wire, platforms ["mac"]) downloads for a Mac and stays the
    plain link for Windows.

It also checks the Worker's analytics route: on a preview, /js/script.js must
answer the empty "analytics off here" script (previews never count); a local
`python3 -m http.server` has no Worker, so there it must be a 404.

With --tracker <URL of a Plausible pa-….js script> it then loads /mac with that
REAL Plausible script instead, captures every event it sends with its content
type (answered locally; nothing reaches Plausible), clicks the Mac button,
switches the tab away (the engagement event) and leaves the page, and replays
the captured events through worker.js's contract (`node
scripts/test-worker.mjs --payloads`): a pageview, a Download Click and an
engagement event must all be captured, and each one must be forwarded, so a
change in Plausible's event format can't silently drop our counts. With the
site's own script the events must already name freelance-easy.com; before our
site exists, Plausible's own public script can stand in with --public-tracker,
which substitutes our domain for its domain when replaying.

It refuses production hostnames: there, a click would put a fake download into
the statistics. A local server serves /mac as /mac.html; that's detected. A
page the deploy doesn't have yet (/mac before its branch lands) is skipped.

Usage (from the repo root):
  uv run --with playwright python3 scripts/check-download-wiring.py <base-url> [--tracker <url> [--public-tracker]]
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

PRODUCTION = {"freelance-easy.com", "www.freelance-easy.com"}
LOCAL = {"localhost", "127.0.0.1", "::1"}
OFF_SCRIPT = "/* analytics off here */"
REPO = pathlib.Path(__file__).resolve().parent.parent

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

# Cancels link navigation after the page's own listeners have run: no download starts.
CANCEL_LINKS = """
document.addEventListener('click', function (e) {
  var a = e.target.closest && e.target.closest('a');
  if (a) e.preventDefault();
}, false);
"""

# Runs before any page script: the page's snippet keeps this function
# (window.plausible || …), so calls are recorded and nothing is sent.
RECORDER = """
window.__calls = [];
window.plausible = function (name, opts) { window.__calls.push([name, (opts && opts.props) || null]); };
window.plausible.init = function () {};
""" + CANCEL_LINKS


def check_cases(browser, base: str, suffix: str) -> tuple[int, int]:
    failures = checked = 0
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    context.add_init_script(RECORDER)
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
    context.close()
    return failures, checked


# (A9) the homepage header's Download, per visitor: (name, UA, navigator.platform, phone?, query, header href, label,
# events, status line: (install link, words it must show) or None). The click is cancelled like the others.
MAC_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
WIN_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
PHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"


def hev(os_: str, campaign: str) -> list:
    return ["Download Click", {"os": os_, "campaign": campaign, "page": "home", "placement": "header"}]


HEADER_CASES = [
    ("mac", MAC_UA, "MacIntel", False, "utm_campaign=f1", "/dl/mac/f1", "Download", [hev("mac", "f1")],
     ("/install#mac", ["Apple Silicon", "M1 or later"])),
    ("win", WIN_UA, "Win32", False, "", "/dl/win/site", "Download", [hev("win", "site")],
     ("/install#windows", ["Windows 10 and 11", "security warning"])),
    ("phone", PHONE_UA, "iPhone", True, "", "#download", "Get it on Mac", [], None),
]

# (A9) a Mac-only placement (G1's platforms: ["mac"]): wired on a link added to the homepage. (visitor, want href)
PLATFORM_CASES = [("mac", MAC_UA, "MacIntel", "/dl/mac/site"), ("win", WIN_UA, "Win32", "#download")]
WIRE_MAC_ONLY = """() => {
  var a = document.createElement('a');
  a.href = '#download'; a.id = 'mac-only-fixture'; a.textContent = 'Download';
  document.body.appendChild(a);
  if (!window.FEDownload) return 'no FEDownload.wire';
  window.FEDownload.wire(a, { placement: 'fixture', platforms: ['mac'] });
  return a.getAttribute('href');
}"""


def visitor(browser, ua: str, platform: str, phone: bool):
    if phone:
        context = browser.new_context(user_agent=ua, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    else:
        context = browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 900})
    context.add_init_script(f"Object.defineProperty(Navigator.prototype, 'platform', {{ get: () => {json.dumps(platform)} }});")
    context.add_init_script(RECORDER)
    return context


def check_header(browser, base: str) -> tuple[int, int]:
    failures = checked = 0
    for name, ua, platform, phone, query, want_href, want_label, want_events, want_status in HEADER_CASES:
        label = f"header [{name}] /{'?' + query if query else ''}"
        context = visitor(browser, ua, platform, phone)
        page = context.new_page()
        page.goto(base + "/" + ("?" + query if query else ""), wait_until="load")
        cta = page.locator(".site-header .nav-cta")
        got_href = cta.get_attribute("href")
        got_label = cta.inner_text().strip()
        cta.click()
        page.wait_for_timeout(100)
        got_events = page.evaluate("window.__calls")
        problems = []
        if got_href != want_href:
            problems.append(f"href {got_href!r}, want {want_href!r}")
        if got_label != want_label:
            problems.append(f"label {got_label!r}, want {want_label!r}")
        if got_events != want_events:
            problems.append(f"events {got_events}, want {want_events}")
        status = page.locator('.site-header [data-dl-status][data-for="header"]')
        if want_status:
            link, words = want_status
            if not status.count() or not status.is_visible():
                problems.append("no visible status line after the click")
            else:
                text = status.inner_text()
                problems += [f"status line lacks {w!r}" for w in words if w not in text]
                if status.locator(f'a[href="{link}"]').count() != 1:
                    problems.append(f"status line has no link to {link}")
        elif status.count() and status.is_visible():
            problems.append("a status line shows on a phone")
        if problems:
            failures += 1
            print(f"FAIL {label}: " + "; ".join(problems))
        else:
            print(f"ok   {label}: {got_href} {got_label!r}, {len(got_events)} event(s)")
        checked += 1
        context.close()
    for name, ua, platform, want_href in PLATFORM_CASES:
        context = visitor(browser, ua, platform, False)
        page = context.new_page()
        page.goto(base + "/", wait_until="load")
        got = page.evaluate(WIRE_MAC_ONLY)
        checked += 1
        if got != want_href:
            failures += 1
            print(f"FAIL platforms ['mac'] [{name}]: {got!r}, want {want_href!r}")
        else:
            print(f"ok   platforms ['mac'] [{name}]: {got}")
        context.close()
    return failures, checked


def check_off_route(browser, base: str, local: bool) -> int:
    # A plain request, like the page's own <script src>: Cloudflare answers a
    # top-level navigation to /js/script.js with the 404 page without running
    # the Worker, but a script load (what visitors do) reaches it.
    context = browser.new_context()
    resp = context.request.get(base + "/js/script.js")
    code = resp.status
    body = (resp.text() if code == 200 else "").strip()
    context.close()
    if local and code == 404:
        print("ok   /js/script.js: no Worker on a local server (404, expected)")
        return 0
    if not local and code == 200 and body == OFF_SCRIPT:
        print(f"ok   /js/script.js: {OFF_SCRIPT!r} (previews never count)")
        return 0
    print(f"FAIL /js/script.js: HTTP {code}, {body[:60]!r}; want {'404' if local else OFF_SCRIPT!r}")
    return 1


def check_real_tracker(browser, base: str, suffix: str, tracker: str, public: bool) -> int:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    script = context.request.get(tracker)
    if not script.ok:
        print(f"FAIL --tracker: HTTP {script.status} for {tracker}")
        return 1
    js = script.text()
    captured: list[dict] = []
    # Plausible's script ignores automated browsers (navigator.webdriver is
    # true under Playwright); this run is a test of its event format, so it
    # looks like an ordinary browser here.
    context.add_init_script("Object.defineProperty(Navigator.prototype, 'webdriver', { get: () => false });")
    context.add_init_script(CANCEL_LINKS)
    context.route("https://plausible.io/**", lambda route: route.abort())  # nothing ever reaches Plausible
    context.route("**/js/script.js", lambda route: route.fulfill(status=200, content_type="application/javascript", body=js))

    def answer(route):
        if route.request.method == "POST":
            captured.append({"body": route.request.post_data or "", "content_type": route.request.headers.get("content-type", "")})
        route.fulfill(status=202, body="ok")

    context.route("**/api/event", answer)
    page = context.new_page()
    page.goto(base + "/mac" + suffix + "?" + AD + "&utm_content=ta", wait_until="load")
    page.wait_for_timeout(1500)
    page.locator('[data-role="primary"]').first.click()
    page.wait_for_timeout(2500)
    # A tab switch: Plausible's script sends the page's engagement event when
    # the page becomes hidden (a headless page never does on its own).
    page.evaluate(
        "() => { Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });"
        " Object.defineProperty(document, 'hidden', { value: true, configurable: true });"
        " document.dispatchEvent(new Event('visibilitychange')); }"
    )
    page.wait_for_timeout(800)
    page.goto(base + "/", wait_until="load")
    page.wait_for_timeout(1500)
    context.close()
    names = [json.loads(c["body"]).get("n") for c in captured if c["body"].startswith("{")]
    print(f"     the real tracker sent: {names}")
    missing = [n for n in ("pageview", "Download Click", "engagement") if n not in names]
    if missing:
        print(f"FAIL --tracker: no {', '.join(missing)} captured")
        return 1
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(captured, f)
    replay = ["node", str(REPO / "scripts" / "test-worker.mjs"), "--payloads", f.name]
    if public:
        replay.append("--substitute-domain")
    run = subprocess.run(replay, capture_output=True, text=True)
    print("\n".join("     " + line for line in run.stdout.strip().splitlines()))
    if run.returncode != 0:
        print("FAIL --tracker: worker.js would drop a real event (see above)")
        return 1
    print("ok   --tracker: every real event passes worker.js's contract")
    return 0


def main() -> int:
    args = sys.argv[1:]
    tracker = None
    public = "--public-tracker" in args
    args = [a for a in args if a != "--public-tracker"]
    if "--tracker" in args:
        i = args.index("--tracker")
        tracker = args[i + 1]
        args = args[:i] + args[i + 2:]
    if len(args) != 1:
        print(__doc__)
        return 2
    base = args[0].rstrip("/")
    host = urlsplit(base).hostname or ""
    if host in PRODUCTION:
        print(f"refusing {host}: a click here would count as a real download. Use a preview or a local server.")
        return 2
    local = host in LOCAL

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Every request goes through the browser: Cloudflare answers 403 to a
        # plain script client. A local http.server has no pretty URLs.
        probe = browser.new_page()
        first = probe.goto(base + "/mac-audio")
        suffix = "" if first and first.status == 200 else ".html"
        probe.close()
        failures, checked = check_cases(browser, base, suffix)
        h_failures, h_checked = check_header(browser, base)
        failures += h_failures
        checked += h_checked
        failures += check_off_route(browser, base, local)
        if tracker:
            failures += check_real_tracker(browser, base, suffix, tracker, public)
        browser.close()
    if not checked:
        print("NOTHING CHECKED")
        return 1
    print(f"ALL PASS ({checked} cases)" if not failures else f"{failures} FAILED")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
