"""C7: the ?ci-tune overlay + recorder (assets/shared/checkpoint-tune.js).

Run: uv run --with pytest --with playwright python3 -m pytest tests/checkpoint/test_tune_flag.py -q   (needs node)
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = "/tests/fixtures/input/tune.html"
TUNE = "checkpoint-tune.js"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def open_page(browser, url):
    ctx = browser.new_context(viewport={"width": 1000, "height": 700})
    page = ctx.new_page()
    urls, errors = [], []
    page.on("request", lambda r: urls.append(r.url))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_timeout(300)
    return ctx, page, urls, errors


def wheel_flick(page):
    page.mouse.move(400, 300)
    for dy in (3, 8, 16, 26, 34, 38, 36, 34, 32, 30):
        page.mouse.wheel(0, dy)
        page.wait_for_timeout(16)
    page.wait_for_timeout(300)


def test_not_requested_without_flag(browser, site_url):
    for path in (FIXTURE, "/"):
        ctx, page, urls, errors = open_page(browser, site_url + path)
        assert not [u for u in urls if TUNE in u], f"{path}: tune script requested without the flag"
        assert page.locator("#ci-tune").count() == 0
        assert page.evaluate("() => typeof window.__ciTune") == "undefined"
        assert not errors
        ctx.close()
    # a similarly named param must not trigger it
    ctx, page, urls, _ = open_page(browser, site_url + FIXTURE + "?ci-tuned=1")
    assert not [u for u in urls if TUNE in u]
    ctx.close()


def test_overlay_with_flag(browser, site_url):
    ctx, page, urls, errors = open_page(browser, site_url + FIXTURE + "?ci-tune")
    assert [u for u in urls if u.endswith(TUNE)], "flag did not load the overlay"
    panel = page.locator("#ci-tune")
    assert panel.count() == 1
    # live thresholds: every DEFAULTS constant is listed with its current value
    defaults = page.evaluate("() => FECheckpoint.DEFAULTS")
    shown = page.evaluate("() => Object.fromEntries([...document.querySelectorAll('#ci-tune input[data-key]')].map(i => [i.dataset.key, parseFloat(i.value)]))")
    assert shown == defaults
    # records: events appear and the shadow detector reports a step
    page.click("#ci-tune button:text('Record')")
    wheel_flick(page)
    page.keyboard.press("ArrowDown")
    st = page.evaluate("() => window.__ciTune.state()")
    assert st["recording"] and st["events"] >= 10
    assert any(s["src"] == "wheel" and s["dir"] == 1 for s in st["steps"])
    assert "REC" in page.locator("#ci-tune-status").inner_text()
    # editing a threshold rebuilds the shadow with it and marks it tuned
    page.fill("#ci-tune input[data-key=START_PX]", "500")
    page.dispatch_event("#ci-tune input[data-key=START_PX]", "change")
    assert page.evaluate("() => window.__ciTune.state().overrides") == {"START_PX": 500}
    page.click("#ci-tune button:text('Clear')")
    wheel_flick(page)
    assert not [s for s in page.evaluate("() => window.__ciTune.state().steps") if s["src"] == "wheel"], "START_PX=500 should block the flick"
    assert not errors
    ctx.close()


def test_dev_only_no_network_no_storage(browser, site_url):
    ctx, page, urls, _ = open_page(browser, site_url + FIXTURE + "?ci-tune")
    before = len(urls)
    page.click("#ci-tune button:text('Record')")
    wheel_flick(page)
    page.keyboard.press("PageDown")
    page.click("#ci-tune button:text('Copy')")
    page.wait_for_timeout(200)
    assert len(urls) == before, "overlay made a request: " + str(urls[before:])
    assert page.evaluate("() => [localStorage.length, sessionStorage.length, document.cookie]") == [0, 0, ""]
    # typed text in a field is never recorded
    page.fill("#field", "secret")
    page.press("#field", "a")
    rec = page.evaluate("() => window.__ciTune.exportRecording()")
    assert not [e for e in rec["events"] if e["type"] == "keydown" and len(e["key"]) == 1 and e["key"] != " "]
    assert "secret" not in json.dumps(rec)
    ctx.close()


def test_recording_is_fixture_format(browser, site_url, tmp_path):
    ctx, page, _urls, _ = open_page(browser, site_url + FIXTURE + "?ci-tune")
    page.click("#ci-tune button:text('Record')")
    wheel_flick(page)
    page.wait_for_timeout(400)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Home")
    with page.expect_download() as dl:
        page.click("#ci-tune button:text('Export')")
    path = dl.value.path()
    rec = json.loads(pathlib.Path(path).read_text())
    ctx.close()
    assert rec["events"] and {"html", "body"} <= set(rec["nodes"]) and rec["env"]["innerHeight"] == 700
    # same keys the checked-in fixtures carry
    ref = json.loads((ROOT / "tests" / "fixtures" / "input" / "mw-click.json").read_text())
    assert set(ref) <= set(rec)
    assert set(ref["env"]) == set(rec["env"])

    # a private copy of the runner's tree, so the real fixtures dir stays untouched
    (tmp_path / "tests" / "checkpoint").mkdir(parents=True)
    (tmp_path / "tests" / "fixtures" / "input").mkdir(parents=True)
    (tmp_path / "assets" / "shared").mkdir(parents=True)
    shutil.copy(ROOT / "tests" / "checkpoint" / "run_detector.mjs", tmp_path / "tests" / "checkpoint")
    shutil.copy(ROOT / "assets" / "shared" / "checkpoint-input.js", tmp_path / "assets" / "shared")
    (tmp_path / "tests" / "fixtures" / "input" / "rec.json").write_text(json.dumps(rec))
    r = subprocess.run(["node", str(tmp_path / "tests" / "checkpoint" / "run_detector.mjs")],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)["fixtures"]["rec"]
    assert any(s["src"] == "wheel" and s["dir"] == 1 for s in out["steps"]), out
    assert any(s["src"] == "key" for s in out["steps"])
    assert out["jumps"] == [{"src": "key", "t": out["jumps"][0]["t"], "target": "first"}]
