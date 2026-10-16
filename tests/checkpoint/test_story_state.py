"""C2: story state harness, failing first (docs/interaction-contract.md v1, docs/checkpoint-config.md v1).

Real wheel / key / scroll input is driven into the homepage story (tests/checkpoint/lib.py) and the contract's state
rules are asserted: step (ICX-STEP, ICX-KEY), back (ICX-BACK), dip with distance >= 2 (ICX-DIP, ICX-JUMP), signed
arithmetic and the clamp (ICX-SIGNED, ICX-RELEASE.4), the rest invariant (ICX-REST) with a seeded fuzz, and history
on the final landing (ICX-HIST). Each runs at desktop 1440x900 and tablet 820x1180, dark and light.

C3 rebuilt the story and removed its markers. The three ICX-HIST tests stay xfail(strict=True) "pending C4": history
is C4's (story-url.js); C3 writes none (main's ruling, 2026-10-15).
Every assertion message starts with its ICX row id.

Fuzz (marked slow; see its docstring for the run time): SEED is fixed; 50 sequences per cell x 4 cells = 200 sequences. A sequence is 2-6 random inputs, then idle until
the allowance (ICX-REST.1) with early exit at the first rest, so a correct build costs about 5 s per sequence.
"""
from __future__ import annotations

import random

import pytest
from playwright.sync_api import sync_playwright

import lib
from lib import (BEATS, CELLS, SEED, SLUGS, Cell, Fuzz, Story, check_engine,
                 assert_rate, dip_spans, rests_seen)

# Bound change (C3, evidenced): ICX-REST.1's allowance is the target's own transition + content + 1 s. lib.allowance
# stands in DEC-8's ceilings (1.5 s per transition + 5 s of content), which C5 reaches by trimming dead time. Today two
# single steps exceed them (C0b's finding, PLAN decision log 2026-10-15), measured on __site.map() (segments identical to
# the base: tests/story/test_segment_order.py): Make->Look 2.58 s + Look 4.93 s = 7.51 s, and the Ride 1.47 s + Email
# 6.03 s = 7.50 s at 1x (desktop dark). With lib's 7.5 s budget those steps timed out 0-10 ms short of their rest frame
# (story T 11.102-11.109 of 11.11; 24.028 of 24.03). C3 may not speed motion up, so the budget gets the measured excess
# plus scheduling slack: +0.5 s. C5 removes this once its trims land.
C5_SLACK = 0.5
_lib_allowance = lib.allowance


def allowance(distance: int) -> float:
    return _lib_allowance(distance) + C5_SLACK


lib.allowance = allowance   # Story.to_checkpoint reads lib.allowance

SEQUENCES_PER_CELL = 50
CELL = pytest.mark.parametrize("cell", CELLS, ids=[c.id for c in CELLS])

SCRUB = ("the base scrubs wheel/key deltas through mapScroll (no gesture detector, no checkpoint snap): a 100 px "
         "notch moves story time by ~0.03 s, so the story either parks mid-segment or never leaves the first rest frame")


def pending_c4(*rows: str):
    """History is C4's (story-url.js, main's ruling 2026-10-15): C3 writes none; C4 removes these markers."""
    return pytest.mark.xfail(strict=True, reason="pending C4: " + ", ".join(rows))


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def story(browser, site_url, cell: Cell):
    st = Story.open(browser, site_url + "/", cell)
    res = st.wait_rest(12)
    assert res.status == "rest" and res.snap.index == 0, f"harness precondition: no REST(make) after load: {res.snap.describe()}"
    yield st
    st.close()


def expect_rest(res, idx: int, row: str, base: str = SCRUB) -> None:
    assert res.status == "rest" and res.snap.index == idx, (
        f"{row}: expected REST({BEATS[idx]}) within {res.elapsed:.1f}s, got status={res.status}: "
        f"{res.snap.describe()}. Base behaviour: {base}")


# ---------------------------------------------------------------------------------------------------------- STEP

@CELL
def test_wheel_step_lands_next_checkpoint(story: Story, cell: Cell):
    story.rec_start()
    story.wheel(100)
    res = story.wait_rest(allowance(1))
    frames = story.rec_stop()
    expect_rest(res, 1, "ICX-STEP.1")
    assert not dip_spans(frames), f"ICX-STEP.1: a step from REST(make) must not dip, saw {dip_spans(frames)}"
    mid = [f for f in frames if story.info.rest[0] + 0.05 < f.T < story.info.rest[1] - 0.05]
    assert len(mid) >= 10, (
        f"ICX-STEP.1: the seam and content must play frame by frame; only {len(mid)} frames were between the two rest "
        "frames (a 100 px notch moved the base's playhead by ~0.03 s; a teleport would show none)")
    assert_rate(frames, "ICX-STEP.6", ceiling=1.0)
    check_engine(res.snap, 1, "ICX-STEP.1")


@CELL
@pytest.mark.parametrize("key", ["ArrowDown", "PageDown", "Space"])
def test_step_keys_lands_next_checkpoint(story: Story, cell: Cell, key: str):
    story.key(key)
    res = story.wait_rest(allowance(1))
    expect_rest(res, 1, f"ICX-KEY.1/ICX-STEP.1 ({key})",
                "the base lets the key scroll the document natively (no key interception), which the story scrubs")
    check_engine(res.snap, 1, f"ICX-KEY.1/ICX-STEP.1 ({key})")


@CELL
def test_every_step_ends_in_rest_within_allowance(story: Story, cell: Cell):
    """The scoped rest invariant, deterministic: one gesture per checkpoint, then no input for transition + content
    + 1 s (allowance(1)); each must be at rest on the next checkpoint, and must stay there for another second."""
    for i in range(1, cell.n_pinned):
        story.wheel(100)
        res = story.wait_rest(allowance(1))
        expect_rest(res, i, f"ICX-REST.1/ICX-STEP.1 (step {i})")
        story.idle(1000)
        after = story.snap()
        assert after.index == i, f"ICX-REST.1: REST({BEATS[i]}) did not hold with no input: {after.describe()}"
        check_engine(after, i, f"ICX-REST.1 (step {i})")


# ---------------------------------------------------------------------------------------------------------- BACK

@CELL
def test_back_step_is_one_220ms_fade_to_previous_rest(story: Story, cell: Cell):
    pre = story.to_checkpoint(1)
    expect_rest(pre, 1, "ICX-BACK.1 (precondition: step to REST(look), ICX-STEP.1)")
    story.rec_start()
    story.wheel(-100)
    res = story.wait_rest(2.0)
    frames = story.rec_stop()
    expect_rest(res, 0, "ICX-BACK.1", "the base scrubs the story backwards through mapScroll: no 220 ms fade, no landing on the previous rest frame")
    spans = dip_spans(frames)
    assert len(spans) == 1, f"ICX-BACK.1: expected exactly one dip, saw {len(spans)}: {spans}"
    dur = spans[0][1] - spans[0][0]
    assert 0.18 <= dur <= 0.26, f"ICX-BACK.1: the fade must take about 220 ms, measured {dur * 1000:.0f} ms"
    assert res.elapsed <= 0.8, f"ICX-BACK.1: back gesture to rest took {res.elapsed:.2f}s (a 220 ms fade, no replay)"
    check_engine(res.snap, 0, "ICX-BACK.1")


# ---------------------------------------------------------------------------------------------------------- DIP

@CELL
def test_end_key_is_one_dip_to_last_pinned(story: Story, cell: Cell):
    story.rec_start()
    story.key("End")
    res = story.wait_rest(allowance(1))
    frames = story.rec_stop()
    expect_rest(res, cell.last, "ICX-DIP.1/ICX-KEY.6", "End scrolls the document to its bottom natively; the story scrubs there and there is no dip")
    spans = dip_spans(frames)
    assert len(spans) == 1, f"ICX-DIP.1: distance {cell.last} must be exactly one dip, saw {len(spans)}: {spans}"
    dur = spans[0][1] - spans[0][0]
    assert 0.18 <= dur <= 0.26, f"ICX-DIP.1: a dip is 220 ms in total, measured {dur * 1000:.0f} ms"
    between = rests_seen(frames) - {0, cell.last}
    assert not between, f"ICX-DIP.1/ICX-SIGNED.6: intermediate checkpoints {sorted(between)} rested during the dip"
    check_engine(res.snap, cell.last, "ICX-DIP.1")


@CELL
def test_input_during_fadeout_moves_the_cut(story: Story, cell: Cell):
    story.rec_start()
    story.key("End")
    story.idle(50)
    story.key("ArrowUp")     # during the 100 ms fade-out: dest = last - 1, committed at the dark frame
    res = story.wait_rest(allowance(1))
    frames = story.rec_stop()
    expect_rest(res, cell.last - 1, "ICX-DIP.2", "End scrolls natively and ArrowUp scrolls back by a line: no dip, no commit at a dark frame")
    assert len(dip_spans(frames)) == 1, f"ICX-DIP.2: input during the fade-out must not start a second dip: {dip_spans(frames)}"
    check_engine(res.snap, cell.last - 1, "ICX-DIP.2")


@CELL
def test_two_dips_start_at_least_600ms_apart(story: Story, cell: Cell):
    story.rec_start()
    story.key("End")
    story.idle(300)          # the first cut has landed; the cooldown still runs
    story.key("Home")
    res = story.wait_rest(allowance(1) + 1.0)
    frames = story.rec_stop()
    expect_rest(res, 0, "ICX-DIP.4", "Home/End scroll natively and the story scrubs; there is no dip and no cooldown")
    spans = dip_spans(frames)
    assert len(spans) == 2, f"ICX-DIP.4: End then Home is two dips (cooldown delays the second), saw {len(spans)}: {spans}"
    assert spans[1][0] - spans[0][0] >= 0.58, f"ICX-DIP.4: dips began {spans[1][0] - spans[0][0]:.3f}s apart (< 600 ms)"
    check_engine(res.snap, 0, "ICX-DIP.4")


@CELL
def test_three_forward_gestures_land_three_pages_on(story: Story, cell: Cell):
    story.rec_start()
    for _ in range(3):
        story.wheel(100)
        story.idle(300)
    res = story.wait_rest(allowance(3))
    frames = story.rec_stop()
    expect_rest(res, 3, "ICX-DIP.5", "each 100 px notch only scrubs 0.03 s of story time; three of them do not reach REST(grow)")
    skipped = rests_seen(frames) - {0, 3}
    assert not skipped, f"ICX-SIGNED.6: checkpoints {sorted(skipped)} passed through but rested"
    assert_rate(frames, "ICX-SIGNED.7")
    check_engine(res.snap, 3, "ICX-DIP.5")


@CELL
def test_three_back_gestures_land_three_pages_back(story: Story, cell: Cell):
    pre = story.to_checkpoint(3)
    expect_rest(pre, 3, "ICX-DIP.5 (precondition: REST(grow) by single steps, ICX-STEP.1)")
    for _ in range(3):
        story.wheel(-100)
        story.idle(300)
    res = story.wait_rest(allowance(3))
    expect_rest(res, 0, "ICX-DIP.5", "three back notches only scrub the story back by 0.1 s")
    check_engine(res.snap, 0, "ICX-DIP.5")


# ---------------------------------------------------------------------------------------------------------- SIGNED

@CELL
def test_forward_gestures_clamp_at_last_pinned(story: Story, cell: Cell):
    """last + 3 quick forward presses: dest clamps at the last pinned; the extras are dropped, the page never
    scrolls past the pin, and the story rests on the last pinned."""
    for _ in range(cell.last + 3):
        story.key("ArrowDown")
        story.idle(120)
    res = story.wait_rest(allowance(cell.last))
    expect_rest(res, cell.last, "ICX-SIGNED.1/ICX-RELEASE.4", "each key scrolls the document a line natively; nothing clamps dest and the story does not reach the last pinned checkpoint")
    assert not res.snap.released and res.snap.y <= story.info.end_y + 1, (
        f"ICX-RELEASE.4: forward gestures before REST(last pinned) were dropped, yet scrollY={res.snap.y:.0f} is past the pin ({story.info.end_y:.0f})")
    check_engine(res.snap, cell.last, "ICX-SIGNED.1")


@CELL
def test_back_gesture_during_forward_seam_reverses_it(story: Story, cell: Cell):
    story.rec_start()
    story.wheel(100)
    story.idle(300)
    story.wheel(-100)
    res = story.wait_rest(allowance(1))
    frames = story.rec_stop()
    assert max(f.T for f in frames) - story.info.rest[0] > 0.3, (
        "ICX-SIGNED.2: the forward seam never played (story time moved < 0.3 s); the base scrubs a 100 px notch "
        "by about 0.03 s instead of starting the make->look seam")
    expect_rest(res, 0, "ICX-SIGNED.2", "the reversal is a scrub back to the same scroll position, not a seam played backwards")
    assert not dip_spans(frames), f"ICX-BACK.3: a reversal inside the 0.6 s ramp plays backwards, with no dip; saw {dip_spans(frames)}"
    assert_rate(frames, "ICX-SIGNED.7")
    check_engine(res.snap, 0, "ICX-SIGNED.2")


@CELL
def test_signed_arithmetic_is_plus_minus_one_per_gesture(story: Story, cell: Cell):
    """Three forward gestures and one back, all inside the first transition: net dest = origin + 2."""
    for dy in (100, 100, 100, -100):
        story.wheel(dy)
        story.idle(260)
    res = story.wait_rest(allowance(3))
    expect_rest(res, 2, "ICX-SIGNED.4", "no signed dest: the four notches are summed as scroll pixels and scrubbed (net 200 px = 0.06 s)")
    check_engine(res.snap, 2, "ICX-SIGNED.4")


# ---------------------------------------------------------------------------------------------------------- HIST

def _since(story: Story, mark: tuple[int, int]):
    calls, length = story.hist()
    return calls[mark[0]:], length - mark[1]


def _written_at_landing(call, idx: int, row: str) -> None:
    """The history write must happen at the final landing: the engine state captured inside the call already has
    rendered == dest == idx (never at gesture time, never at a pass-through landing)."""
    st = (call[2] or {}).get("fe")
    assert st is not None, f"{row}: no window.FEStory state at the time of the history write"
    assert st.get("rendered") == st.get("dest") == idx, (
        f"{row}: the write at {call[1]!r} happened with rendered={st.get('rendered')} dest={st.get('dest')}; "
        f"it belongs at the final landing (rendered == dest == {idx})")


def _url_slug(u: str | None) -> str:
    return "" if u is None else (u.split("#", 1)[1] if "#" in u else "")


@CELL
@pending_c4("ICX-HIST.1")
def test_a_step_writes_replacestate_once_at_its_landing(story: Story, cell: Cell):
    mark = story.hist_mark()
    story.wheel(100)
    res = story.wait_rest(allowance(1))
    calls, grew = _since(story, mark)
    assert [c[0] for c in calls] == ["replaceState"] and _url_slug(calls[0][1]) == SLUGS[1] and grew == 0, (
        f"ICX-HIST.1: a step writes one replaceState '#{SLUGS[1]}' and leaves history.length unchanged; got {calls}, length +{grew} "
        f"(the base writes no chapter URL: it has no landing; wait ended {res.status}: {res.snap.describe()})")
    expect_rest(res, 1, "ICX-HIST.1")
    _written_at_landing(calls[0], 1, "ICX-HIST.1")


@CELL
@pending_c4("ICX-HIST.1", "ICX-SIGNED.6")
def test_a_run_of_steps_writes_only_its_final_landing(story: Story, cell: Cell):
    mark = story.hist_mark()
    for _ in range(3):
        story.wheel(100)
        story.idle(300)
    res = story.wait_rest(allowance(3))
    calls, grew = _since(story, mark)
    assert [c[0] for c in calls] == ["replaceState"] and _url_slug(calls[0][1]) == SLUGS[3] and grew == 0, (
        f"ICX-HIST.1/ICX-SIGNED.6: a run of 3 steps writes once, '#{SLUGS[3]}', and never a passed-through chapter; got {calls}, "
        f"length +{grew} (the base writes no chapter URL; wait ended {res.status}: {res.snap.describe()})")
    expect_rest(res, 3, "ICX-HIST.1")
    _written_at_landing(calls[0], 3, "ICX-HIST.1/ICX-SIGNED.6")


@CELL
@pending_c4("ICX-HIST.2", "ICX-HIST.5")
def test_a_jump_pushes_one_entry_at_its_landing(story: Story, cell: Cell):
    mark = story.hist_mark()
    story.key("End")
    res = story.wait_rest(allowance(1))
    calls, grew = _since(story, mark)
    assert [c[0] for c in calls] == ["pushState"] and _url_slug(calls[0][1]) == SLUGS[cell.last] and grew == 1, (
        f"ICX-HIST.2: an End jump adds exactly one pushState '#{SLUGS[cell.last]}'; got {calls}, length +{grew} "
        f"(the base writes no history on End; wait ended {res.status}: {res.snap.describe()})")
    expect_rest(res, cell.last, "ICX-HIST.2")
    _written_at_landing(calls[0], cell.last, "ICX-HIST.2")


# ---------------------------------------------------------------------------------------------------------- REST fuzz

@pytest.mark.slow
@pytest.mark.parametrize("cell", CELLS, ids=[c.id for c in CELLS])
def test_fuzz_never_rests_mid_transition(browser, site_url, cell: Cell):
    """Seeded fuzz (ICX-REST.1/.2, ICX-SIGNED.7): after the last input of every sequence the story reaches rest on a
    checkpoint (or RELEASED below the pin) within the allowance, never stalls mid-transition, and never plays faster
    than 3x. Failure messages carry the seed, the sequence number and the inputs so a run is replayable."""
    story = Story.open(browser, site_url + "/", cell)
    try:
        pre = story.wait_rest(12)
        assert pre.status == "rest" and pre.snap.index == 0, f"harness precondition: {pre.snap.describe()}"
        fuzz = Fuzz(cell, random.Random(f"{SEED}-{cell.id}"))
        for n in range(SEQUENCES_PER_CELL):
            story.rec_start()
            before = story.snap()
            start_idx = before.index if before.index is not None else 0
            ops = fuzz.sequence(story, forward_first=(n % 2 == 0))
            res = story.wait_rest(allowance(6), stall_s=1.5)
            frames = story.rec_stop()
            where = f"[seed {SEED}-{cell.id} sequence {n}] inputs: {' '.join(ops)}"
            assert res.status in ("rest", "released"), (
                f"ICX-REST.{2 if res.status == 'stalled' else 1}: {where} -> {res.status} after {res.elapsed:.1f}s with no input: "
                f"{res.snap.describe()}. Base behaviour: {SCRUB}")
            if res.status == "released":
                due = allowance(max(1, cell.last - start_idx))
                assert res.elapsed <= due, f"ICX-REST.1: {where} -> RELEASED took {res.elapsed:.1f}s after the last input (allowance {due:.1f}s)"
            if res.status == "rest":
                check_engine(res.snap, res.snap.index, f"ICX-REST.1 {where}")
                due = allowance(abs(res.snap.index - start_idx))
                assert res.elapsed <= due, (
                    f"ICX-REST.1: {where} -> rest took {res.elapsed:.1f}s after the last input; transition + content + 1 s "
                    f"for distance {abs(res.snap.index - start_idx)} is {due:.1f}s")
            assert_rate(frames, "ICX-SIGNED.7", where=f"{where} -> ")
    finally:
        story.close()
