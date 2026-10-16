"""C1: the checkpoint input module (assets/shared/checkpoint-input.js) against labelled fixtures.

The labels (tests/fixtures/input/LABELS.md) were committed before the module existed; only timing tolerances come
from the config (the module's DEFAULTS, which must match docs/checkpoint-config.md v1).
Run: uv run --with pytest python3 -m pytest tests/checkpoint -q   (needs node on PATH)
"""
from __future__ import annotations

import functools
import importlib.util
import json
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tests" / "checkpoint" / "run_detector.mjs"
FIX = ROOT / "tests" / "fixtures" / "input"
DOC = ROOT / "docs" / "checkpoint-config.md"


def _node(*args: str) -> str:
    r = subprocess.run(["node", str(RUNNER), *args], capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert r.returncode == 0, f"run_detector.mjs failed:\n{r.stderr}"
    return r.stdout


@functools.lru_cache(maxsize=1)
def results() -> dict:
    return json.loads(_node())["fixtures"]


@functools.lru_cache(maxsize=1)
def config() -> dict:
    return json.loads(_node("--config"))


def _labels() -> dict[str, dict]:
    rows = {}
    for line in (FIX / "LABELS.md").read_text().splitlines():
        m = re.match(r"^\| `([a-z0-9-]+)` \|(.*)\|\s*$", line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        _scenario, steps, jumps, prevented, classes = cells
        rows[m.group(1)] = {
            "steps": [] if steps == "—" else [int(s) for s in steps.split()],
            "jumps": [] if jumps == "—" else jumps.split(),
            "prevented": prevented,
            "classes": [] if classes == "—" else classes.split(),
        }
    return rows


LABELS = _labels()


def _fixture(name: str) -> dict:
    return json.loads((FIX / f"{name}.json").read_text())


def _expected_prevented(spec: str, fx: dict) -> list[int] | int:
    evs = fx["events"]
    if spec == "all":
        return list(range(len(evs)))
    if spec == "none":
        return []
    if spec.startswith("tag:"):
        return [i for i, e in enumerate(evs) if e.get("tag") == spec[4:]]
    if spec.startswith("from:"):
        return [i for i, e in enumerate(evs) if e["t"] >= int(spec[5:])]
    return int(spec)


def _gesture_classes(trace: list[dict]) -> list[str]:
    order, cls = [], {}
    for rec in trace:
        if rec["gesture"] not in cls:
            order.append(rec["gesture"])
            cls[rec["gesture"]] = rec["cls"]
    return [cls[g] for g in order]


def test_labels_cover_every_fixture():
    files = {p.stem for p in FIX.glob("*.json")}
    assert files == set(LABELS), f"unlabelled: {sorted(files - set(LABELS))}; missing: {sorted(set(LABELS) - files)}"
    assert len(files) >= 60


def test_fixtures_match_generator():
    spec = importlib.util.spec_from_file_location("gen_fixtures", FIX / "gen_fixtures.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    built = gen.build()
    for name, data in built.items():
        assert json.loads((FIX / f"{name}.json").read_text()) == data, f"{name}.json is stale: rerun gen_fixtures.py"


@pytest.mark.parametrize("name", sorted(LABELS))
def test_labelled_recordings(name):
    lab, got, fx = LABELS[name], results()[name], _fixture(name)
    assert [s["dir"] for s in got["steps"]] == lab["steps"], f"{name}: steps {got['steps']}"
    assert [j["target"] for j in got["jumps"]] == lab["jumps"], f"{name}: jumps {got['jumps']}"
    want = _expected_prevented(lab["prevented"], fx)
    if isinstance(want, int):
        assert len(got["prevented"]) == want, f"{name}: prevented {got['prevented']}"
    else:
        assert got["prevented"] == want, f"{name}: prevented {got['prevented']}"
    assert _gesture_classes(got["trace"]) == lab["classes"], f"{name}: classes {got['trace'][:3]}…"


def test_classification_sticky_per_gesture():
    """ICX-CLASS.1/.2/.3: every event's class equals its gesture's first event; a new gesture is classed afresh."""
    for name, got in results().items():
        first = {}
        for rec in got["trace"]:
            first.setdefault(rec["gesture"], rec["cls"])
            assert rec["cls"] == first[rec["gesture"]], f"{name}: event {rec['i']} changed class mid-gesture"
    r = results()
    # a notch gesture keeps its class while smooth-looking (4 px) events arrive inside QUIET_NOTCH
    tr = r["cls-notch-then-drag-180"]["trace"]
    assert len({t["gesture"] for t in tr}) == 1 and {t["cls"] for t in tr} == {"notch"} and len(tr) == 21
    # the gap that ends a gesture is the RUNNING gesture's threshold (smooth 140 < 200 < notch 220): a new notch gesture
    assert _gesture_classes(r["cls-drag-then-notch-200"]["trace"]) == ["smooth", "notch"]
    # reset per gesture: notch then smooth
    assert _gesture_classes(r["cls-notch-then-flick"]["trace"]) == ["notch", "smooth"]
    # D1: a smooth flick opening at >= 50 px is notch for its whole gesture, and still steps once
    for n in ("d1-first-60", "d1-first-50"):
        assert {t["cls"] for t in r[n]["trace"]} == {"notch"} and len(r[n]["steps"]) == 1
    assert {t["cls"] for t in r["d1-first-49"]["trace"]} == {"smooth"}


def test_step_timing_tolerances_from_config():
    """Repeats are >= REPEAT_MS apart, rises >= MIN_STEP_MS after the previous step, held keys >= KEY_REPEAT_MS."""
    d = config()["DEFAULTS"]
    for name, got in results().items():
        steps = got["steps"]
        for prev, cur in zip(steps, steps[1:]):
            gap = cur["t"] - prev["t"]
            if cur["trigger"] == "repeat":
                assert gap >= d["REPEAT_MS"], f"{name}: repeat after {gap} ms"
            if cur["trigger"] == "rise":
                assert gap >= d["MIN_STEP_MS"], f"{name}: rise after {gap} ms"
            if cur["trigger"] == "key-repeat":
                assert gap >= d["KEY_REPEAT_MS"], f"{name}: key repeat after {gap} ms"
    held = [s["t"] for s in results()["key-held-arrowdown"]["steps"]]
    assert held == [0, 500, 929, 1358, 1787]
    spin = [s["t"] for s in results()["mw-spin-sustained"]["steps"]]
    assert spin == [0, 880, 1760]


def test_run_detector_is_deterministic():
    assert _node() == _node()


def test_config_version_one_place_and_matches_docs():
    cfg = config()
    assert cfg["CONFIG_VERSION"] == 1
    text = DOC.read_text()
    assert text.startswith("# Checkpoint input config — version 1")
    d = cfg["DEFAULTS"]
    for const in ("MIN_DELTA", "START_PX", "START_WIN", "QUIET_SMOOTH", "QUIET_NOTCH", "W_NOW", "W_PREV", "CONT_GAP",
                  "TAIL_GATE", "RISE_RATIO", "V_RISE_MIN", "MIN_STEP_MS", "REPEAT_MS", "SUSTAIN_K", "REVERSE_PX",
                  "KEY_REPEAT_MS", "TOUCH_SLOP", "DIR_RATIO", "LINE_PX"):
        m = re.search(rf"^\| `{const}` \| ([0-9.]+)", text, re.M)
        assert m, f"{const} not in docs/checkpoint-config.md"
        assert float(m.group(1)) == d[const], f"{const}: module {d[const]} != docs {m.group(1)}"
    assert re.search(r"`REVERSE_PX` \| 12 px summed within 80 ms", text) and d["REVERSE_WIN"] == 80
    assert re.search(r"`SWIPE_PX` \| max\(36 px, 5 % of the pin height\)", text)
    assert d["SWIPE_MIN_PX"] == 36 and d["SWIPE_FRAC"] == 0.05
    assert re.search(r"`SWIPE_VEL` \| 0.4 px/ms \(at `touchend`, with `abs\(dy\)` ≥ 14 px\)", text)
    assert d["SWIPE_VEL"] == 0.4 and d["SWIPE_END_MIN_PX"] == 14
    assert re.search(r"Notch hint: first delta \| ≥ 50 px with no event in the previous 30 ms", text)
    assert d["NOTCH_HINT_PX"] == 50 and d["NOTCH_HINT_GAP"] == 30
    assert re.search(r"`visualViewport.scale > 1.01`", text) and d["ZOOM_SCALE"] == 1.01
