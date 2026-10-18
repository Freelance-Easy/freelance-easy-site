# Interaction contract (ICX v1)

Status: v1 — DECIDED 2026-10-15 by main under Daniel's delegation (decisions-2026-10-15.md in the run dir); not yet implemented

Decisions: `.orchestrate/2026-10-14-site-ux/decisions-2026-10-15.md` (§A DEC answers, §B the scroll rulebook #12–#26,
§C technical). Cited below as "decisions #n" or "decisions §C".

- **Binding.** Every piece that moves people between checkpoints (story, rail, menu, tour, deep links)
  implements this file. Later DONE WHENs cite a row id (e.g. `ICX-DIP.2`). C3 owns the destination table's
  implementation; C1, C4, B5, B6 and K1 consume it.
- **Source of truth:** vault "Site UX Consolidation — Build Plan (2026-10-14)" §3 (the ICX table and the destination
  table) and §2 DEC-4/6/7/8. It supersedes R1, R2 and R3 where they differ (jumps, back steps, history, fills).
- **Settle rules:** ICX-SETTLE-1…9 and ICX-SETTLE-D1 come from C0a's verdict (`docs/cp-spike-verdict.md`,
  "Settle rules: the ICX patch for C0b"). Each cites its evidence row.
- **Constants:** every number a test needs that is tunable lives in `docs/checkpoint-config.md` (version 1). Numbers
  written here (220 ms, 600 ms, 0.6 s, 1.5×, 3×, 40 %, the DEC-8 dead-time ceilings) are contract values: changing one
  is a contract change.
- **Decided:** each spot marked "DECIDED (DEC-n, 2026-10-15)" is a DEC answer; each rule that was an open question in
  the draft cites its decisions number and "(was OPEN-n)". No question is left open (see "Decision status"); two C3
  build tasks remain
  ("Build tasks for C3").
- **Global rate ceiling (ICX-SIGNED.7):** nothing on the story or tour stage ever plays faster than 3× (decisions §C,
  Daniel's ceiling). Every rate below is bounded by it.

## Terms

| Term | Meaning |
|---|---|
| checkpoint | A rest frame: a story destination whose `kind` is `pinned` in the current mode, or a tour chapter (ICX-CHECKPOINT) |
| native section | A destination whose `kind` is `native` in the current mode: plain document scroll, no interception |
| `dest` | The signed destination: the checkpoint the input so far asks for |
| landing | The moment the move into a checkpoint is complete and only its own content (if any) is left: for a step, the end of its seam; for a dip or a back-fade, the cut (the dark frame); for a reversed seam, its arrival on the origin's rest frame. Every landing is either a pass-through landing or a final landing (below). `rendered`, `distance`, `onLand` and `aria-current` (ICX-HL.2) change at every landing. Read from the vault's dip row ("input … after the cut counts as a new step from the new `rendered`") |
| pass-through landing | A landing with `rendered ≠ dest` after it (queued steps: e.g. a rushed seam lands `o + 1` while `dest = o + 3`). `rendered` advances, `aria-current` moves, `onLand` fires marked as a pass-through. The checkpoint's content does not play, nothing rests, `aria-live` does not announce, and **no history is written**. "Checkpoints passed through" (vault) are exactly these, plus the ones a dip cuts past (never landed at all) |
| final landing | A landing with `rendered == dest` after it. Only a final landing plays the checkpoint's content, leads to rest, announces through `aria-live` (ICX-KEY.2) and writes history (ICX-HIST.1/.2) |
| `rendered` | The last checkpoint fully landed (see landing). A checkpoint playing its content is landed, so `distance` during content counts from it |
| `distance` | `abs(dest − rendered)` |
| `phase` | The engine state; `"rest"` means resting on a checkpoint with nothing playing |
| transition | The seam from one checkpoint toward the next (ends where the next checkpoint's content starts) |
| content | The checkpoint's own autoplay, from the end of its transition to its rest frame |
| dip | The 220 ms fade out → cut → fade in (ICX-DIP). Used by ICX-DIP (distance ≥ 2), ICX-BACK (the back-fade) and ICX-SIGNED.5 (a transition that cannot finish within 0.6 s at ≤ 3×) |
| rest-entry | A checkpoint's content start (the end of its seam; R1 §3.3 `S_b`). A dip that lands on a checkpoint's rest-entry then plays its content (decisions §C) (was OPEN-7) |
| dead time | Story time during which the rendered stage frame does not change (no moving element): holds, waits and pauses. DEC-8's ceilings trim only dead time (ICX-STEP.2) |
| step | One gesture (wheel gesture, swipe, step key): ±1 |
| jump | An explicit target: rail/menu click, Home/End, logo, deep link, popstate (ICX-JUMP); a FREE settle uses the same visual rule (ICX-SETTLE-4); a jump to a `native` row is a native anchor scroll (ICX-JUMP.5) |
| FREE / RELEASED | C0a states: a foreign scroll inside the track / native scroll below the pinned track (ICX-SETTLE-2) |
| last pinned | The last `pinned` row in the current mode: desktop `end`, tablet `chase`, phone `end` |

## The destination table (ICX-DEST)

Owned by C3; consumed by C4, B5, B6 and K1. One row per destination, in beat order (`BEATS` in `assets/story/site.js`).

Names: DECIDED (DEC-4, 2026-10-15). Slug = the name kebab-cased. No numbers, counters, fills or progress UI
anywhere (ICX-NOPROG).

Anchors (decisions #20): every chapter section in `src/pages/index.html` gets `id` = its slug, so `/#<slug>` works
with no JS. The legacy hashes keep tiny anchors of their own so old links work with no JS; with JS they land on their
chapter and the URL is replaced by the slug (ICX-HIST.6). Today's ids `how`, `pricing`, `download` sit on the
sections; they move to those legacy anchors. `#top` stays `main#top`.

| beat id | name (rail label, caption eyebrow) | slug (URL hash) | anchor (section `id`) | legacy anchor | rest (story time of the rest frame) | desktop ≥1024 | tablet 640–1023 | phone <640 | classic / calm / static / no-JS |
|---|---|---|---|---|---|---|---|---|---|
| `make` | New invoice | `new-invoice` (the story writes plain `/`, ICX-HIST.5) | `new-invoice` | `#top` (`main#top`) | `TL.HOLD` (desktop dark ≈ 3.60 s) | pinned | pinned | pinned | native |
| `look` | Templates | `templates` | `templates` | `#how` | segment end − 0.02 (≈ 11.11 s) | pinned | pinned | pinned | native |
| `know` | Invoices | `invoices` | `invoices` | — | segment end − 0.02 (≈ 15.06 s) | pinned | pinned | pinned | native |
| `grow` | Dashboard | `dashboard` | `dashboard` | — | segment end − 0.02 (≈ 17.44 s) | pinned | pinned | pinned | native |
| `chase` | Email | `email` | `email` | — | segment end − 0.02 (≈ 24.94 s) | pinned | pinned (last pinned) | pinned | native |
| `yours` | Your data | `your-data` | `your-data` | — | `yours` segment start + 0.28 (≈ 26.14 s) | pinned | native | pinned | native |
| `price` | Price | `price` | `price` | `#pricing` | `price` segment start + 0.3 (≈ 28.01 s) | pinned | native | native | native |
| `note` | A note | `a-note` | `a-note` | — | `brand` segment start + 0.2 (≈ 29.81 s) | pinned | native | native | native |
| `end` | Get the app | `get-the-app` | `get-the-app` | `#download` | desktop: `brand` segment end − 0.05 (≈ 30.56 s); phone: `TL.T1 − END_REST` | pinned (last pinned) | native | pinned (last pinned) | native |

- **Phone order (decisions #21): as shipped 10-10.** The story is pinned through Your data → the Get the app card
  (`end`, the last pinned; site.js `TALL_PIN`); Price and A note follow as native sections after the release. With JS,
  `/#get-the-app` on a phone targets the pinned card. Revisit only in the M1 device session.
- **Short touch screens (decisions #22): calm automatically, as today** (coarse pointer and 100svh < 600 px, site.js
  `SHORT_TOUCH`): every row native, as in the last column.

- **rest:** the expression is today's hold `T` in `site.js` (`holds`, ~:680-692), which R1 §3.2 turns into
  `REST_T[beat]`. The seconds are R1 §2.6's computed desktop dark-theme values, not re-measured here. Light theme: every
  value after the first is 0.91 s earlier (R1 §2.6). Phone and tablet build their own timeline, so their values differ.
  `rest` applies only where the row is `pinned`.
- **Mode counts:** desktop 9 pinned; tablet 5 pinned (make…chase), 4 native; phone 7 pinned (make…chase, yours, end),
  2 native (price, note); classic / calm / static / no-JS 0 pinned, 9 native.
- The vault's mode breakpoints are the ones `site.js` uses today: `desktop()` = width ≥ 1024, `preset()` = "tall"
  below 640. Calm also covers a short touch screen (above).

Assertions:
- **ICX-DEST.1** At a desktop, a tablet and a phone viewport, and with classic effectively on or no JS, the engine's
  list of pinned destinations equals the table's pinned set for that mode, in beat order. Classic is judged by its
  **effective** state (ICX-CLASSIC.8): reduced motion means classic (all native) unless the stored `fe-classic` choice
  turned the story on, in which case the viewport's pinned set applies; a short touch screen is always calm
  (ICX-DEST.6).
- **ICX-DEST.2** Each slug equals the kebab-case of its name; the nine slugs are unique; no slug contains a digit.
- **ICX-DEST.3** Rail, menu and caption eyebrows show exactly the table's names (fe:claims checks the words).
- **ICX-DEST.5** `src/pages/index.html` has one element per row with `id` = the slug, and one element each with `id`
  `how`, `pricing`, `download` inside (or at the start of) the `look`, `price` and `end` sections; with JS off, loading
  `/#<slug>` or a legacy hash scrolls to that chapter.
- **ICX-DEST.6** A short touch screen (coarse pointer, 100svh < 600 px) gets the calm layout on load, as today.
- **ICX-DEST.4** Mode flips (resize or rotation across 640 or 1024, the classic toggle, a reduced-motion change) keep
  the reading place (`readingPlace`/`restorePlace`): the destination in view before the flip is the one in view after,
  and `document.activeElement` is unchanged.

## ICX-SCRUB — phones and touch tablets scrub (DECIDED by Daniel 2026-10-18, PHONE-options option 1)

Rule: a **scrub build** — layout "tall" (< 640 px, any pointer, as the live site) or a touch tablet (640–1023 px with
a coarse pointer; site.js `SCRUB_TABLET`) — runs the live site's scroll scrub (main 652d12a), not the checkpoint
engine. The page scrolls natively; the story time follows the scroll through a map of holds (one per pinned row, at
its `rest`) and eased ramps. Desktop (≥ 1024) and a fine-pointer window 640–1023 keep the checkpoint engine.
ICX-STEP, ICX-BACK, ICX-SIGNED, ICX-DIP, ICX-REST, ICX-RELEASE, ICX-SETTLE and ICX-CLASS apply to the checkpoint
builds only; ICX-DEST, ICX-HL, ICX-KEY.2/.3, ICX-HIDDEN, ICX-CLASSIC, ICX-NOPROG and the 3× ceiling apply to both.

- **ICX-SCRUB.1** No input is intercepted: no `touchmove`, `wheel` or key event is ever prevented (the gesture
  detector is disabled). The pull at the top, iOS momentum and the release into Price / A note are the browser's own.
- **ICX-SCRUB.2** The map: 1.4× the scroll per story-second on phones (48 × 1.4 vh of the stable 100svh), 48 vh on
  tablets; holds (vh, × 1.4 on phones) make 10, look 28, know 26, grow 14, chase 26, yours 26, end 40; each hold
  drifts 0.03 s past its `rest`; ramps ease at both ends.
- **ICX-SCRUB.3** The stage follows the scroll's story time: it eases in and out, never faster than 3× (a seam's own
  CAP is eased into) and never skips forward. Only a one-frame jump (an explicit jump, or a jump back by > 2.5 s) or a
  long rewind (> 8 s back, after the scroll paused 0.12 s) is one 220 ms dip. Scrolling back plays the story backwards.
- **ICX-SCRUB.4** A phone's map equals the live site's (652d12a) within 1 px per piece and 0.001 s per time, both
  themes (`tests/checkpoint/scrub_live_map.json`).
- **ICX-SCRUB.5** History and landings: a **final landing** is the stage caught up with a still scroll inside checkpoint
  `k`'s hold, `k` not the last landed (or an explicit jump's target). "Still" means the scroll position has not moved
  for 150 ms: a slow continuous drag through a hold (where the stage catches up between scroll events) is still moving,
  so it lands nothing until it stops. It sets `dest`/`rendered`, announces through
  `aria-live` (ICX-KEY.2) and fires `onLand(final)`: story-url.js writes one `replaceState` (ICX-HIST.8). Holds crossed
  while the stage moves are `onDest` previews only (no write, no announcement); a stop between holds writes nothing.
  Coming back up from below the story (Price, A note) into a hold is a landing of its own even when that hold was the
  last landed (a re-entry, `onLand({final, reentry})`, ICX-HIST.8): its URL by one `replaceState` unless the URL already
  names it, and one announcement.
  A menu / logo / Home jump scrolls to the hold (`dest` at once, the landing on arrival): one `pushState`
  (ICX-HIST.2); popstate lands the same way with no write (ICX-HIST.3). A menu jump to a native row (Price) is the
  page's own smooth scroll; a rebuild while it runs (a theme switch) asks for the same target again, so it arrives
  (ICX-JUMP.5); the reader's own touch or wheel ends that carry-through.
- **ICX-SCRUB.6** Deep link, reload: a fresh `/#<slug>` to a pinned row lands on its hold (no replay of its content); a
  reload or history visit of the same entry at the same width keeps the reader's pixel; a fresh arrival at the top
  plays Make's arrival to its hold, and the first scroll takes over.
- **ICX-SCRUB.7** `phase`: `rest` when the stage has caught up with the scroll (in a hold or between holds),
  `transition` while it chases, `released` below the story. A rebuild (theme, late fonts, a refit) keeps the same story
  time under the new map; a mode flip keeps the reading place (ICX-DEST.4).
- **ICX-SCRUB.8** The ☰ menu lists the chapters in page order: the pinned story's rows, then the native sections after
  it (phone: … Your data, Get the app, Price, A note).

## The ICX rows

Each row: the rule (from the vault table), then the assertions a test makes.

### ICX-CHECKPOINT — Checkpoint

Rule: a checkpoint is a rest frame: a story page (mode-aware, see ICX-DEST) or a tour chapter.

- **ICX-CHECKPOINT.1** The story's checkpoints are exactly the rows `pinned` in the current mode (ICX-DEST.1). A
  `native` row is never a checkpoint: no input is intercepted on it.
- **ICX-CHECKPOINT.2** When `phase == "rest"` on checkpoint `b`: `rendered == dest == b`, the story time equals `b`'s
  `rest` exactly, `b`'s caption is the active one, and `scrollY` is within 1 px of `b`'s track position.
- **ICX-CHECKPOINT.3** Tour chapters are checkpoints under the same rules. Their names are the story's names where
  the two overlap (decisions #26: one vocabulary site-wide); the tour's own destination table comes with child F.

### ICX-STEP — Step +1 (one gesture)

Rule: play the transition to the next checkpoint at the designed speed. Then the checkpoint's content autoplays and
rests.

Timing — DECIDED (DEC-8, 2026-10-15; decisions #6, #12): the budgets are **ceilings on dead time, never on motion
speed**. The moving part of every seam keeps today's duration and easing (the shipped base, 9471605; the Ride and
the PDF→Look circle untouched). Only holds, waits and pauses (dead time, Terms) are trimmed, until each transition
is ≤ 1.5 s. A seam that cannot reach 1.5 s without speeding up its motion is a **named exception**, judged by Daniel
on frame strips (expected: Make→Look). The Ride stays 1.45 s ± 0.1 s. Caption ≤ 0.7 s after the gesture. C5 shows
before/after as a live A/B switch for Daniel.
Content — DECIDED (DEC-6, 2026-10-15): each automatic content run ≤ 5 s where feasible (trimmed by cutting pauses,
under the same dead-time rule; Email's content is brought to ≤ 5 s this way); typing pace ≥ 90 ms per character.

Named exceptions (transition > 1.5 s allowed; each judged on frame strips, not by a number): Make→Look (expected).
C5 adds a row here only with before/after frame strips showing the seam has no dead time left.

- **ICX-STEP.1** From `REST(b)` with `b` not last pinned, one gesture sets `dest = b + 1`, plays exactly one
  transition, lands `b + 1` at the seam's end (`rendered = b + 1`), plays `b + 1`'s content, and ends in
  `REST(b + 1)`. No dip.
- **ICX-STEP.2** Motion is untouched: in a step with no further input, for every seam and content, each moving segment (a story-time interval in which
  some stage element changes) has the same duration (± one frame) and the same easing as on the base 9471605
  (compared on `__fxTrace` or frame strips). Only dead-time intervals differ. With that: every transition (gesture →
  the end of its seam, at 1×) is ≤ 1.5 s, except a named exception; the Ride is 1.45 s ± 0.1 s.
- **ICX-STEP.3** The incoming caption becomes the active caption ≤ 0.7 s after the gesture event, for every step
  (Make→Look included), except a checkpoint on the named caption-exception list. That list is **empty in v1**; C5 may
  add a checkpoint only with frame strips Daniel has seen (main's ruling, 2026-10-15). The transition named-exception
  list above does not exempt a caption.
- **ICX-STEP.4** Each checkpoint's content run is ≤ 5 s (Email included), except a content run listed as a named
  exception under the same dead-time rule (none expected).
- **ICX-STEP.5** Any typed text in content advances at ≥ 90 ms per character.
- **ICX-STEP.6** The playhead never runs faster than 1× in a step with no further input (the "designed speed").
- **ICX-STEP.7** Input during `b`'s content (landed, not yet at rest) — decisions #13, R1 §3.3's hybrid. A forward
  gesture sets `dest = b + 1` (`distance = 1`); for `b` = last pinned it is dropped instead (ICX-RELEASE.4). Content
  is never fast-forwarded:
  - if ≤ 0.6 s of `b`'s content is left (`CONTENT_FINISH_MAX`), it finishes at 1×, then the `b → b + 1` transition
    plays (ICX-STEP.1);
  - if more is left, the content's frame is held and crossfades over 220 ms onto `b`'s rest frame (never through dark;
    no new landing, `rendered` stays `b`), then the `b → b + 1` transition plays (amended 2026-10-17, FADEDEF —
    Daniel picked the crossfade over the old dip: "fade feels smoothest").
  - The same crossfade skips the content of a chapter reached by a pass-through landing with `distance = 1` still to
    go (ICX-SIGNED.6), and of a chapter found part-played on a still frame (after FREE or a cooldown stopped the move).
    Inside the cooldown it waits for the cooldown's end, then crossfades. The skipped content never plays.
  - Either way, if further gestures make `distance ≥ 2` by the decision point (the end of the finishing content, or
    the end of the crossfade), it is ICX-DIP to `dest` instead.
  - A back gesture during content is ICX-BACK.2. The dip cooldown (ICX-DIP.4) applies to the skip's crossfade (it
    holds gesture steps only). An explicit jump or a foreign scroll during the crossfade removes the held frame at once
    and the jump's own transition starts at once; a hidden tab pauses the crossfade (ICX-HIDDEN).

### ICX-BACK — Step −1

Rule: a 220 ms fade to the previous checkpoint's rest frame. No replay, in both the story and the tour. If a forward
seam is still running, it plays backwards at 1.5× instead.

- **ICX-BACK.1** From `REST(b)`, one back gesture: one 220 ms dip, landing on `REST(b − 1)`. The story time goes
  straight to `b − 1`'s `rest`; no frame of `b − 1`'s content plays.
- **ICX-BACK.2** During `b`'s content (its seam has finished), one back gesture: the same 220 ms fade to `REST(b − 1)`.
- **ICX-BACK.3** During a forward seam toward `b`, one back gesture: no dip; the seam plays backwards at 1.5× (or
  faster, per ICX-SIGNED.5, never above 3×) and lands on `REST(b − 1)`. If the played part cannot be undone within
  0.6 s by ICX-SIGNED.5's ramp formula (`T_3(R) > 0.6 s` with `r0 = 1.5×`), it is the 220 ms fade to `REST(b − 1)`
  instead.
- **ICX-BACK.4** The same three behaviours hold in the tour.
- **ICX-BACK.5** At `REST(first)`, a back gesture (wheel, key, swipe) is not intercepted: the page scrolls natively,
  and pull-to-refresh works on phones (decisions #16). At any other time a back gesture never takes `dest` below the
  first checkpoint (ICX-SIGNED.1).

### ICX-SIGNED — Gestures during a transition (signed)

Rule: each gesture adds ±1 to a signed `dest`; `rendered` = the last checkpoint fully landed;
`distance = abs(dest − rendered)`.
Reversal precedence: a gesture opposite to the running transition first cancels pending same-direction steps. If
`dest` then equals the transition's origin, a running forward seam plays backwards at 1.5×, and a running back-fade
completes and is followed by a forward step. The running transition rushes (≤ 0.6 s left).
Precedence: the ≤ 0.6 s cap wins, so a reversal plays at max(1.5×, the rate needed to finish within 0.6 s).
Checkpoints passed through skip their content.
Decided (decisions §C) (was OPEN-4/6): the rush and the ≤ 0.6 s cap are bounded by the 3× ceiling. A rush happens
only when a gesture **changes** `dest` and the rest of the running transition, played with the rate ramp, finishes
in ≤ 0.6 s (the formula in ICX-SIGNED.5); otherwise the calm 220 ms dip. Decided (decisions #17) (was OPEN-5): `dest`
is clamped at the last pinned checkpoint. Queued steps (main's ruling, 2026-10-15): each intermediate seam end is a
pass-through landing (Terms); only the final landing plays content, rests, announces and writes history.

- **ICX-SIGNED.1** N same-direction gestures during a transition move `dest` by exactly N, clamped to
  [first checkpoint, last pinned]; `rendered` changes only at a landing (Terms). A forward gesture whose `+1` would
  pass the last pinned is dropped: it does not change `dest`, does not rush, and does not release (decisions #17).
  Only a forward gesture that starts at `REST(last pinned)` releases (ICX-RELEASE.1). The same clamp holds at the first
  checkpoint (ICX-BACK.5).
- **ICX-SIGNED.2** Forward seam from origin `o` toward `o + 1`, `dest = o + 1`, one opposite gesture: `dest = o`, the
  seam plays backwards and lands on `REST(o)`.
- **ICX-SIGNED.3** Back-fade from `o` toward `o − 1`, one forward gesture: the fade completes, then a forward step
  plays (`o − 1 → o`).
- **ICX-SIGNED.4** The arithmetic is always ±1 per gesture; an opposite gesture removes one pending same-direction
  step before any reversal can happen. Example: forward seam `o → o + 1` with `dest = o + 3`. One back gesture →
  `dest = o + 2` (no reversal: `dest` is not the origin). A second → `dest = o + 1` (all pending steps cancelled; the
  seam keeps going to `o + 1`). A third → `dest = o` (the origin) → the seam plays backwards (ICX-SIGNED.2).
  Decision time (decisions §C) (was OPEN-4): the dip decision is taken when a gesture changes `dest` during a
  transition and again at each landing. If the running transition can rush (ICX-SIGNED.5), it rushes to its landing
  and `distance` is judged from the new `rendered` there (1 → step, ≥ 2 → ICX-DIP); so in the example, a seam that can
  rush makes a pass-through landing on `o + 1` (no content, no announcement, no history) and then steps to `o + 2`,
  whose final landing plays its content and writes history. If it cannot rush, the 220 ms dip to `dest` starts at
  once, and the back gesture during its fade-out moves the cut to `o + 2` (ICX-DIP.2).
- **ICX-SIGNED.5** Rush (decisions §C; acceleration-aware per main's ruling). Let `R` = the story time left in the
  running transition, `r0` = the current playback rate (1× in a normal step), `A` = `RATE_ACCEL` (config, 12 /s²),
  `c` = a rate cap. With the rate ramping from `r0` up to `c` at `A`:
  `t_ramp = (c − r0) / A`, `d_ramp = r0·t_ramp + A·t_ramp² / 2`;
  `T_c(R) = (√(r0² + 2·A·R) − r0) / A` if `R ≤ d_ramp`, else `t_ramp + (R − d_ramp) / c`.
  When a gesture changes `dest` during a running transition: if `T_3(R) ≤ 0.6 s` it rushes, ramping toward the cap
  `c* = max(RUSH, the smallest c ≤ 3× with T_c(R) ≤ 0.6 s)`, and finishes within 0.6 s (at `r0 = 1×`, `A = 12 /s²`
  this holds for `R ≤ 1.633 s`; e.g. 1.8 s would take ≈ 0.656 s, so it dips). Otherwise the transition is cut by the
  220 ms dip to `dest` (to its rest-entry; or to the origin's rest frame when `dest` is the origin), subject to the
  dip cooldown (ICX-DIP.4). A gesture that does not change `dest` (clamped, ICX-SIGNED.1) does not rush. The ramp
  needs no deceleration at the end: a seam ends on a still frame (R1 §3.2).
  A reversal (ICX-SIGNED.2) uses the same formula with `R` = the played part of the seam and `r0` = `ABORT_RATE`
  (1.5×, R1 §3.3's abort, which starts at that rate): if `T_3(R) ≤ 0.6 s` it plays backwards toward
  `c* = max(1.5×, the smallest c ≤ 3× with T_c(R) ≤ 0.6 s)` (at `A = 12 /s²` this holds for `R ≤ 1.706 s`);
  otherwise the 220 ms fade to the origin's rest frame.
- **ICX-SIGNED.6** A checkpoint passed through on the way to `dest` (a pass-through landing, or cut past by a dip)
  renders none of its content frames, never rests, is never announced, and is never written to history. A
  pass-through landing's frame crossfades onto its rest frame (ICX-STEP.7, no dip) and the next transition plays from
  there (added 2026-10-17, FADEDEF).
- **ICX-SIGNED.7** Rate ceiling (decisions §C): story time on the story or tour stage never advances or reverses
  faster than 3× in any mode, input or phase (checked on `__fxTrace` story time per frame, dips excluded since a cut
  is not playback).

### ICX-DIP — Dip rule

Rule: when `distance ≥ 2` at decision time: one 220 ms dip (fade out → cut to `dest`'s rest-entry → fade in → play its
content). Input during the fade-out updates `dest`, committed at the dark frame. Input during the fade-in or after the
cut counts as a new step from the new `rendered`. Cooldown: at most one dip per 600 ms. Gestures inside the cooldown
still update `dest` (which is preserved); when the cooldown ends, `distance = 1` → step, `≥ 2` → dip.

- **ICX-DIP.1** `distance ≥ 2` at decision time → exactly one dip, 220 ms total; no intermediate checkpoint renders
  (ICX-SIGNED.6). After the cut, `dest`'s content plays from its rest-entry (its content start, decisions §C) to its rest.
- **ICX-DIP.2** A gesture during the fade-out changes where the cut lands: the cut target is `dest` as it stands at the
  dark frame.
- **ICX-DIP.3** The cut is the dip's landing, and a final one (`dest` is committed at the dark frame, so
  `rendered == dest` there): `rendered` becomes the dip's target (onLand, `aria-current`, `aria-live`, history). A
  gesture during the fade-in or after the cut is a new step from that `rendered`; since the target's content is then
  playing, ICX-STEP.7 (forward) or ICX-BACK.2 (back) says how it plays out.
- **ICX-DIP.4** Two dips never start less than 600 ms apart. Gestures inside the cooldown still change `dest`. At the
  cooldown's end: `distance == 1` → a step (ICX-STEP/ICX-BACK), `distance ≥ 2` → a dip, `distance == 0` → nothing.
- **ICX-DIP.5** "3 gestures = 3 pages": three forward gestures in quick succession from `REST(b)` land on
  `REST(min(b + 3, last pinned))` (clamp, ICX-SIGNED.1); three back gestures land on `REST(max(b − 3, first))`. At
  `REST(last pinned)` the first forward gesture releases instead (ICX-RELEASE.1); at `REST(first)` the first back
  gesture scrolls natively (ICX-BACK.5).

### ICX-JUMP — Explicit jump (rail/menu click, Home/End, logo, deep link)

Rule (vault §3, quoted): target ±1 → the same as a step. Otherwise → one dip to the target, then play its content
(deep links play the demo). Back/Forward (popstate): the same visual behaviour, but never writes history.
Read with ICX-JUMP.0: "otherwise" means distance ≥ 2; a jump at rest to the checkpoint already landed (distance 0)
moves nothing and writes no history.

- **ICX-JUMP.0** Zero distance: a jump at rest whose target is the checkpoint already landed (`target == rendered`,
  e.g. a rail click on the current chapter, or End at `REST(last pinned)`, ICX-KEY.6) moves nothing: no dip, no content
  replay, no history write. DECIDED (decisions #14, 2026-10-15): clicking the current chapter does nothing (no
  replay). The same during the landed checkpoint's content (main's ruling, 2026-10-15): a click on the current chapter,
  or End while the last pinned's demo plays, does nothing — no dip, no restart, no history write — and the demo
  continues to rest. During a transition, `target == rendered` is ordinary signed input (ICX-SIGNED: `dest` becomes
  the target).
- **ICX-JUMP.1** A jump to `rendered + 1` behaves exactly as ICX-STEP; to `rendered − 1` exactly as ICX-BACK.
- **ICX-JUMP.2** Any other pinned target (`|target − rendered| ≥ 2`): one dip (ICX-DIP) to the target, then its content
  plays to rest, in either direction.
- **ICX-JUMP.3** Deep link vs reload (decisions #25). A deep link (a fresh load of `/#<slug>` to a pinned row) plays
  that chapter's demo: no other checkpoint's frame or content is shown first, the target's content plays from its
  rest-entry to its rest, and `rendered` is the target from the first frame. A reload (navigation type `reload`) lands
  on that chapter's finished rest frame: no content plays, no dip. Neither writes history (ICX-HIST.3). A deep link or
  reload whose row is `native` in the current mode (or in classic) is the browser's own anchor scroll to its `id`.
  (added 2026-10-17, INT5-fix) A reload or history visit of the same entry the reader left below the story (the footer)
  returns to that distance below it, even when the URL names a pinned chapter.
- **ICX-JUMP.4** popstate: the same visuals as .0/.1/.2, and no `pushState`/`replaceState` call (ICX-HIST.3).
- **ICX-JUMP.5** A rail/menu jump to a row that is `native` in the current mode (e.g. tablet "Price", phone "A note")
  is a smooth native anchor scroll to its anchor (`behavior: "smooth"`); instant under reduced motion and in classic
  (ICX-CLASSIC.3). It pushes one history entry like any jump, written when the scroll arrives (ICX-HIST.2). Decisions
  §C (was OPEN-9). (added 2026-10-17, INT5-fix) A theme switch while a native jump is still scrolling carries the jump
  through to its target; the arrival writes its one push there.

### ICX-REST — Never rest mid-transition

Rule: invariant: if there is no input for (transition + content + 1 s), `phase == "rest"` on a checkpoint. A test
checks it under fuzz.

Scope: the invariant applies in a mode with pinned rows, with the story's pinned track in play, and counts only time
while the tab is visible.

- **ICX-REST.1** Fuzz (random wheel, key, touch, rail clicks, popstate, foreign `scrollTo`, resize), pinned mode, tab
  visible: after the last input, within the target checkpoint's transition + content + 1 s of visible time,
  `phase == "rest"`, `rendered == dest`, and ICX-CHECKPOINT.2 holds — or the phase is RELEASED with `scrollY` below
  the pinned track, which also satisfies the invariant (decisions §C; nothing can be mid-transition there) (was OPEN-16).
- **ICX-REST.2** The phase never stays mid-transition or mid-dip with no input while the tab is visible (no stall).
- **ICX-REST.3** Tab hidden: the invariant is suspended and ICX-HIDDEN.1 holds instead (time stops). Time spent hidden
  does not count toward the allowance; after return, ICX-REST.1 applies again from the moment the tab became visible.
- **ICX-REST.4** Classic / calm / static / no-JS (no pinned rows): there are no checkpoints and no transitions; what
  holds instead is ICX-CLASSIC.1 (nothing autoplays, story time never advances).

### ICX-RELEASE — Release

Rule: at the last pinned checkpoint, a forward gesture is not intercepted: native scroll into the following sections.
Scrolling back into the pin re-enters at the last checkpoint. (C0a's mechanics: ICX-SETTLE-8.)

- **ICX-RELEASE.1** At `REST(last pinned)`, a forward wheel, key or swipe is not `preventDefault`ed, and `scrollY`
  moves past the pinned track natively.
- **ICX-RELEASE.2** Scrolling back up into the pin (wheel, key, swipe or momentum) lands on `REST(last pinned)`, never
  mid-transition and never on an earlier checkpoint; the next back gesture is an ordinary ICX-BACK. One exception, from
  C0a (ICX-SETTLE-4): a **scrollbar drag** from below that is held at an earlier beat is an explicit choice and settles on
  that beat (`nearest`): it lands where the reader stopped. DECIDED (decisions #15, 2026-10-15).
- **ICX-RELEASE.3** Last pinned per mode: desktop `end`, tablet `chase`, phone `end` (the phone order as shipped,
  ICX-DEST).
- **ICX-RELEASE.4** Clamp before release (decisions #17): forward gestures that arrive during the transition into, or
  the content of, the last pinned checkpoint are dropped (ICX-SIGNED.1): the page never scrolls past the pin, and it
  rests on the last pinned (the Get the app card on desktop and phone). The next forward gesture from
  `REST(last pinned)` releases.

### ICX-HIST — History (by navigation source)

Rule (vault §3, quoted): user steps → `replaceState`. User jumps (rail, menu, Home/End, logo) → `pushState`.
Initialization (deep link, reload) and history traversal (popstate) never push or replace. Hash = the checkpoint slug
from the destination table. Read with ICX-JUMP.0: a zero-distance jump at rest is not a move and writes nothing.
The theme toggle never writes the hash.

Decided (decisions §C) (was OPEN-12): history is written **on the final landing** (Terms), never when `dest`
changes and never at a pass-through landing: `replaceState` for steps, FREE settles and scroll-spy; `pushState` only
for explicit jumps. A checkpoint passed through is never written.

- **ICX-HIST.1** A run of steps writes once, at its final landing, the landed checkpoint's URL (`rendered == dest`)
  with `replaceState` (`history.length` unchanged). Pass-through landings write nothing; while the run is under way the
  URL still shows the checkpoint the run started from. (added 2026-10-17, INT5-fix) A mode change (Classic on/off, a
  layout change) ends any jump in flight without a write: its pending push and a native jump's arrival write are void;
  a landing already made but not yet written is written first.
- **ICX-HIST.2** A rail, menu, Home/End or logo jump that moves (`target ≠ rendered`, ICX-JUMP.1/.2/.5) adds exactly
  one history entry with `pushState` at its final landing (the seam's end, the dip's cut, or the native scroll's
  arrival), carrying the landed checkpoint's URL. If gestures extend the run after the jump, the run still writes one
  entry, with `pushState`, at its final landing, so Back undoes the whole run. A zero-distance jump (ICX-JUMP.0) leaves
  the URL and `history.length` unchanged.
- **ICX-HIST.3** Load with a hash, reload, and popstate make no `pushState`/`replaceState` call (spy on both). The one
  exception is a legacy hash (ICX-HIST.6).
- **ICX-HIST.4** Toggling the theme leaves the URL and `history.length` unchanged.
- **ICX-HIST.5** The first checkpoint's URL is plain `/` with no hash (decisions #18): landing on it writes
  `location.pathname` with no `#`. Every other URL the story writes is `/#<slug>` with one of the other eight slugs.
  The story never writes a legacy or theme hash.
- **ICX-HIST.6** Legacy hashes (decisions #19): when the URL carries `#top`, `#how`, `#pricing` or `#download` (on
  load or on `hashchange`), the page lands on that chapter (`top` → New invoice, `how` → Templates, `pricing` → Price,
  `download` → Get the app; site.js `ANCHOR`) under the deep-link/reload rule (ICX-JUMP.3), and `replaceState` swaps
  the URL for the chapter's own (`/` for `#top`). `history.length` is unchanged.
- **ICX-HIST.7** Theme hashes `#dark`/`#light` keep working on load (A5 reads them); home never writes them. They are
  not chapter hashes: the page starts on the first chapter, and nothing is written until the next final landing.
- **ICX-HIST.10** (added 2026-10-16, C4-engine) A landing caused by keyboard focus moving onto a chapter (source `focus`)
  writes like a step: `replaceState` at its final landing, never `pushState`, so Tab-ing through the page never fills
  Back. Focus never STARTS a push; a focus landing that extends a run started by an explicit jump keeps that run's single
  `pushState` (ICX-HIST.2). In calm/classic the entry a jump leaves records its scroll offset with the mode and width;
  Back restores it only when the chapter, mode and width match the current ones, otherwise it lands on the chapter's
  anchor (amended 2026-10-17, INT5-fix).
- **ICX-HIST.8** A FREE settle writes its final landing with `replaceState`; a distance-0 re-alignment writes nothing
  (ICX-SETTLE-4). (added 2026-10-17, INT5-fix) A re-entry from below (the reader scrolls back into the pinned story,
  also after arriving on a native row by Back) is a final landing on the last pinned chapter: it writes that chapter's
  URL with `replaceState`, unless the URL already names it (then nothing).
- **ICX-HIST.9** Scroll-spy history (main's ruling, 2026-10-15; owner amended 2026-10-16). In native sections
  (classic/calm, or the native rows of a pinned mode) the scroll-spy runs in the nav module (`rail.js`), in every mode
  that has native sections and whether or not the rail itself is visible; on every change of the current section it
  dispatches `fe:spy` (`detail: {slug}`) on `document`. The one owner of every history write, this one included, is
  `story-url.js` (C4): it writes the current section's URL with `replaceState` **only** when the visitor's own
  scrolling changed the current section (ICX-HL.4). It writes nothing while any of these suppression flags (all
  `story-url.js`'s own) is set:
  - `initializing`: from load (fresh load, reload, deep link, legacy hash) until the scroll that load causes has
    settled (its `scrollend`, or `SETTLE_IDLE` with no scroll where `scrollend` is missing), or at once if none is needed;
  - `restoring`: from a `popstate` until the scroll it causes has settled, the same way;
  - `jumping`: from a programmatic jump to a native row (ICX-JUMP.5) until its arrival, where the jump writes its own
    `pushState` (ICX-HIST.2) instead.
  Explicit jumps (rail, menu, logo, Home/End) go through `window.FEStoryURL.jump(slug)` when it exists: it sets
  `jumping` for a native row, calls `FEStory.goTo(slug, {source: "jump"})`, and pushes one entry at the final landing
  (pinned row) or at the native scroll's arrival (native row). Callers fall back to `FEStory.goTo` when it is absent.
  The highlight and `aria-current` still follow the scroll-spy while a flag is set (ICX-HL.4); only history is
  suppressed.

### ICX-HL — Highlight

Rule: rail, menu and tour chips: the visual highlight follows `dest` on input. `aria-current="location"` moves on
landing (`rendered`). One owner in every mode, the nav module (`rail.js`): pinned mode → the engine's
`onDest`/`onLand`; FREE settling inside the track → the nearest destination; calm/classic/native sections →
scroll-spy (IntersectionObserver) on the destination anchors.

- **ICX-HL.1** After each input, before landing, the highlighted rail/menu/chip item is `dest`'s.
- **ICX-HL.2** Exactly one item carries `aria-current="location"`, and it is `rendered`'s. It changes only on a
  landing as defined in Terms (a step's seam end; a dip's or back-fade's cut), so it never waits for content. It moves
  at pass-through landings too (each queued checkpoint in turn), while the visual highlight stays on `dest`
  (ICX-HL.1); only the final landing is announced (ICX-KEY.2).
- **ICX-HL.3** In FREE, the highlight is the destination nearest `scrollY` (ICX-SETTLE-2's `nearest`).
- **ICX-HL.4** In calm/classic/native sections, highlight and `aria-current` follow an IntersectionObserver on the
  destination anchors. A native section is current when its top has crossed 40 % of the viewport height
  (`SPY_LINE`): the current one is the last anchor, in beat order, whose top is at or above that line (decisions §C) (was OPEN-17).
- **ICX-HL.5** Only `rail.js` sets the highlight or `aria-current` on nav items (a source grep finds no other
  writer).

### ICX-CLASS — Gesture classification

Rule: notch vs smooth is decided on a gesture's first event and held until that gesture ends at the quiet threshold.
It resets for each new gesture.

- **ICX-CLASS.1** The detector's class for every event of a gesture equals the class of its first event.
- **ICX-CLASS.2** The gesture ends after a quiet gap longer than `QUIET_NOTCH` (notch) or `QUIET_SMOOTH` (smooth);
  the next event starts a new gesture and is classified afresh, except a gap inside a still-moving inertia tail
  (ICX-CLASS.4).
- **ICX-CLASS.4** (FLICKER, 2026-10-16, main-approved) A gap is the hand going quiet only if the hand could have been
  heard: an inertia tail emits an event every frame while it moves, so a gap in one is the page or browser holding input
  back (a busy main thread; Chrome coalesces held wheel events). A gap > `QUIET_SMOOTH` does not end a smooth flick
  (peak ≥ `V_RISE_MIN`, frame-paced: at least 3 event gaps under `SPREAD_MIN`, which separate mouse clicks are not) whose rate
  when the gap began was ≥ `TAIL_LIVE`, when the next event is in the same direction, comes ≤ `JOIN_MAX` after the last
  one and is not a line-mode (`deltaMode` 1) event: the gesture carries on, with no new start step. Only a tail joins:
  it was decaying when the gap began (its rate ≤ `TAIL_DECAY` × its peak, or its last delta below its biggest delta)
  and its last 3 deltas were not mouse notches (all ≥ `NOTCH_HINT_PX` and multiples of one size: 100/100/100,
  100/200/100). A fast-spun mouse wheel is frame-paced too, but its notches hold the rate and repeat one size, so its
  later clicks step exactly as before this rule (Sol FLICKER-2 #2); a stream still speeding up when it went quiet is
  the hand stopping, not a tail. (A `wheelDeltaY` multiple of 120 is NOT a notch signature here: Chrome's coalesced
  trackpad events can carry ±240 — Sol FLICKER-1 #1.) A deliberate new flick in a joined gesture still steps by the
  rise test. Known trade-off (Sol FLICKER-2 #1, main's ruling 2026-10-17): a gentle second flick (under `V_RISE_MIN`)
  within `JOIN_MAX` of a still-moving tail joins it and does not step; it needs a firmer swipe. A missed step is
  gentler than the double step + dip, and a re-acceleration step read partly coalesced tail deliveries as a new flick
  (Sol FLICKER-3 #2). Daniel tunes `JOIN_MAX` / `TAIL_LIVE` on devices. Measured: one flick read as two gestures at
  22–26 of 26 stall positions before (tests/checkpoint/test_flicker.py), the second step dipping mid-Ride (Daniel:
  "flicker for a second before it moves again").
- **ICX-CLASS.5** (FLICKER) Rates are measured over the time the input covers: a smooth event more than `SPREAD_MIN`
  after the previous one counts its delta spread evenly over that gap (a coalesced event carries the frames the page
  did not hear), and events under `BUNCH_MS` after such an event are the same held-back delivery. A held-back burst is
  therefore never a rise (a 40–45 ms stall at 120 Hz stepped twice before).
- **ICX-CLASS.3** A smooth flick whose first delta is ≥ 50 px (so it gets the notch hint) still steps once
  (ICX-SETTLE-D1).

### ICX-NOPROG — No progress UI

Rule: no counters, numbers, fills, progress bars, timecodes or Pause anywhere (DEC-4).

- **ICX-NOPROG.1** In every mode, the rail, menu, tour chips and caption eyebrows contain no digits and no "n / N"
  or "n of N" text.
- **ICX-NOPROG.2** No `<progress>`, `role="progressbar"`, `role="meter"` or `aria-valuenow` on the homepage or tour;
  no element whose size or fill tracks the story or tour position.
- **ICX-NOPROG.3** No timecode and no Pause/Play control. The WCAG 2.2.2 stop control is the classic-view toggle
  (ICX-CLASSIC.6), DECIDED (DEC-6, 2026-10-15). The fe:claims / a11y sign-off that this meets WCAG 2.2.2 is a QA task
  on K1 (decisions §C) (was OPEN-22).

### ICX-CLASSIC — Classic view / reduced motion

Rule: no autoplay. The story = native sections with anchors. The tour = chapter end states. Steps and jumps are
instant. (Decisions #23: reduced motion now sets only the starting state, ICX-CLASSIC.8; the rule applies whenever
classic is on.)
Classic view — DECIDED (DEC-7, 2026-10-15): a visible, persistent toggle switches to the calm/static layout
(native sections, no autoplay); it keeps the reading place and is remembered per visitor.
Global stop — DECIDED (DEC-6, 2026-10-15): the classic-view toggle is the global stop control.
Toggle — DECIDED (decisions #23, DEC-1): in the slim top bar (sticky, never hides) next to the theme toggle; icon +
"Classic" at ≥ 1024 px, icon-only below (the label in `aria-label` and a tooltip); also on `/tour/`; reduced-motion
visitors start in classic but may switch the story on; remembered per visitor in `localStorage` `fe-classic`. The
label is NEW COPY for fe:claims.

- **ICX-CLASSIC.1** With classic view on: nothing autoplays; every destination is `native` (ICX-DEST); each has its
  anchor.
- **ICX-CLASSIC.2** The tour with classic on shows each chapter's end state, with no autoplay.
- **ICX-CLASSIC.3** Steps and jumps are instant: no transition, no dip, no smooth scroll.
- **ICX-CLASSIC.4** In every mode where the story (or the tour's autoplay) can run, the toggle sits in the top bar
  next to the theme toggle on the homepage and on `/tour/`, so it is visible without scrolling and while the page
  scrolls. Where calm is automatic it is absent (ICX-CLASSIC.9). At ≥ 1024 px it shows the icon and the visible
  text "Classic"; below 1024 px the icon only, with an `aria-label` and a tooltip carrying the label.
- **ICX-CLASSIC.5** Switching either way keeps the reading place and focus (ICX-DEST.4).
- **ICX-CLASSIC.6** Switching to classic stops every running autoplay at once (story and tour).
- **ICX-CLASSIC.7** The choice is stored in `localStorage` `fe-classic` and survives a reload and a new visit in the
  same browser, on the homepage and `/tour/` alike.
- **ICX-CLASSIC.8** With `prefers-reduced-motion: reduce` and no stored choice, the page starts in classic. A stored
  choice wins over the media query, so a reduced-motion visitor who switches the story on gets it on the next visit
  too. With the story on under reduced motion, native anchor scrolls stay instant (ICX-JUMP.5).
- **ICX-CLASSIC.9** Short touch screens stay calm automatically (ICX-DEST.6, decisions #22). Decided by main
  2026-10-15: on a screen where calm is automatic the classic toggle is **not shown** (there is no autoplay to stop and
  no story to switch to, so it would be a dead control); the stored `fe-classic` choice is kept untouched for larger
  screens. Test: at 375×548 coarse pointer the toggle is absent from the accessibility tree and the page is calm.

### ICX-HIDDEN — Hidden tab

Rule: autoplay pauses and resumes at rest. DECIDED (DEC-6, 2026-10-15): autoplay pauses when the tab is hidden.
DECIDED (decisions #24): on return it resumes from where it paused (no replay, no jump).

- **ICX-HIDDEN.1** On `visibilitychange` to hidden, story and tour time stop advancing.
- **ICX-HIDDEN.2** On return to visible, story time continues from the exact value it had when hidden (the first
  visible frame shows the paused frame; no replay, no jump to the rest frame), at the rate it had (≤ 3×), and the run
  ends at rest on the same `dest`. Hidden time does not count toward ICX-REST.1.

### ICX-KEY — Keyboard

Rule: arrows, PgUp/PgDn, Space/Shift+Space, Home/End → steps and jumps inside the pinned story. `aria-live` announces
the landed checkpoint name. Focus is not moved. DECIDED (DEC-6, 2026-10-15): `aria-live` announces landings without
moving focus. Decided (decisions §C) (was OPEN-20): only Up/Down/PgUp/PgDn/Space/Home/End are intercepted; R1 §3.4's
ignore list is adopted; the polite `aria-live` announces every final landing, whatever caused it (pass-through
landings are not announced, main's ruling 2026-10-15).

- **ICX-KEY.1** Inside the pinned story: ArrowDown, PageDown, Space → step +1; ArrowUp, PageUp, Shift+Space →
  step −1; Home → jump to the first checkpoint; End → jump to the last pinned. ArrowLeft and ArrowRight are never
  intercepted.
- **ICX-KEY.2** On every final landing (key, wheel, touch, rail/menu, settle, popstate), an `aria-live="polite"`
  region's text becomes the landed checkpoint's name (ICX-DEST); nothing is announced mid-transition or at a
  pass-through landing.
- **ICX-KEY.3** `document.activeElement` is the same before and after any key step or jump.
- **ICX-KEY.4** A held key (`e.repeat`) steps at most once per `KEY_REPEAT_MS` (config).
- **ICX-KEY.5** At the last pinned, a forward step key (ArrowDown, PageDown, Space) passes natively
  (ICX-RELEASE.1), unless it arrives before `REST(last pinned)` (dropped, ICX-RELEASE.4).
- **ICX-KEY.6** Home and End always jump (vault Keyboard row; C0a S8 / ICX-SETTLE-8), from the pinned story and from
  below it (RELEASED): Home → the first checkpoint, End → the last pinned. End at `REST(last pinned)` is a jump to the
  checkpoint already landed (`distance == 0`): nothing moves, and End is not passed to the page. R1 §3.4's "End at the
  last beat passes through to the page end" is superseded (vault §3 supersedes R1–R3). (added 2026-10-17, INT5-fix)
  Home and End go through the same jump path as the rail (`FEStoryURL.jump`), so the departing offset is saved before
  the page moves.
- **ICX-KEY.7** Ignored (never intercepted, never step; R1 §3.4): `e.defaultPrevented` (the rail's own arrow and
  Home/End roving); Alt, Ctrl or Meta held; focus in `input`, `textarea`, `select` or `[contenteditable]`; Space while
  focus is on `a`, `button`, `summary` or `[role=button]`; an open dialog.

### ICX-BYPASS — Bypass

Rule: Ctrl/⌘ + wheel (zoom), pinch, and input inside dialogs or form fields are never intercepted.

- **ICX-BYPASS.1** A wheel event with `ctrlKey` or `metaKey` is never `preventDefault`ed and never steps.
- **ICX-BYPASS.2** A pinch (a second finger) never steps; a touch while pinch-zoomed pans (ICX-SETTLE-9).
- **ICX-BYPASS.3** Wheel, key and touch whose target is inside an open dialog, `input`, `textarea`, `select` or
  `[contenteditable]` are never `preventDefault`ed and never step.
- **ICX-BYPASS.4** Decided (decisions §C; R1 §3.4) (was OPEN-21): a wheel event with `abs(dx) > abs(dy)` (horizontal
  swipes, macOS back/forward), and a wheel or touch whose target is inside a nested scroll container that can still
  scroll in that direction (`composedPath()` check), are never `preventDefault`ed and never step.

## ICX-SETTLE — settle rules from C0a

From `docs/cp-spike-verdict.md` ("Settle rules: the ICX patch for C0b"). The evidence cited is that file's verdict row
and its files under `scratch/cp-spike/evidence/<column>/` (C0a branch, final run on 801bae3). Constants are in
`docs/checkpoint-config.md` § "Settle (C0a)".

| Id | Rule | Test asserts | Evidence |
|---|---|---|---|
| **ICX-SETTLE-1** Acknowledge by position | `syncScroll(y)` rounds `y` to an integer and clamps it to the scroll range. If `abs(scrollY − y) ≤ 0.5` it does nothing and arms nothing. Otherwise it stores `pending = {y, until: now + ACK_MS}` and calls `scrollTo({top: y, behavior: "instant"})`. A `scroll` event with `abs(scrollY − pending.y) ≤ ACK_TOL` before `until` is ours. No boolean "next event is ours" flag. | Every landing's own scroll is acknowledged and never enters FREE; a no-op `syncScroll` arms nothing; source has no boolean ack flag. | verdict row R1 (PASS on all three proxies): `R1__*.json` |
| **ICX-SETTLE-2** FREE | Any other `scroll` event with `storyTop − 1 ≤ scrollY ≤ storyEnd + 1` enters FREE: the stage keeps its frame, and the rail previews `nearest = round((scrollY − storyTop) / BEAT_PX)`. Below `storyEnd + 1` it is RELEASED; above `storyTop − 1` it is the page above. | A foreign `scrollTo` inside the track: phase FREE, the stage frame unchanged, the highlight = `nearest`. Below: RELEASED. FREE is entered synchronously or within one frame of a foreign scroll (C3 build task BT-1). | verdict rows R2, R3 (footnote 3) |
| **ICX-SETTLE-3** Settle trigger | With `onscrollend`: settle `SCROLLEND_GRACE` after a `scrollend`, only if no `scroll` came in that time. Without `scrollend`: settle after `SETTLE_IDLE` of no scroll events. Always: a `SETTLE_BACKSTOP` timer re-armed on every scroll event. Feature-detect and carry both paths (BT-2). | A 1 s scroll stream gives exactly one settle (both paths, `?noscrollend` forcing the idle path); the backstop fires if neither does. | verdict rows R6 (`R6__*-nograce.json`: 30 settles without the grace), R7 (≈ 167 ms idle latency) |
| **ICX-SETTLE-4** Settle target | The nearest beat, as a jump (ICX-JUMP: ±1 = a step, ≥ 2 = a dip). Distance 0 (the nearest beat is the one already landed, the page merely scrolled off it): a re-alignment only — the page scrolls back to that beat's position, no dip, no content replay, no history write (unlike ICX-JUMP.0, the scroll position does move). The settle's own scroll is acknowledged (ICX-SETTLE-1). Re-entry from below: a FREE episode that began in RELEASED settles on the last pinned beat unless a scrollbar hold was seen in it; a new FREE episode within `REENTRY_STICKY_MS` of such a settle still counts as re-entry, again unless a scrollbar hold is seen in that new episode (a held drag always settles on `nearest`, ICX-RELEASE.2). | After a settle, no second FREE, and `phase == "rest"` on: the last pinned, if the FREE episode is a re-entry AND no scrollbar hold was seen in it (it began in RELEASED, or began within `REENTRY_STICKY_MS` of such a settle); otherwise `nearest`. A momentum stream from below lands on the last pinned and never walks back. | verdict row R8 (844×390 walked back to beat 7 before the rule) |
| **ICX-SETTLE-5** Settle cancellation | An intercepted gesture (wheel, key, touch) during FREE cancels the pending settle and counts from **the beat the settle would have picked** (ICX-SETTLE-4's target: the last pinned on a re-entry with no scrollbar hold seen, otherwise the beat nearest the current `scrollY`), not from the stage's frame. A further foreign scroll restarts the timers. If the settle wins the race, the outcome is the same beat. | Scrollbar drag then an immediate wheel or key: exactly one move, to `settleTarget ± 1` clamped to [first checkpoint, last pinned], whichever path ran (re-entry with no scrollbar hold seen: `last pinned − 1` for a back gesture; otherwise, a held drag included: `nearest ± 1`, clamped). Where the clamp bites, a forward gesture counted from the last pinned releases instead (ICX-RELEASE.1) and a back gesture counted from the first scrolls natively (ICX-BACK.5). | verdict row R3 (Chromium 1440×900 intermittent, footnote 3; BT-1) |
| **ICX-SETTLE-6** Scrollbar hold | A capture-phase `mousedown` on `document` with `clientX ≥ documentElement.clientWidth` (or `clientY ≥ clientHeight`) means held: the settle waits. The hold ends on `mouseup`/`pointerup`, a `mousemove` with `buttons === 0`, window `blur`, or `HOLD_MAX`. Overlay scrollbars are invisible to this test; there the settle relies on ICX-SETTLE-3. | Classic scrollbar: no settle during a 1 s still hold; exactly one settle on release. | verdict row R5 (`R5__*-classicbar.json`, footnote 5) |
| **ICX-SETTLE-7** Resize / rotation | On every `resize`, re-measure at once (no debounce for the re-snap). `BEAT_PX = round(100svh − header)` in integer CSS px; the pin height is the same integer. Inside the story: `syncScroll(y_dest)`. RELEASED: keep the distance below `storyEnd`, from the last scroll position seen at the old viewport size, clamped to the new room below the story. Browser scroll corrections within `RESIZE_GRACE` after a real geometry change are re-snapped, never FREE. Page boot is not a geometry change. `overflow-anchor: none` on `html` and `body`. A height-only change where 100svh did not move is a no-op. Measure with offsets and `scrollY` only, never `getBoundingClientRect`. | Resize/rotate on a beat: the same beat, `scrollY` on its track position, no FREE. Below the story: distance kept (or clamped). Source has no `getBoundingClientRect` in the input/settle layer. | verdict row R4 (footnote 4) |
| **ICX-SETTLE-8** Release / re-entry | At `REST(last)`, a forward wheel, key or swipe is not intercepted. Wheel from below: events pass while `scrollY + dy ≥ storyEnd`; the event that would cross is prevented, `syncScroll(storyEnd)` lands `REST(last)`, and the rest of that gesture is swallowed. Keys from below pass natively (then ICX-SETTLE-2/4). Home and End always jump. | ICX-RELEASE.1/.2 plus: the crossing wheel event is prevented and the rest of that gesture steps nothing. | verdict row R2 (footnotes 1, 2) |
| **ICX-SETTLE-9** Bypass | Ctrl+wheel is never prevented (it scrolls natively, then FREE and settle). A touch while `visualViewport.scale > 1.01` pans and never steps. A second finger ends the touch with no step. Pinch zoom (amended 2026-10-16, C6-fix): a FREE episode that sees `visualViewport.scale > 1.01` never settles and never releases while zoomed; when the scale returns to ≤ 1.01 it settles once on the beat that was landed, as ICX-SETTLE-4's distance-0 re-alignment (no dip, no content replay, no history write), never on `nearest`; an intercepted gesture during it counts from that beat (ICX-SETTLE-5); a pure zoom with no layout scroll enters no FREE and settles nothing. | ICX-BYPASS.1/.2 plus: a Ctrl+wheel inside the track never steps. If the browser scrolls natively on it (as headless Chromium did in C0a), exactly one settle follows (via FREE); if it does not scroll, no settle. | verdict row R9 (footnote 8: iPhone partial) |
| **ICX-SETTLE-D1** Detector note | R1 §3.4 counts a notch gesture as "sustained" by any event. Fix: notch gestures also need `vNow ≥ SUSTAIN_K · peakSinceStep` to repeat (smooth gestures already did). | A smooth flick with a ≥ 50 px first delta and a decaying tail longer than `REPEAT_MS` steps once; a sustained notch spin still repeats every `REPEAT_MS`. | `S1__*-r1notch.json` (R1's rule fails), verdict row R2 (WebKit first run) |

## Not machine-testable (judged by a person)

- "The designed speed" and the story feel, including the Ride and Make→Look: Daniel judges on frame strips and the
  C5 live A/B switch (DECIDED (DEC-8, 2026-10-15)). ICX-STEP.2/.3 check only that motion is unchanged, the dead-time
  ceilings, and the Ride's 1.45 s ± 0.1 s. A named exception is accepted by Daniel's eye, not by a number.
- "≤ 5 s where feasible": a test checks the 5 s ceiling and the named-exception list (ICX-STEP.4).
- A named caption exception (ICX-STEP.3; none in v1) is accepted only on frame strips Daniel has seen.
- "Visible" toggle: ICX-CLASSIC.4 checks it is in the viewport, not that people notice it.
- The device feel of every ICX-SETTLE row (C0a's last column, below): only the M1 device session can judge it.

## Build tasks for C3

Not questions: work C3 must do and prove.
- **BT-1** (ICX-SETTLE-2/5) (was OPEN-23) Chromium 1440×900 R3 was intermittent in C0a: FREE was sometimes not yet
  entered 40 ms after a foreign `scrollTo`. C3 proves FREE is entered synchronously or within one frame, under load.
- **BT-2** (ICX-SETTLE-3) (was OPEN-24) Whether shipping Safari has `onscrollend` is UNVERIFIED-DEVICE. C3
  feature-detects and carries both settle paths, each covered by a test (`?noscrollend` forces the idle path).

## Decision status

All decided 2026-10-15 (decisions-2026-10-15.md, by main under Daniel's delegation), including main's follow-up
rulings: the classic toggle is hidden where calm is automatic (ICX-CLASSIC.9); a skipped demo cuts to this chapter's
rest frame and the normal transition still plays (ICX-STEP.7; the seam, the Ride included, is never skipped); caption
timing is ICX-STEP.3 (empty caption-exception list in v1); queued steps pass through (Terms, ICX-HIST.1); rushes are
acceleration-aware (ICX-SIGNED.5); scroll-spy history is suppressed outside the visitor's own scrolling
(ICX-HIST.9); zero-distance jumps during a demo do nothing (ICX-JUMP.0).


Device-only items for the M1 device session (C0a, every real-device cell UNVERIFIED-DEVICE; Mac Safari, Windows
Chrome/Edge, iPhone Safari):
- **R1 acknowledgement:** Mac trackpad (Safari + Chrome), Magic Mouse, Windows notch: a step never shows a jump or a
  one-frame flash of the pinned stage. iPhone: the same with a swipe.
- **R2 boundaries:** trackpad flick at the end card scrolls out with its own inertia; scrolling back up is a soft stop
  on the end card, never a wall or a bounce. Windows notch at the last beat releases one notch. iPhone: swipe out,
  then fling back.
- **R3 settle cancellation:** drag the scrollbar, then wheel or press a key at once: one move, no double jump.
- **R4 resize/rotation:** rotate the iPhone on a beat and below the story; resize the Mac window mid-transition; snap
  a Windows window to half the screen.
- **R5 scrollbar hold:** Windows classic scrollbar: hold still, the page waits; release, one transition. Mac Safari
  overlay scrollbar: hold still > 0.2 s — does it snap mid-hold?
- **R6 autoscroll:** Windows middle-click autoscroll: the stage holds its frame; one transition when it stops.
- **R7 Safari without `scrollend`:** run `'onscrollend' in window` in real Safari; scrollbar drags and find-in-page
  settle cleanly ≈ 0.17 s after they stop.
- **R8 iOS momentum + address bar:** a fling from below lands on the end card with no visible fight; the address bar
  moving mid-story keeps the beat; one finger swipe = one step; pull-to-refresh at the first beat still works;
  landscape. (A no-go here widens ICX-RELEASE on phones.)
- **R9 zoom:** Safari and Chrome ⌘+/− at 110–175 %, then step: beats stay aligned; a trackpad pinch never steps;
  iPhone pinch-zoom, then a swipe pans.
- **Detector feel (C7):** trackpad inertia, Magic Mouse, Windows notches, hi-res ratchet wheels against
  `docs/checkpoint-config.md` version 1.
