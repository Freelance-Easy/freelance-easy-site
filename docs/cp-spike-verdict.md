# C0a: sticky-track feasibility spike, verdict

Run `2026-10-14-site-ux`, piece C0a (R2), branch `ux/c0a-spike` off 652d12a. Built and run 2026-10-14/15 on the Mac.
The spike is `scratch/cp-spike/` (never deployed). It implements R1 §3.2's "A2" model in isolation, not in `site.js`:
- a sticky pin over a short native track (one pin height per beat, 9 beats);
- JS-owned wheel, key and touch input (R1 §3.4 detector);
- story time decoupled from `scrollY`;
- FREE + settle for scroll sources we cannot intercept;
- RELEASED native scroll after the last beat.

## Go / no-go

**GO WITH WORKAROUNDS for C3's sticky-track model.** In the final full run (2026-10-15, 127 probes on the final code
801bae3, none needing its automatic retry: 64 PASS · 52 WORKAROUND · 11 FAIL, where all 11 FAILs are the intentional
failure-mode variants — 9 × R6 `-nograce` (what breaks without S3) and 2 × S1 `-r1notch` (what breaks without D1) —
which never count toward a cell) every row passes or passes with a workaround on all three
Playwright proxies once the settle rules S1–S9 below are in place. One cell is **intermittent**: Chromium 1440×900 R3
(settle cancellation) failed on both attempts in the earlier post-Sol rerun and passed in the final run (footnote 3) —
C3 must treat it as a real race, not a pass. No proxy result argues against the model. The workarounds are local
rules in the input/settle layer, not changes to the model.

**What a late device no-go would change** (the M1 gate's device session):
- **Detector feel** (trackpad inertia, Magic Mouse, Windows notches): constants only (C7 tuning). The model stands.
- **Settle feel** (Safari's overlay scrollbar, Windows autoscroll): S3/S6 timing only. Worst case, overlay-scrollbar
  platforms drop the snap and stay FREE until the next gesture. That is local to C3's settle code.
- **iPhone momentum from below or the address bar** (R8): this is the one that reshapes C3. The phone row of the
  destination table would go native for more beats, or for the whole story (ICX-RELEASE widens), and C6's touch
  adapter shrinks. Desktop and tablet would be unaffected.

## Verdict table

Cells: **PASS** = works with R1's design as written. **WORKAROUND** = works only with a C0a rule (S1–S9) that R1
does not have, or only partly provable on the proxy (the cell says which). **FAIL** = broken.
**UNVERIFIED-DEVICE** = needs a real device that was not available. The device session moved to after the merge
(Daniel, 2026-10-14). The Mac Safari column is UNVERIFIED-DEVICE because Safari's "Allow Remote Automation" is off
(`defaults read com.apple.Safari AllowRemoteAutomation`: the key does not exist). `safaridriver --enable` needs
Daniel's password, so it was not run.

Proxies:
- **Chromium** = Playwright Chromium 1243 (stands in for Mac Chrome), 1440×900 and 1280×720 at DPR 2, plus
  360×640 Android (isMobile, hasTouch, DPR 3).
- **WebKit** = Playwright WebKit 2359 (stands in for Mac Safari), 1440×900 and 1280×720.
- **WebKit iPhone** = WebKit with the iPhone 14 profile (isMobile, hasTouch, `pointer: coarse` true) at the real
  viewports 390×664, 375×548, 360×640 and 844×390.

R9's step-and-settle probe (`r9_browser_zoom`) also ran at simulated browser zoom 125 % and 175 %. Settle, hold
and rotation at those zoom levels were not probed. Evidence lives in
`scratch/cp-spike/evidence/<column>/<row>__<WxH>[-variant].json`: checks, measured data and the page's event log.
The matrix is in `evidence/summary.json` / `summary.md`.

| Row | Playwright Chromium | Playwright WebKit | WebKit iPhone-emulation | Mac Safari (real) | Windows Chrome/Edge (real) | iPhone Safari (real) | What a human must feel at the M1 gate |
|---|---|---|---|---|---|---|---|
| R1 programmatic-scroll acknowledgement | PASS | PASS | PASS | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | Mac trackpad (Safari + Chrome), Magic Mouse, Windows notch: a step never shows a jump or a one-frame flash of the pinned stage. iPhone: the same with a swipe. |
| R2 FREE/RELEASED boundaries | PASS ¹ | PASS ² | PASS | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | Trackpad flick at the end card: it scrolls out with its own inertia. Scrolling back up: a soft stop on the end card, never a wall or a bounce into beat 7. Windows notch at the last beat: releases one notch. iPhone: swipe out, then fling back. |
| R3 settle cancellation | PASS, **intermittent** ³ | PASS | PASS | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | Drag the scrollbar, then wheel or press a key at once: one move, no double jump. |
| R4 resize/rotation | WORKAROUND (S7) ⁴ | WORKAROUND (S7) | WORKAROUND (S7) | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | Rotate the iPhone on a beat, and again below the story. Resize the Mac window mid-transition. Snap a Windows window to half the screen. |
| R5 scrollbar hold | WORKAROUND ⁵ | WORKAROUND ⁵ | WORKAROUND ⁵ | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | Windows classic scrollbar: drag and hold still, and the page waits; release, and one transition plays. Mac Safari overlay scrollbar: drag, then hold still for more than 0.2 s. Does it snap mid-hold? |
| R6 autoscroll | WORKAROUND (S3) | WORKAROUND (S3) | WORKAROUND (S3) | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | Windows middle-click autoscroll through the story: the stage holds its frame, and one transition plays when it stops. Mac has no autoscroll. |
| R7 Safari without `scrollend` | WORKAROUND ⁶ | WORKAROUND ⁶ | WORKAROUND ⁶ | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | Real Safari: run `'onscrollend' in window` in the console. Scrollbar drags and find-in-page then settle cleanly about 0.17 s after they stop. |
| R8 iOS momentum + address bar | WORKAROUND (S4) ⁷ | WORKAROUND (S4) | WORKAROUND (S4) | n/a | n/a | UNVERIFIED-DEVICE | Real iPhone: a momentum fling from below lands on the end card with no visible fight. The address bar collapsing or expanding mid-story keeps the beat. A real finger swipe = one step. Pull-to-refresh at beat 0 still works. Landscape. |
| R9 zoom | PASS | PASS | WORKAROUND ⁸ (partial) | UNVERIFIED-DEVICE (zoom-sensitive) | UNVERIFIED-DEVICE | UNVERIFIED-DEVICE | Safari and Chrome ⌘+/− at 110–175 %, then step: beats stay aligned. A trackpad pinch (a ctrl+wheel) never steps. Shipping Safari's unzoomed `getBoundingClientRect` (the `vrect` trap) does not reproduce in Playwright WebKit (`legacyZoom()` → `legacy: false` on all three proxies). The spike measures only with offsets and `scrollY`. iPhone: pinch-zoom, then a swipe pans. |

Counts over R1–R9 (final run, 2026-10-15; evidence files regenerated on 801bae3, summary in `evidence/summary.md`):
- Playwright Chromium: 4 PASS (R3 intermittent, footnote 3) · 5 WORKAROUND · 0 FAIL.
- Playwright WebKit: 4 PASS · 5 WORKAROUND · 0 FAIL.
- WebKit iPhone-emulation: 3 PASS · 6 WORKAROUND · 0 FAIL.
- All three real-device columns: UNVERIFIED-DEVICE.
- Final-run command: `uv run --with playwright==1.63.0 python3 scratch/cp-spike/run_probes.py` (≈18 min); no probe needed
  its automatic retry (no evidence file carries `first_attempt_failed`). Run totals: 64 PASS · 52 WORKAROUND ·
  11 FAIL, the 11 being the intentional `-nograce` / `-r1notch` variants only.

The `-nograce` and `-r1notch` variants record failure modes on purpose (S3, D1) and do not count toward the cells.

Footnotes:
1. 360×640 Android (CDP touch): trusted touch drags stepped once inside the story and scrolled natively at the last
   beat.
2. WebKit 1440×900 R2 failed on its first attempt and passed on the automatic rerun. Host jitter can split a
   synthetic flick past `QUIET_SMOOTH`. The final full run (2026-10-15) passed it on the first attempt, so the
   regenerated evidence file no longer carries `first_attempt_failed`.
3. Chromium 1440×900 R3 **FAILED on both attempts** in the post-Sol rerun (`run-solfix.log`,
   `evidence/chromium/R3__1440x900.json`): FREE was not yet entered 40 ms after a foreign `scrollTo`, so the key
   step ran outside FREE. This is undiagnosed: probe timing or the FREE-freeze change. Every other R3 run passed,
   and the final full run (2026-10-15) passed it on the first attempt — so it is **intermittent**, not fixed.
   **Open item for C3:** prove FREE is entered synchronously on a foreign `scrollTo` (or within one frame) under load;
   a 40 ms window that sometimes misses is a real race on slow machines.
4. Chromium 360×640 Android (isMobile): the first runs FAILed because a reader below the story could not keep
   their old distance below `storyEnd` after the rotation: the document end clamps it (699 → 621 px). After Sol
   C0a-1 the check expects min(old distance, the new room below the story), and it passes (`run-solfix.log`).
5. Mac proxies have overlay scrollbars (0 px), so the hold is invisible to S6 there. Real thumb drags on a classic
   15 px bar (`-classicbar`) PASS on Chromium and WebKit: `mousedown` and `mouseup` both reached the page, there was
   no settle during a 1 s still hold, and exactly one settle came on release. An undetected still hold settles after
   about 1 s.
6. The idle fallback was forced with `?noscrollend`, because all three proxies have `onscrollend`. Measured: one
   settle about 168 ms after the last scroll.
7. Logic only: touch is synthetic (CDP on Chromium) and momentum is a `scrollBy` stream.
8. iPhone: only the zoom-emulation and CSS-zoom parts ran. There is no Ctrl+wheel, and pinch is not drivable.

## Settle rules: the ICX patch for C0b

Add these under the ICX table as **ICX-SETTLE** (S1–S9) and put the constants into `docs/checkpoint-config.md`
version 1. All values are what the spike ran with. Ranges are where C7 may tune them.

| Rule | Statement |
|---|---|
| **S1 Acknowledge by position** | `syncScroll(y)` rounds `y` to an integer and clamps it to the scroll range. If `abs(scrollY − y) ≤ 0.5` it does nothing (no scroll event will come, so it arms nothing). Otherwise it stores `pending = {y, until: now + ACK_MS}` and calls `scrollTo({top: y, behavior: "instant"})`. A `scroll` event with `abs(scrollY − pending.y) ≤ ACK_TOL` before `until` is ours. Never use a boolean "next event is ours" flag. Measured on all three proxies: `scrollTo` applies synchronously, and each call gives exactly one `scroll` and one `scrollend` (R1). |
| **S2 FREE** | Any other `scroll` event with `storyTop − 1 ≤ scrollY ≤ storyEnd + 1` enters FREE. The stage keeps its frame, and the rail previews `nearest = round((scrollY − storyTop) / BEAT_PX)`. Below `storyEnd + 1` it is RELEASED; above `storyTop − 1` it is the page above. |
| **S3 Settle trigger** | Where `onscrollend` exists: settle `SCROLLEND_GRACE` after a `scrollend`, and only if no `scroll` event came in that time. Without the grace, the settle fires mid-stream: Chromium and WebKit fire a `scrollend` after **every** programmatic or instant scroll, 59 of them during one 1 s autoscroll stand-in, which gave 30 settles (`R6__*-nograce.json`). Without `scrollend`: settle after `SETTLE_IDLE` of no scroll events (measured latency ≈ 167 ms, R7). Always: a `SETTLE_BACKSTOP` timer re-armed on every scroll event. |
| **S4 Settle target** | The nearest beat, as a jump (ICX-JUMP: ±1 = a step, otherwise a dip). The settle's own scroll is acknowledged (S1), so it never re-enters FREE. **Re-entry from below:** a FREE episode that began in RELEASED settles on the **last** beat unless a scrollbar hold was seen in it. This covers iOS momentum, PageUp, find and restoration. After such a settle, a new FREE episode within `REENTRY_STICKY_MS` still counts as re-entry. On 844×390 a frame gap mid-momentum let the settle fire, and the rest of the stream walked the story back to beat 7 until this rule was added (R8). |
| **S5 Settle cancellation** | An intercepted gesture (wheel, key or touch) during FREE cancels the pending settle. It counts from the beat nearest the current `scrollY`, not from the stage's frame. A further foreign scroll restarts the timers. If the settle wins the race instead (it fires 50 ms after a `scrollend`), the outcome is the same beat (R3 records which path ran). |
| **S6 Scrollbar hold** | A capture-phase `mousedown` on `document` with `clientX ≥ documentElement.clientWidth` (or `clientY ≥ clientHeight`) means held: the settle waits. The hold ends on `mouseup`/`pointerup`, on a `mousemove` with `buttons === 0`, on window `blur`, or after `HOLD_MAX`. Real thumb drags on a non-overlay scrollbar delivered both `mousedown` and `mouseup` on Chromium and WebKit (`R5__*-classicbar.json`). **Overlay scrollbars** (the macOS default, iOS) are invisible to this test. There the settle relies on S3: Chromium fires `scrollend` at release (per the spec; not provable headless), and WebKit's idle path can snap a thumb that is held still for 150 ms. WebKit fires synthetic `mousemove`s after every scroll, carrying the real `buttons` state. |
| **S7 Resize / rotation** | On every `resize`, re-measure at once (no debounce for the re-snap). `BEAT_PX = round(100svh − header)` in integer CSS px, and the pin height is set to the same integer. Inside the story: `syncScroll(y_dest)`. RELEASED: keep the distance below `storyEnd`, computed from the **last scroll position seen at the old viewport size**: WebKit moves `scrollY` on rotation before `resize` fires (the first 844×390 run kept 209 px instead of 395). Browser scroll corrections within `RESIZE_GRACE` after a real geometry change are re-snapped, never FREE. Page boot is not a geometry change. Set `overflow-anchor: none` on `html` and `body`. A height-only change where 100svh did not move (iOS bars) is a no-op. Measure with offsets and `scrollY` only, never `getBoundingClientRect` (the Safari CSS-zoom trap). |
| **S8 Release / re-entry** | R1 §3.2 as written, with a sticky decision per gesture. At REST(last), a forward wheel, key or swipe is not intercepted. Wheel from below: events pass while `scrollY + dy ≥ storyEnd`. The event that would cross is prevented, `syncScroll(storyEnd)` lands REST(last), and the rest of that gesture is swallowed. Keys from below pass natively (then S2/S4). Home and End always jump. |
| **S9 Bypass** | Ctrl+wheel is never prevented: in headless Chromium it scrolled natively, then FREE and settle. A touch while `visualViewport.scale > 1.01` (pinch-zoomed) pans and never steps. A second finger ends the touch with no step. |
| **D1 Detector note (for C0b/C1)** | R1 §3.4 counts a notch gesture as "sustained" by any event. A smooth flick whose first delta is ≥ 50 px gets the notch hint and keeps it for the whole gesture (ICX-CLASS), so a decaying tail longer than `REPEAT_MS` stepped twice (WebKit R2, first run). Fix: notch gestures also need `vNow ≥ SUSTAIN_K · peakSinceStep` to repeat. `S1__*-r1notch.json` runs R1's rule for comparison. |

| Constant | Value | Range | Turn it when… |
|---|---|---|---|
| `ACK_TOL` | 1.5 px | 1–2 | fractional DPR / browser zoom gives acknowledgement misses (none at 125 %/175 %) |
| `ACK_MS` | 400 ms | 250–600 | a slow device delivers the scroll event late |
| `SCROLLEND_GRACE` | 50 ms | 30–100 | autoscroll or find streams settle mid-way → raise |
| `SETTLE_IDLE` | 150 ms | 120–250 | Safari scrollbar holds snap mid-drag → raise; the settle feels late → lower |
| `SETTLE_BACKSTOP` | 700 ms | 500–1500 | a held overlay thumb snaps on Chrome → raise |
| `REENTRY_STICKY_MS` | 800 ms | 500–1200 | iPhone momentum from below still walks back → raise |
| `RESIZE_GRACE` | 250 ms | 150–400 | rotation leaves the page FREE → raise |
| `HOLD_MAX` | 10 s | 5–20 s | — (safety only) |
| `SUSTAIN_K` (now for notch gestures too) | 0.7 | 0.5–0.9 | a long notch spin stops repeating → lower |

R1's other detector constants ran unchanged: `QUIET_SMOOTH` 140, `QUIET_NOTCH` 220, `START_PX` 8, `CONT_GAP` 45,
`RISE_RATIO` 1.8, `V_RISE_MIN` 1000, `MIN_STEP_MS` 250, `REPEAT_MS` 850, `REVERSE_PX` 12 / 80 ms, `KEY_REPEAT_MS` 420,
`SWIPE_PX` max(36, 5 % of the pin), `SWIPE_VEL` 0.4, `TOUCH_SLOP` 8, `DIR_RATIO` 1.2.

## What was synthesised

Nothing here is a real device. The inputs were:
- **Wheel:** Playwright `mouse.wheel`. These are trusted events with hand-made decaying inertia tails, single
  100 px "notches" and bursts. There is no real trackpad, Magic Mouse or notched wheel.
- **Keyboard:** `keyboard.press`.
- **Scrollbar:** real mouse drags on a CSS-styled non-overlay scrollbar (`?classicbar`). The overlay case used a
  real button down plus a dispatched `mousedown` at `clientX = clientWidth`.
- **Touch:** Chromium used CDP `Input.dispatchTouchEvent`. These are trusted, and native scroll happened on release.
  WebKit used JS-dispatched touch-shaped events: untrusted, logic only, with no native scroll and no momentum. Mobile
  WebKit has no `mouse.wheel`, so its gestures are synthetic swipes, and the native scroll after a passed swipe was
  stood in by a `window.scrollBy` stream.
- **Autoscroll, find, iOS momentum:** `window.scrollBy` streams once per frame.
- **Rotation and the iOS bars:** `set_viewport_size`. In emulation 100svh follows the viewport, so the "bars" case
  re-lays out, unlike a real iPhone.
- **Browser zoom:** contexts with the CSS viewport divided by 1.25/1.75 and the DPR multiplied by the same factor.
- **Pinch:** CDP `Emulation.setPageScaleFactor(2)` on Chromium. It is not drivable on WebKit.

## Run it

- Look at the spike by hand: `python3 -m http.server 8802 --bind 127.0.0.1 --directory /Users/danielpaskert/work/site-c0a`,
  then open `http://127.0.0.1:8802/scratch/cp-spike/index.html`. Query options are in the `spike.js` header,
  e.g. `?noscrollend`, `?classicbar`, `?csszoom=1.25`, `#b4`.
- All probes, about 18 min; the runner serves 127.0.0.1:8802 itself if the port is free:
  `uv run --with playwright==1.63.0 python3 /Users/danielpaskert/work/site-c0a/scratch/cp-spike/run_probes.py`.
  Slices: `--col chromium|webkit|webkit-iphone`, `--row R1 … R9|S1`. A slice merges into `summary.json`.
  Pin 1.63.0: it matches the installed chromium-1243 / webkit-2359. 1.64 wants webkit-2370.
- Digest the evidence into the numbers above: `python3 /Users/danielpaskert/work/site-c0a/scratch/cp-spike/digest.py`.

## Notes for C3 / C0b

- Playwright WebKit 2359 **has** `onscrollend`, so the Safari path was forced with `?noscrollend`. Whether shipping
  Safari 26.4 has it is UNVERIFIED-DEVICE. C3 must feature-detect and carry both paths.
- `scratch/` is not in `.assetsignore` yet (CF-15, B1 owns it). Until B1 lands, a deploy would publish
  `scratch/cp-spike/`.
