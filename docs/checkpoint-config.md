# Checkpoint input config — version 1

Status: version 1, part of ICX v1 (`docs/interaction-contract.md`) — DECIDED 2026-10-15 by main under Daniel's
delegation (decisions-2026-10-15.md in the run dir); not yet implemented.

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
- **"PICKED by C0b per PLAN (not from R1); tune in C7"** marks the only two ranges C0b chose (`REVERSE_PX`,
  `KEY_REPEAT_MS`), because PLAN § C0b tells it to. Every other range R1 leaves open stays "unset (R1)".
- Numbers fixed by the contract (220 ms dip, 600 ms cooldown, 0.6 s rush cap, 1.5× reversal, the 3× rate ceiling,
  the 40 % scroll-spy line, the DEC-8 dead-time ceilings) are listed at the end and are not tunable here.

## Detector: wheel (R1 §3.4)

| Constant | Value | Range | Turn it when… | Source |
|---|---|---|---|---|
| `LINE_PX` | 33.3 px per line | fixed | — (normalises `deltaMode` 1) | R1 §3.4 |
| `MIN_DELTA` | 0.5 px | 0–2 px | resting fingers on a Windows precision touchpad step by themselves → raise | R1 §3.4 |
| `START_PX` | 8 px | 4–20 px | brushing the trackpad steps → raise; a deliberate small scroll is ignored → lower | R1 §3.4 |
| `START_WIN` | 120 ms | unset (R1) | (paired with `START_PX`) | R1 §3.4 |
| `QUIET_SMOOTH` | 140 ms | 100–250 ms | — (ends slow drags; a moving inertia tail CAN show gaps when the page or browser holds input back, measured by FLICKER 2026-10-16: those are joined by ICX-CLASS.4, not ended here) | R1 §3.4; ICX-CLASS |
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
| `TAIL_LIVE` | 20 px/s (ICX-CLASS.4) | 10–60 px/s | a stalled late tail still adds a step → lower; a slow drag right after a flick's natural end is swallowed → raise | FLICKER stall matrix (60 left 1/26 residue at s0 1300–1400 ms; 20 none on the C1 tails) |
| `JOIN_MAX` | 600 ms (ICX-CLASS.4) | 300–1000 ms | a long page stall still splits a flick → raise; a second gesture soon after a moving tail is swallowed → lower | FLICKER: stalls 150–500 ms joined; > `JOIN_MAX` is a new gesture |
| `SPREAD_MIN` | 24 ms (ICX-CLASS.5) | 17–45 ms | a coalesced burst still reads as a rise → lower; a 60 Hz stream's rates look smeared → raise | FLICKER: above one 60 Hz frame plus jitter; 120 Hz 40–45 ms stalls 2–4/26 → 0/26 |
| `BUNCH_MS` | 4 ms (ICX-CLASS.5) | 2–8 ms | held-back events delivered in a burst still read as a rise → raise | FLICKER: below any device's frame interval (8 ms at 120 Hz) |
| `REVERSE_PX` | 12 px summed within 80 ms | 8–20 px (window fixed at 80 ms) — **PICKED by C0b per PLAN (not from R1); tune in C7** | a deliberate reversal during a tail is missed → lower; trackpad jitter reverses a step → raise | value: R1 §3.4 (and C0a ran it); range: PICKED by C0b per PLAN § C0b, R1 leaves it unset |
| Notch hint: first delta | ≥ 50 px with no event in the previous 30 ms | unset (R1) | smooth flicks get the notch hint too often → raise (D1 already guards the repeat) | R1 §3.4 normalisation; C0a D1 |

## Keyboard (R1 §3.4)

| Constant | Value | Range | Turn it when… | Source |
|---|---|---|---|---|
| `KEY_REPEAT_MS` | 420 ms | 300–600 ms — **PICKED by C0b per PLAN (not from R1); tune in C7** | a held arrow or PageDown travels too fast to read → raise; it feels sluggish → lower | value: R1 §3.4 (and C0a ran it); range: PICKED by C0b per PLAN § C0b, R1 leaves it unset; ICX-KEY.4 |

## Touch (R1 §3.4)

| Constant | Value | Range | Turn it when… | Source |
|---|---|---|---|---|
| `TOUCH_SLOP` | 8 px | unset (R1) | — | R1 §3.4 |
| `DIR_RATIO` | 1.2 | unset (R1) | — | R1 §3.4 |
| `SWIPE_PX` | max(36 px, 5 % of the pin height) | unset (R1) | — | R1 §3.4 |
| `SWIPE_VEL` | 0.4 px/ms (at `touchend`, with `abs(dy)` ≥ 14 px) | unset (R1) | — | R1 §3.4 |
| Pinch-zoom pan threshold | `visualViewport.scale > 1.01` | unset (C0a) | — | C0a S9; ICX-SETTLE-9 |

## Story playhead (R1 §3.4 "story" rows)

R1's values, bounded by the decided contract (decisions-2026-10-15.md §B #13, §C). Where the contract fixes a bound,
the bound is the range ceiling and the contract wins.

| Constant | Value | Range | Turn it when… | Source |
|---|---|---|---|---|
| `RATE_MAX` | 3× | fixed (contract) | — (Daniel's ceiling: nothing plays faster, anywhere) | decisions §C; ICX-SIGNED.7 |
| `RUSH` | 2.5× | unset (R1); never above `RATE_MAX` | — | R1 §3.4; ICX-SIGNED.5 |
| `RUSH_MAX` | 0.6 s, acceleration-aware: a rush only if `T_3(R) ≤ 0.6 s`, the rest `R` played with the rate ramp from the current rate up to ≤ `RATE_MAX` at `RATE_ACCEL` (formula in ICX-SIGNED.5; at 1× and 12 /s², `R ≤ 1.633 s`; a reversal from 1.5×, `R ≤ 1.706 s`) | fixed (contract) | — | decisions §C + main's ruling 2026-10-15 (R1 started at 0.35 s at `RUSH`; superseded); ICX-SIGNED.5, ICX-BACK.3 |
| `CONTENT_FINISH_MAX` (R1's `CONTENT_RUSH_MAX`) | 0.6 s of content left → it finishes at **1×** (never rushed); more → the 220 ms skip dip | fixed (contract) | — | decisions #13; ICX-STEP.7 |
| `DIP` | 100 ms out + 120 ms in | the total is fixed at 220 ms (ICX-DIP); the split is unset (R1) | — | R1 §3.3/§3.4 |
| `ABORT_RATE` | 1.5× | fixed as the floor; never above `RATE_MAX` (ICX-BACK.3, ICX-SIGNED.5) | — | R1 §3.4 |
| `RATE_ACCEL` (R1's "rate easing") | 12 /s² | unset (R1) | — (a change moves the rush cut-off: ICX-SIGNED.5 recomputes it, never approximates) | R1 §3.2/§3.4; ICX-SIGNED.5 |

## Nav (decided)

| Constant | Value | Range | Turn it when… | Source |
|---|---|---|---|---|
| `SPY_LINE` | 40 % of the viewport height: a native section is current once its top has crossed this line | fixed (contract) | — | decisions §C (was OPEN-17); ICX-HL.4 |

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
| Remaining time after a `dest`-changing gesture during a transition ≤ 0.6 s, computed with the rate ramp (≤ 3× at `RATE_ACCEL`), else the 220 ms dip; reversal from 1.5×, same formula | ICX-SIGNED.5, ICX-BACK.3 |
| Rate ceiling 3× (`RATE_MAX`) everywhere | ICX-SIGNED.7 |
| Scroll-spy line 40 % of the viewport height (`SPY_LINE`) | ICX-HL.4 |
| Idle allowance before the rest invariant: transition + content + 1 s of visible time | ICX-REST.1 |
| **DEC-8 dead-time rule** — DECIDED (DEC-8, 2026-10-15): the ceilings apply to dead time only, never to motion speed. Moving parts keep the base 9471605's durations and easing; holds, waits and pauses are trimmed until each transition ≤ 1.5 s; named exceptions (expected: Make→Look) are judged on frame strips; the Ride 1.45 s ± 0.1 s; caption ≤ 0.7 s for every step (named caption-exception list empty in v1) | ICX-STEP.2, .3 |
| Content run ≤ 5 s where feasible (pauses cut, same dead-time rule); typing ≥ 90 ms/char — DECIDED (DEC-6, 2026-10-15) | ICX-STEP.4, .5 |
| Mode breakpoints: desktop ≥ 1024 px, tablet 640–1023 px, phone < 640 px | ICX-DEST |
