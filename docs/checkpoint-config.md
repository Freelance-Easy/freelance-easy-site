# Checkpoint input config — version 1

Status: DRAFT version 1, part of the ICX v1 draft (`docs/interaction-contract.md`); not approved.

- **What this is:** every tunable constant of the checkpoint input layer: the R1 §3.4 gesture detector, keyboard
  and touch, the story playhead, and C0a's settle rules. C3 implements them as one table (R1 §3.6's `tune`). C7 tunes
  them on real devices.
- **Version 1 = R1's starting values + C0a's settle constants.** C0a's verdict (`docs/cp-spike-verdict.md`, final run
  on 801bae3, 127 probes) states it ran these unchanged: `QUIET_SMOOTH`, `QUIET_NOTCH`, `START_PX`, `CONT_GAP`,
  `RISE_RATIO`, `V_RISE_MIN`, `MIN_STEP_MS`, `REPEAT_MS`, `REVERSE_PX`, `KEY_REPEAT_MS`, `SWIPE_PX`, `SWIPE_VEL`,
  `TOUCH_SLOP`, `DIR_RATIO`, plus `SUSTAIN_K` with the D1 change. The other rows are R1's starting values that the
  verdict does not list as run. Any change after C7 bumps the version and names the device and evidence that drove it.
- **Range** = where C7 may tune without a contract change. "unset (R1)" = R1 gives no range; C7 sets one from the
  device session.
- **"tune in C7"** marks a value or range C0b picked because R1 left it open.
- Numbers fixed by the contract (220 ms dip, 600 ms cooldown, 0.6 s rush cap, 1.5× reversal, the DEC-8 budgets) are
  listed at the end for reference only. They are not tunable here.

## Detector: wheel (R1 §3.4)

| Constant | Value | Range | Turn it when… | Source |
|---|---|---|---|---|
| `LINE_PX` | 33.3 px per line | fixed | — (normalises `deltaMode` 1) | R1 §3.4 |
| `MIN_DELTA` | 0.5 px | 0–2 px | resting fingers on a Windows precision touchpad step by themselves → raise | R1 §3.4 |
| `START_PX` | 8 px | 4–20 px | brushing the trackpad steps → raise; a deliberate small scroll is ignored → lower | R1 §3.4 |
| `START_WIN` | 120 ms | unset (R1) | (paired with `START_PX`) | R1 §3.4 |
| `QUIET_SMOOTH` | 140 ms | 100–250 ms | — (a tail has no gaps; this only ends slow drags) | R1 §3.4; ICX-CLASS |
| `QUIET_NOTCH` | 220 ms | 150–400 ms | "click, click, click" counts as one → lower; a fast spin splits into several → raise | R1 §3.4; ICX-CLASS |
| `W_NOW` | 50 ms | fixed | — | R1 §3.4 |
| `W_PREV` | 120 ms | fixed | — | R1 §3.4 |
| `CONT_GAP` | 45 ms | 35–70 ms | a high-res ratchet wheel double-steps → lower | R1 §3.4 |
| `TAIL_GATE` | 0.6 | 0.4–0.8 | a second flick right after the first is missed → raise | R1 §3.4 |
| `RISE_RATIO` | 1.8 | 1.3–2.5 | one flick counts twice → raise; a second flick is missed → lower | R1 §3.4 |
| `V_RISE_MIN` | 1000 px/s | 600–2000 px/s | the jitter late in a tail steps → raise | R1 §3.4 |
| `MIN_STEP_MS` | 250 ms | 150–400 ms | a double step at gesture onset → raise | R1 §3.4 |
| `REPEAT_MS` | 850 ms | 600–1200 ms | a long spin feels sluggish → lower; one long trackpad drag goes too far → raise | R1 §3.4 |
| `SUSTAIN_K` | 0.7 (smooth **and notch** gestures, ICX-SETTLE-D1) | 0.5–0.9 | a long notch spin stops repeating → lower | R1 §3.4; C0a D1 (`S1__*-r1notch.json`) |
| `REVERSE_PX` | 12 px summed within 80 ms | 8–20 px (window fixed at 80 ms) — **tune in C7** | a deliberate reversal during a tail is missed → lower; trackpad jitter reverses a step → raise | R1 §3.4 (value; range unset in R1, picked here) |
| Notch hint: first delta | ≥ 50 px with no event in the previous 30 ms | unset (R1) | smooth flicks get the notch hint too often → raise (D1 already guards the repeat) | R1 §3.4 normalisation; C0a D1 |

## Keyboard (R1 §3.4)

| Constant | Value | Range | Turn it when… | Source |
|---|---|---|---|---|
| `KEY_REPEAT_MS` | 420 ms | 300–600 ms — **tune in C7** | a held arrow or PageDown travels too fast to read → raise; it feels sluggish → lower | R1 §3.4 (value; range unset in R1, picked here); ICX-KEY.4 |

## Touch (R1 §3.4)

| Constant | Value | Range | Turn it when… | Source |
|---|---|---|---|---|
| `TOUCH_SLOP` | 8 px | unset (R1) | — | R1 §3.4 |
| `DIR_RATIO` | 1.2 | unset (R1) | — | R1 §3.4 |
| `SWIPE_PX` | max(36 px, 5 % of the pin height) | unset (R1) | — | R1 §3.4 |
| `SWIPE_VEL` | 0.4 px/ms (at `touchend`, with `abs(dy)` ≥ 14 px) | unset (R1) | — | R1 §3.4 |
| Pinch-zoom pan threshold | `visualViewport.scale > 1.01` | unset (C0a) | — | C0a S9; ICX-SETTLE-9 |

## Story playhead (R1 §3.4 "story" rows)

R1's values. Where the contract fixes a bound, the bound is the range ceiling and the contract wins.

| Constant | Value | Range | Turn it when… | Source |
|---|---|---|---|---|
| `RUSH` | 2.5× | unset (R1) | — | R1 §3.4 |
| `RUSH_MAX` | 0.35 s | ≤ 0.6 s (ICX-SIGNED.5) | — | R1 §3.4; contract cap; OPEN-6 |
| `CONTENT_RUSH_MAX` | 0.6 s | ≤ 0.6 s (ICX-SIGNED.5) | — | R1 §3.4; contract cap; OPEN-6 |
| `DIP` | 100 ms out + 120 ms in | the total is fixed at 220 ms (ICX-DIP); the split is unset (R1) | — | R1 §3.3/§3.4 |
| `ABORT_RATE` | 1.5× | fixed as the floor (ICX-BACK.3, ICX-SIGNED.5) | — | R1 §3.4 |
| Rate easing | 12 /s² | unset (R1) | — | R1 §3.2/§3.4 |

## Settle (C0a)

The values the spike ran with (`docs/cp-spike-verdict.md`, "Settle rules"). Evidence = that file's verdict row and
`scratch/cp-spike/evidence/<column>/<row>__<WxH>[-variant].json` on the C0a branch.

| Constant | Value | Range | Turn it when… | Rule | Evidence row |
|---|---|---|---|---|---|
| `ACK_TOL` | 1.5 px | 1–2 px | fractional DPR / browser zoom gives acknowledgement misses (none at 125 %/175 %) | ICX-SETTLE-1 | R1, R9 |
| `ACK_MS` | 400 ms | 250–600 ms | a slow device delivers the scroll event late | ICX-SETTLE-1 | R1 |
| `SCROLLEND_GRACE` | 50 ms | 30–100 ms | autoscroll or find streams settle mid-way → raise | ICX-SETTLE-3, -5 | R6 (`R6__*-nograce.json`: 59 `scrollend`s, 30 settles without it), R3 |
| `SETTLE_IDLE` | 150 ms | 120–250 ms | Safari scrollbar holds snap mid-drag → raise; the settle feels late → lower | ICX-SETTLE-3 | R7 (measured latency ≈ 167 ms with `?noscrollend`) |
| `SETTLE_BACKSTOP` | 700 ms | 500–1500 ms | a held overlay thumb snaps on Chrome → raise | ICX-SETTLE-3 | R5, R6 |
| `REENTRY_STICKY_MS` | 800 ms | 500–1200 ms | iPhone momentum from below still walks back → raise | ICX-SETTLE-4 | R8 (844×390) |
| `RESIZE_GRACE` | 250 ms | 150–400 ms | rotation leaves the page FREE → raise | ICX-SETTLE-7 | R4 |
| `HOLD_MAX` | 10 s | 5–20 s | — (safety only) | ICX-SETTLE-6 | R5 |
| FREE band | `storyTop − 1` … `storyEnd + 1` px | fixed | — | ICX-SETTLE-2 | R2 |
| No-op threshold | `abs(scrollY − y) ≤ 0.5` px | fixed | — | ICX-SETTLE-1 | R1 |

`BEAT_PX` is not a tunable: it is measured, `round(100svh − header)` in integer CSS px (ICX-SETTLE-7).

## Fixed by the contract (reference only; change = contract change)

| Value | Row |
|---|---|
| Back step fade 220 ms | ICX-BACK.1 |
| Dip 220 ms total; cooldown 600 ms | ICX-DIP.1, .4 |
| Remaining time after a gesture during a transition ≤ 0.6 s; reversal ≥ 1.5× | ICX-SIGNED.5 |
| Idle allowance before the rest invariant: transition + content + 1 s | ICX-REST.1 |
| Transition ≤ 1.5 s; Make→Look ≤ 1.6 s; the Ride ≈ 1.45 s; caption ≤ 0.7 s — DEFAULT (DEC-8), pending Daniel | ICX-STEP.2, .3 |
| Content run ≤ 5 s where feasible; typing ≥ 90 ms/char — DEFAULT (DEC-6), pending Daniel | ICX-STEP.4, .5 |
| Mode breakpoints: desktop ≥ 1024 px, tablet 640–1023 px, phone < 640 px | ICX-DEST |
