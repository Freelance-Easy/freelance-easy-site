#!/usr/bin/env python3
"""Fidelity harness (R7 §4 F1-F18, the machine-checkable ones).

    fidelity.py --url <http://127.0.0.1:PORT/path> --check F7,F8[,...] [--json]

Checks: F1 F3 F5 F7 F8 F10 F11 LINKS (ALL = every one). Exit 0 = every requested
check passed, 1 = at least one failed, 2 = usage error. Output: one line per
check (`F7 PASS|FAIL detail...`), or one JSON document with --json.

  F1     token lint over the page's same-origin stylesheets + inline <style>
         (token_lint.py; /assets/fe/ exempt). Meant for changed CSS: a page that
         links an un-migrated stylesheet fails it, so it is opt-in via --check.
  F3     axe-core serious/critical at 390 + 1440, dark + light (run_axe.py)
  F5     only same-origin font requests, none third-party, no duplicate font file
  F7     CLS < 0.02 on load; header/rail/stage rects unchanged across a theme switch
  F8     fresh profile, no hash/storage -> data-theme="dark" (not on /mac);
         a theme-color meta, when present, follows the theme
  F10    prefers-reduced-motion: reduce -> 0 running animations after 1 s
  F11    at 360/390/430: no horizontal overflow, targets >= 24 px (primary >= 44 px)
  LINKS  every same-origin link resolves (file, .html, /index.html, a
         _redirects rule or a worker.js route) and in-page #anchors exist; external links are listed,
         never fetched

Only 127.0.0.1/localhost is ever contacted; every other host is aborted.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_axe  # noqa: E402
import token_lint  # noqa: E402

ROOT = HERE.parent.parent
LOCAL = {"127.0.0.1", "localhost"}
PHONE_WIDTHS = (360, 390, 430)
LAYOUT_SELECTORS = ("header, .site-header, .theme-toggle, .story-nav, .nav, .nav-cta, "
                    "[data-rail], [data-stage], .rail, .stage")
PRIMARY_SELECTOR = ".btn-primary, [data-primary], [data-role=primary]"


def _local_only(route, blocked: list[str]):
    if urlparse(route.request.url).hostname in LOCAL:
        route.continue_()
    else:
        blocked.append(route.request.url)
        route.abort()


def _new_page(browser, width=1280, height=900, **kw):
    ctx = browser.new_context(viewport={"width": width, "height": height}, **kw)
    blocked: list[str] = []
    ctx.route("**/*", lambda r: _local_only(r, blocked))
    return ctx, ctx.new_page(), blocked


class Fail(Exception):
    """A check failed for a reason other than a rule violation (bad status, nothing to check, ...)."""


class _LocalRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).hostname not in LOCAL:
            raise Fail(f"refusing redirect to non-local host: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_LocalRedirects)


# Routes that answer with an installer or a release redirect (_redirects + worker.js): the
# harness never requests them, so a local Wrangler cannot be made to proxy a real download.
_DOWNLOAD_RX = re.compile(r"^/(dl(/|$)|download(/|$)|releases(/|$))")


def _get(url: str):
    """(status, body bytes) for a local URL. Redirects are followed only to local hosts;
    a redirect to anything else raises Fail and nothing external is requested."""
    if urlparse(url).hostname not in LOCAL:
        raise Fail(f"refusing non-local URL: {url}")
    if _DOWNLOAD_RX.match(urlparse(url).path):
        raise Fail(f"refusing to fetch a download route: {url}")
    try:
        with _OPENER.open(url, timeout=15) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def _goto(page, url: str):
    """Navigate; fail on a non-2xx main document or an empty body."""
    resp = page.goto(url, wait_until="load")
    if resp is None or not (200 <= resp.status < 300):
        raise Fail(f"main document status {resp.status if resp else 'none'} for {url}")
    if not page.evaluate("document.body && (document.body.innerText.trim().length > 0 "
                         "|| document.body.querySelector('img,svg,canvas,video') !== null)"):
        raise Fail(f"nothing to check: empty document at {url}")
    return resp


_IMPORT_RX = re.compile(r"@import\s+(?:url\(\s*)?[\"']?([^\"')\s;]+)", re.I)


def _collect_css(href: str, seen: set, found: list, depth: int = 0):
    if href in seen:
        return
    seen.add(href)
    if urlparse(href).hostname not in LOCAL:
        found.append({"file": href, "line": 0, "rule": "third-party-css", "text": href})
        return
    status, body = _get(href)
    if status != 200:
        found.append({"file": href, "line": 0, "rule": "css-unreachable", "text": str(status)})
        return
    text = body.decode("utf-8", "replace")
    found += token_lint.lint_text(text, urlparse(href).path)
    if depth < 5:
        for imp in _IMPORT_RX.findall(text):
            _collect_css(urljoin(href, imp), seen, found, depth + 1)


# ---------------------------------------------------------------- checks ----

def check_F1(browser, url):
    ctx, page, _ = _new_page(browser)
    try:
        _goto(page, url)
        sheets = page.evaluate(
            "Array.from(document.querySelectorAll('link[rel~=stylesheet]')).map(l => l.href)")
        inline = page.evaluate(
            "Array.from(document.querySelectorAll('style')).map(s => s.textContent)")
        attrs = page.evaluate(
            "Array.from(document.querySelectorAll('[style]')).map(e => e.getAttribute('style'))")
    finally:
        ctx.close()
    if not (sheets or inline or attrs):
        raise Fail("nothing to check: the page has no stylesheet, <style> or style attribute")
    found: list[dict] = []
    seen: set = set()
    for href in sheets:
        _collect_css(href, seen, found)
    for i, css in enumerate(inline):
        found += token_lint.lint_text(css, f"<style #{i}>")
        for imp in _IMPORT_RX.findall(css):
            _collect_css(urljoin(url, imp), seen, found, 1)
    for i, a in enumerate(attrs):
        found += token_lint.lint_text("x{" + a + "}", f"<style attr #{i}>")
    return (not found, [f"{len(found)} violation(s)"] + [
        f"{v['file']}:{v['line']} {v['rule']} {v['text']}" for v in found[:20]], len(found))


def check_F3(browser, url):
    found = []
    for theme in ("dark", "light"):
        for w in (390, 1440):
            try:
                found += run_axe.run_axe(browser, url, theme, w)
            except RuntimeError as e:
                raise Fail(str(e))
    return not found, [f"{v['impact']} {v['id']} x{v['nodes']} @{v['width']} {v['theme']}"
                       for v in found]


def check_F5(browser, url):
    ctx, page, blocked = _new_page(browser)
    fonts: list[str] = []
    page.on("request", lambda r: fonts.append(r.url) if (
        r.resource_type == "font" or re.search(r"\.(woff2?|ttf|otf)(\?|$)", r.url)) else None)
    try:
        _goto(page, url)
        page.wait_for_timeout(800)
    finally:
        ctx.close()
    bad = []
    third = [u for u in blocked if re.search(
        r"font|\.woff|\.ttf|\.otf|typekit|gstatic", u, re.I)]
    bad += [f"third-party font request {u}" for u in third]
    bad += [f"non-local font request {u}" for u in fonts if urlparse(u).hostname not in LOCAL]
    names = [Path(urlparse(u).path).name for u in fonts if urlparse(u).hostname in LOCAL]
    for n in sorted({n for n in names if names.count(n) > 1}):
        bad.append(f"font file requested more than once: {n}")
    if not bad and not names:
        raise Fail("nothing to check: the page loaded no font file (F5 does not allow empty)")
    return not bad, bad or [f"{len(set(names))} local font file(s)"]


_CLS_JS = """() => {
  window.__cls = 0; window.__shifts = [];
  new PerformanceObserver(l => { for (const e of l.getEntries())
    if (!e.hadRecentInput) {
      window.__cls += e.value;
      window.__shifts.push(Math.round(e.startTime) + 'ms ' + e.value.toFixed(4) + ' ' +
        (e.sources || []).map(s => s.node ? s.node.nodeName.toLowerCase() + '.' + (s.node.className || '') : '?').join(','));
    } }).observe({type: 'layout-shift', buffered: true});
}"""
_RECTS_JS = """sel => Array.from(document.querySelectorAll(sel)).map(e => {
  const r = e.getBoundingClientRect();
  return [e.tagName.toLowerCase() + (e.className && e.className.baseVal === undefined ? '.' + e.className : ''),
          Math.round(r.x * 10) / 10, Math.round(r.y * 10) / 10,
          Math.round(r.width * 10) / 10, Math.round(r.height * 10) / 10];
})"""


def check_F7(browser, url):
    ctx, page, _ = _new_page(browser)
    bad = []
    try:
        page.add_init_script("(" + _CLS_JS + ")()")
        _goto(page, url)
        page.wait_for_timeout(1500)
        cls = page.evaluate("window.__cls")
        if cls >= 0.02:
            bad.append(f"CLS {cls:.4f} >= 0.02 ({'; '.join(page.evaluate('window.__shifts'))})")
        # An empty box set is allowed here (the doc pages have no header/rail/stage; CLS above
        # is still measured); the seeded F7 page and the home page do have boxes.
        before = page.evaluate(_RECTS_JS, LAYOUT_SELECTORS)
        toggle = page.query_selector("[data-theme-toggle]")
        if toggle and toggle.is_visible():
            toggle.click()
        else:
            page.evaluate("""() => { const d = document.documentElement;
              d.setAttribute('data-theme', d.getAttribute('data-theme') === 'light' ? 'dark' : 'light'); }""")
        page.wait_for_timeout(800)
        after = page.evaluate(_RECTS_JS, LAYOUT_SELECTORS)
        if before != after:
            bad.append(f"rects moved across theme switch: {before} -> {after}")
    finally:
        ctx.close()
    return not bad, bad or [f"CLS {cls:.4f}; {len(before)} box(es) stable across theme switch"]


def _is_mac(url):
    return urlparse(url).path.rstrip("/") in ("/mac", "/mac.html")


_THEME_STATE_JS = """() => {
  const metas = Array.from(document.querySelectorAll('meta[name=theme-color]'));
  const plain = metas.filter(m => !m.media);
  const m = plain.length ? plain[plain.length - 1] : metas.find(m => matchMedia(m.media).matches);
  return {theme: document.documentElement.getAttribute('data-theme'),
          color: m ? m.content : null, metas: metas.length};
}"""


def _color_is_dark(c: str):
    h = c.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    try:
        return sum(int(h[i:i + 2], 16) for i in (0, 2, 4)) / 3 < 128
    except ValueError:
        return None


def check_F8(browser, url):
    """Fresh profile, no hash/storage: data-theme="dark" ("light" on /mac) whatever the OS
    scheme (both prefers-color-scheme values are run); then, when the page has a visible
    theme toggle, click it and require the opposite theme. Each state must also carry a
    matching theme-color meta (when the page has any; doc pages have none)."""
    want0 = "light" if _is_mac(url) else "dark"
    bad, seen = [], []

    def judge(tag, st, want):
        seen.append(f"{tag}: data-theme={st['theme']!r}")
        if st["theme"] != want:
            bad.append(f"[{tag}] data-theme={st['theme']!r}, want {want!r}")
        if st["color"]:
            d = _color_is_dark(st["color"])
            if d is not None and d != (want == "dark"):
                bad.append(f"[{tag}] theme-color {st['color']} does not follow {want}")

    for scheme in ("dark", "light"):
        ctx, page, _ = _new_page(browser, color_scheme=scheme)
        try:
            _goto(page, url.split("#")[0])
            page.wait_for_timeout(300)
            judge(f"os={scheme}", page.evaluate(_THEME_STATE_JS), want0)
            toggle = page.query_selector("[data-theme-toggle]")
            if toggle and toggle.is_visible():
                toggle.click()
                page.wait_for_timeout(700)
                judge(f"os={scheme},toggled", page.evaluate(_THEME_STATE_JS),
                      "dark" if want0 == "light" else "light")
        finally:
            ctx.close()
    return not bad, bad + seen


def check_F10(browser, url):
    ctx, page, _ = _new_page(browser, reduced_motion="reduce")
    try:
        _goto(page, url)
        page.wait_for_timeout(1000)
        running = page.evaluate("""() => document.getAnimations()
          .filter(a => a.playState === 'running')
          .map(a => (a.animationName || a.transitionProperty || 'anim') + '@' +
                    (a.effect && a.effect.target ? a.effect.target.tagName.toLowerCase() : '?'))""")
    finally:
        ctx.close()
    return not running, [f"running animation under reduce: {a}" for a in running[:10]] or [
        "0 running animations"]


_F11_JS = """primary => {
  const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const out = [];
  const sel = 'button, [role=button], input:not([type=hidden]), select, textarea, a';
  const all = Array.from(document.querySelectorAll(sel)).filter(vis);
  // WCAG 2.5.8 spacing exception: a target under 24 px passes when a 24 px circle centred on it
  // touches no other target
  const spaced = e => {
    const r = e.getBoundingClientRect(), cx = r.x + r.width / 2, cy = r.y + r.height / 2;
    return all.every(o => {
      if (o === e || o.contains(e) || e.contains(o)) return true;
      const q = o.getBoundingClientRect();
      const dx = Math.max(q.left - cx, 0, cx - q.right), dy = Math.max(q.top - cy, 0, cy - q.bottom);
      return Math.hypot(dx, dy) >= 12;
    });
  };
  for (const e of all) {
    const s = getComputedStyle(e);
    // inline text links are exempt from the 24 px rule (WCAG 2.5.8 inline exception)
    if (e.tagName === 'A' && s.display === 'inline' && !e.matches(primary)) continue;
    const r = e.getBoundingClientRect();
    const need = e.matches(primary) ? 44 : 24;
    if ((r.width < need || r.height < need) && (need === 44 || !spaced(e)))
      out.push((e.tagName.toLowerCase() + '.' + (e.className || '') + ' ' + Math.round(r.width) + 'x' +
                Math.round(r.height) + ' < ' + need).slice(0, 90));
  }
  return {sw: document.documentElement.scrollWidth, iw: innerWidth, small: out, n: all.length};
}"""


def check_F11(browser, url):
    bad = []
    for w in PHONE_WIDTHS:
        ctx, page, _ = _new_page(browser, width=w, height=800)
        try:
            _goto(page, url)
            page.wait_for_timeout(500)
            r = page.evaluate(_F11_JS, PRIMARY_SELECTOR)
        finally:
            ctx.close()
        if r["n"] == 0:
            raise Fail("nothing to check: no visible link/button/input at "
                       f"{w}px (F11 does not allow empty)")
        if r["sw"] > r["iw"]:
            bad.append(f"@{w}: scrollWidth {r['sw']} > innerWidth {r['iw']}")
        bad += [f"@{w}: target {s}" for s in r["small"][:5]]
    return not bad, bad or [f"no overflow or small targets at {PHONE_WIDTHS}"]


# ---- LINKS ----

def _redirect_rules():
    rules = []
    p = ROOT / "_redirects"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.split("#")[0].strip()
            if not line:
                continue
            src = line.split()[0]
            rx = re.escape(src).replace(r"\*", ".*")
            rx = re.sub(r":[A-Za-z_]+", "[^/]+", rx.replace(r"\:", ":"))
            rules.append(re.compile("^" + rx + "$"))
    w = ROOT / "worker.js"  # routes the Worker answers itself (e.g. /dl/mac/*)
    if w.exists():
        src = w.read_text()
        for exact in re.findall(r'pathname\s*===\s*"(/[^"]*)"', src):
            rules.append(re.compile("^" + re.escape(exact) + "$"))
        for pre in re.findall(r'pathname\.startsWith\("(/[^"]*)"\)', src):
            rules.append(re.compile("^" + re.escape(pre) + ".*$"))
    return rules


def check_LINKS(browser, url):
    ctx, page, _ = _new_page(browser)
    try:
        _goto(page, url)
        hrefs = page.evaluate("""() => Array.from(document.querySelectorAll('a[href]'))
          .map(a => a.getAttribute('href'))""")
        ids = set(page.evaluate("Array.from(document.querySelectorAll('[id]')).map(e => e.id)"))
    finally:
        ctx.close()
    if not hrefs:
        raise Fail("nothing to check: the page has no <a href> (LINKS does not allow empty)")
    rules = _redirect_rules()
    bad, ok, external, routed = [], 0, set(), set()
    for h in sorted(set(hrefs)):
        if re.match(r"(mailto|tel|javascript|sms):", h, re.I):
            continue
        full = urljoin(url, h)
        u = urlparse(full)
        if u.scheme in ("http", "https") and u.hostname not in LOCAL:
            external.add(full)
            continue
        target, frag = urldefrag(full)
        if not frag and h.startswith("#"):
            continue
        if target == url.split("#")[0] or h.startswith("#"):
            if frag and frag not in ids and frag != "top":
                bad.append(f"missing anchor #{frag}")
            else:
                ok += 1
            continue
        path = urlparse(target).path
        # classify BEFORE any fetch: a routed path (_redirects / worker.js) is never requested
        if _DOWNLOAD_RX.match(path) or any(r.match(path) for r in rules):
            routed.add(path)
            continue
        cands = [target, target.rstrip("/") + ".html", target.rstrip("/") + "/index.html"]
        try:
            found200 = any(_get(c)[0] == 200 for c in cands)
        except Fail as e:
            bad.append(f"link {h}: {e}")
            continue
        if found200:
            ok += 1
        elif any(r.match(path) for r in rules):
            routed.add(path)
        else:
            bad.append(f"broken link {h} (404)")
    info = [f"{ok} ok, {len(routed)} routed via _redirects, {len(external)} external (not fetched)"]
    info += [f"external: {e}" for e in sorted(external)]
    return not bad, bad + info


CHECKS = {"F1": check_F1, "F3": check_F3, "F5": check_F5, "F7": check_F7, "F8": check_F8,
          "F10": check_F10, "F11": check_F11, "LINKS": check_LINKS}


def run_checks(url: str, names: list[str]) -> list[dict]:
    from playwright.sync_api import sync_playwright
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for n in names:
                try:
                    out = CHECKS[n](browser, url)
                    res = {"check": n, "ok": bool(out[0]), "details": out[1]}
                    if len(out) > 2:
                        res["count"] = out[2]
                except Fail as e:
                    res = {"check": n, "ok": False, "details": [str(e)]}
                except Exception as e:  # a crash or timeout is a FAIL, never a pass
                    res = {"check": n, "ok": False,
                           "details": [f"harness error: {type(e).__name__}: {str(e)[:300]}"]}
                results.append(res)
        finally:
            browser.close()
    return results


def main(argv: list[str]) -> int:
    args = argv[1:]
    url, checks, as_json, bad = None, None, False, False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--url" and i + 1 < len(args):
            i += 1
            url = args[i]
        elif a == "--check" and i + 1 < len(args):
            i += 1
            checks = [c.strip().upper() for c in args[i].split(",") if c.strip()]
        elif a == "--json":
            as_json = True
        else:
            bad = True
        i += 1
    if checks == ["ALL"]:
        checks = list(CHECKS)
    if (bad or not url or not checks or urlparse(url).hostname not in LOCAL
            or any(c not in CHECKS for c in checks)):
        print(__doc__, file=sys.stderr)
        return 2
    results = run_checks(url, checks)
    if as_json:
        print(json.dumps({"url": url, "results": results}, indent=1))
    else:
        for r in results:
            print(f"{r['check']} {'PASS' if r['ok'] else 'FAIL'} " + "; ".join(r["details"]))
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
