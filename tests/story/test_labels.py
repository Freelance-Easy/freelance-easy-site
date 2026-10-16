"""B3: chapter names, no numbers (DEC-4, decisions-2026-10-15 #3; ICX-DEST.3).

The homepage rail and the caption eyebrows (span.step, including the one heroSplit injects on the phone story) use the
nine decided names and carry no digits. Beat ids and data-go may keep "grow"; no visible word is "Grow" (G12).

Run: python3 -m pytest tests/story/test_labels.py -q
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
NAMES = ["New invoice", "Templates", "Invoices", "Dashboard", "Email", "Your data", "Price", "A note", "Get the app"]
GO = ["make", "look", "know", "grow", "chase", "yours", "price", "note", "end"]
EYEBROW_GO = ["look", "know", "grow", "chase"]


def _built_index() -> str:
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build-site.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return (ROOT / "index.html").read_text()


class _Rail(HTMLParser):
    """Collects each rail link (attrs + its visible name, B5) and each span.step with its chapter."""

    def __init__(self):
        super().__init__()
        self.in_nav = False
        self.btns: list[dict] = []
        self.cur: dict | None = None
        self.hid = False
        self.copy = None
        self.steps: list[tuple[str, str]] = []
        self.in_step = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "nav" and "story-nav" in cls:
            self.in_nav = True
        elif self.in_nav and tag == "a":  # B5 (rail v3): links, not buttons
            self.cur = {"attrs": a, "hidden_text": ""}
            self.btns.append(self.cur)
        elif self.in_nav and tag == "span" and "nm" in cls:  # B5: the always-visible name
            self.hid = True
        if a.get("data-copy"):
            self.copy = a["data-copy"]
        if tag == "span" and "step" in cls:
            self.in_step = True
            self.steps.append((self.copy or "", ""))

    def handle_endtag(self, tag):
        if tag == "nav":
            self.in_nav = False
        elif tag == "span":
            self.hid = False
            self.in_step = False

    def handle_data(self, data):
        if self.hid and self.cur is not None:
            self.cur["hidden_text"] += data
        if self.in_step:
            c, t = self.steps[-1]
            self.steps[-1] = (c, t + data)


def _parse():
    p = _Rail()
    p.feed(_built_index())
    return p


def _hero_split_source() -> str:
    js = (ROOT / "assets" / "story" / "site.js").read_text()
    i = js.index("function heroSplit(")
    return js[i:js.index("\n  }\n", i)]


def test_label_set():
    p = _parse()
    assert [b["attrs"].get("data-go") for b in p.btns] == GO
    assert [b["attrs"].get("data-name") for b in p.btns] == NAMES
    assert [b["hidden_text"].strip() for b in p.btns] == NAMES
    steps = dict(p.steps)
    for go in EYEBROW_GO:
        assert steps[go].strip() == NAMES[GO.index(go)], (go, steps[go])
    m = re.search(r'stepEl\.textContent = "([^"]*)"', _hero_split_source())
    assert m and m.group(1) == NAMES[0], m


def test_no_numerals():
    p = _parse()
    for b in p.btns:
        assert not re.search(r"\d", b["hidden_text"]), b
        assert not re.search(r"\d", b["attrs"].get("data-name") or ""), b
        assert not b["attrs"].get("data-n"), b
    for go, t in p.steps:
        assert not re.search(r"\d", t), (go, t)
    for lit in re.findall(r'(?:textContent|innerText)\s*=\s*"([^"]*)"', _hero_split_source()):
        assert not re.search(r"\d", lit), lit


def test_no_grow_visible():
    p = _parse()
    shown = [b["attrs"].get("data-name") or "" for b in p.btns] + [b["hidden_text"] for b in p.btns]
    shown += [t for _, t in p.steps]
    shown += re.findall(r'(?:textContent|innerText)\s*=\s*"([^"]*)"', _hero_split_source())
    for t in shown:
        assert not re.search(r"grow|track", t, re.I), t
    assert "grow" in [b["attrs"].get("data-go") for b in p.btns]  # ids may keep it
