# Interaction contract (ICX v1)

Status: DRAFT v1 — defaults pending Daniel (DEC-4/6/7/8); not approved

- **Binding once approved.** Every piece that moves people between checkpoints (story, rail, menu, tour, deep links)
  implements this file. Later DONE WHENs cite a row id (e.g. `ICX-DIP.2`). C3 owns the destination table's
  implementation; C1, C4, B5, B6 and K1 consume it.
- **Source of truth:** vault "Site UX Consolidation — Build Plan (2026-10-14)" §3 (the ICX table and the destination
  table) and §2 DEC-4/6/7/8. It supersedes R1, R2 and R3 where they differ (jumps, back steps, history, fills).
- **Settle rules:** ICX-SETTLE-1…9 and ICX-SETTLE-D1 come from C0a's verdict (`docs/cp-spike-verdict.md`,
  "Settle rules: the ICX patch for C0b"). Each cites its evidence row.
- **Constants:** every number a test needs that is tunable lives in `docs/checkpoint-config.md` (version 1). Numbers
  written here (220 ms, 600 ms, 0.6 s, 1.5×, the DEC-8 budgets) are contract values: changing one is a contract change.
- **Defaults:** each spot marked "DEFAULT (DEC-n), pending Daniel" uses the default offered to Daniel on 2026-10-15.
  An answer is a find-and-edit on that marker.
- **OPEN:** where the vault table is silent, the row says "OPEN-n" and the question is in "OPEN for Daniel" at the end.
  Builders do not pick an answer for an OPEN item; they ask main.

## Terms

| Term | Meaning |
|---|---|
| checkpoint | A rest frame: a story destination whose `kind` is `pinned` in the current mode, or a tour chapter (ICX-CHECKPOINT) |
| native section | A destination whose `kind` is `native` in the current mode: plain document scroll, no interception |
| `dest` | The signed destination: the checkpoint the input so far asks for |
| landing | The moment the move into a checkpoint is complete and only its own content (if any) is left: for a step, the end of its seam; for a dip or a back-fade, the cut (the dark frame); for a reversed seam, its arrival on the origin's rest frame. One definition everywhere: `rendered`, `distance`, `onLand`, `aria-current` (ICX-HL.2) and the `aria-live` announcement (ICX-KEY.2) all change at the landing. Read from the vault's dip row ("input … after the cut counts as a new step from the new `rendered`") |
| `rendered` | The last checkpoint fully landed (see landing). A checkpoint playing its content is landed, so `distance` during content counts from it |
| `distance` | `abs(dest − rendered)` |
| `phase` | The engine state; `"rest"` means resting on a checkpoint with nothing playing |
| transition | The seam from one checkpoint toward the next (ends where the next checkpoint's content starts) |
| content | The checkpoint's own autoplay, from the end of its transition to its rest frame |
| dip | The 220 ms fade out → cut → fade in (ICX-DIP) |
| step | One gesture (wheel gesture, swipe, step key): ±1 |
| jump | An explicit target: rail/menu click, Home/End, logo, deep link, popstate (ICX-JUMP); a FREE settle uses the same visual rule (ICX-SETTLE-4) |
| FREE / RELEASED | C0a states: a foreign scroll inside the track / native scroll below the pinned track (ICX-SETTLE-2) |
| last pinned | The last `pinned` row in the current mode: desktop `end`, tablet `chase`, phone `end` |

## The destination table (ICX-DEST)

Owned by C3; consumed by C4, B5, B6 and K1. One row per destination, in beat order (`BEATS` in `assets/story/site.js`).

Names: DEFAULT (DEC-4), pending Daniel. Slug = the name kebab-cased. No numbers, counters, fills or progress UI
anywhere (ICX-NOPROG).

| beat id | name (rail label, caption eyebrow) | slug (URL hash) | anchor (`src/pages/index.html` section id) | rest (story time of the rest frame) | desktop ≥1024 | tablet 640–1023 | phone <640 | classic / calm / static / no-JS |
|---|---|---|---|---|---|---|---|---|
| `make` | New invoice | `new-invoice` | — no section id (the section sits in `main#top`); OPEN-13 | `TL.HOLD` (desktop dark ≈ 3.60 s) | pinned | pinned | pinned | native |
| `look` | Templates | `templates` | `how` | segment end − 0.02 (≈ 11.11 s) | pinned | pinned | pinned | native |
| `know` | Invoices | `invoices` | — no section id; OPEN-13 | segment end − 0.02 (≈ 15.06 s) | pinned | pinned | pinned | native |
| `grow` | Dashboard | `dashboard` | — no section id; OPEN-13 | segment end − 0.02 (≈ 17.44 s) | pinned | pinned | pinned | native |
| `chase` | Email | `email` | — no section id; OPEN-13 | segment end − 0.02 (≈ 24.94 s) | pinned | pinned (last pinned) | pinned | native |
| `yours` | Your data | `your-data` | — no section id; OPEN-13 | `yours` segment start + 0.28 (≈ 26.14 s) | pinned | native | pinned | native |
| `price` | Price | `price` | `pricing` | `price` segment start + 0.3 (≈ 28.01 s) | pinned | native | native | native |
| `note` | A note | `a-note` | — no section id; OPEN-13 | `brand` segment start + 0.2 (≈ 29.81 s) | pinned | native | native | native |
| `end` | Get the app | `get-the-app` | `download` | desktop: `brand` segment end − 0.05 (≈ 30.56 s); phone: `TL.T1 − END_REST` | pinned (last pinned) | native | pinned (last pinned); OPEN-14 | native |

- **rest:** the expression is today's hold `T` in `site.js` (`holds`, ~:680-692), which R1 §3.2 turns into
  `REST_T[beat]`. The seconds are R1 §2.6's computed desktop dark-theme values, not re-measured here. Light theme: every
  value after the first is 0.91 s earlier (R1 §2.6). Phone and tablet build their own timeline, so their values differ.
  `rest` applies only where the row is `pinned`.
- **Mode counts:** desktop 9 pinned; tablet 5 pinned (make…chase), 4 native; phone 7 pinned (make…chase, yours, end),
  2 native (price, note); classic / calm / static / no-JS 0 pinned, 9 native.
- The vault's mode breakpoints are the ones `site.js` uses today: `desktop()` = width ≥ 1024, `preset()` = "tall"
  below 640. Calm today also covers a short touch screen (OPEN-15).

Assertions:
- **ICX-DEST.1** At a desktop, a tablet and a phone viewport, and in classic/reduced-motion/no-JS, the engine's
  list of pinned destinations equals the table's pinned set for that mode, in beat order.
- **ICX-DEST.2** Each slug equals the kebab-case of its name; the nine slugs are unique; no slug contains a digit.
- **ICX-DEST.3** Rail, menu and caption eyebrows show exactly the table's names (fe:claims checks the words).
- **ICX-DEST.4** Mode flips (resize or rotation across 640 or 1024, the classic toggle, a reduced-motion change) keep
  the reading place (`readingPlace`/`restorePlace`): the destination in view before the flip is the one in view after,
  and `document.activeElement` is unchanged.

## The ICX rows

Each row: the rule (from the vault table), then the assertions a test makes.

### ICX-CHECKPOINT — Checkpoint

Rule: a checkpoint is a rest frame: a story page (mode-aware, see ICX-DEST) or a tour chapter.

- **ICX-CHECKPOINT.1** The story's checkpoints are exactly the rows `pinned` in the current mode (ICX-DEST.1). A
  `native` row is never a checkpoint: no input is intercepted on it.
- **ICX-CHECKPOINT.2** When `phase == "rest"` on checkpoint `b`: `rendered == dest == b`, the story time equals `b`'s
  `rest` exactly, `b`'s caption is the active one, and `scrollY` is within 1 px of `b`'s track position.
- **ICX-CHECKPOINT.3** Tour chapters are checkpoints under the same rules. Their list is not in this table (OPEN-1).

### ICX-STEP — Step +1 (one gesture)

Rule: play the transition to the next checkpoint at the designed speed. Then the checkpoint's content autoplays and
rests.

Budgets — DEFAULT (DEC-8), pending Daniel (Daniel judges the feel by eye on frame strips; tests check only the numbers):
every transition ≤ 1.5 s; Make→Look ≤ 1.6 s; the Ride (the Dashboard → Email seam, `ride`) 1.45 s ± 0.1 s; caption
≤ 0.7 s after the gesture.
Content — DEFAULT (DEC-6), pending Daniel: each automatic content run ≤ 5 s where feasible; typing pace
≥ 90 ms per character.

- **ICX-STEP.1** From `REST(b)` with `b` not last pinned, one gesture sets `dest = b + 1`, plays exactly one
  transition, lands `b + 1` at the seam's end (`rendered = b + 1`), plays `b + 1`'s content, and ends in
  `REST(b + 1)`. No dip.
- **ICX-STEP.2** Transition length (gesture → the end of the seam), at 1×: ≤ 1.5 s, except Make→Look ≤ 1.6 s.
  The Ride: DEFAULT (DEC-8), pending Daniel: 1.45 s ± 0.1 s. Daniel still judges the Ride by eye (see "Not
  machine-testable").
- **ICX-STEP.3** The incoming caption becomes the active caption ≤ 0.7 s after the gesture event.
- **ICX-STEP.4** Each checkpoint's content run is ≤ 5 s, except rows listed as "not feasible" (OPEN-2).
- **ICX-STEP.5** Any typed text in content advances at ≥ 90 ms per character.
- **ICX-STEP.6** The playhead never runs faster than 1× in a step with no further input (the "designed speed").
- **ICX-STEP.7** A forward gesture during `b`'s content (landed, not yet at rest): `dest = b + 1`, `distance = 1`, so
  the next move is a step to `b + 1`; two or more such gestures make `distance ≥ 2` → ICX-DIP. A back gesture during
  content is ICX-BACK.2. What happens to the rest of `b`'s content before the forward step: OPEN-25.

### ICX-BACK — Step −1

Rule: a 220 ms fade to the previous checkpoint's rest frame. No replay, in both the story and the tour. If a forward
seam is still running, it plays backwards at 1.5× instead.

- **ICX-BACK.1** From `REST(b)`, one back gesture: one 220 ms dip, landing on `REST(b − 1)`. The story time goes
  straight to `b − 1`'s `rest`; no frame of `b − 1`'s content plays.
- **ICX-BACK.2** During `b`'s content (its seam has finished), one back gesture: the same 220 ms fade to `REST(b − 1)`.
- **ICX-BACK.3** During a forward seam toward `b`, one back gesture: no dip; the seam plays backwards at 1.5× (or
  faster, per ICX-SIGNED.5) and lands on `REST(b − 1)`.
- **ICX-BACK.4** The same three behaviours hold in the tour.
- **ICX-BACK.5** A back gesture at the first checkpoint: OPEN-3.

### ICX-SIGNED — Gestures during a transition (signed)

Rule: each gesture adds ±1 to a signed `dest`; `rendered` = the last checkpoint fully landed;
`distance = abs(dest − rendered)`.
Reversal precedence: a gesture opposite to the running transition first cancels pending same-direction steps. If
`dest` then equals the transition's origin, a running forward seam plays backwards at 1.5×, and a running back-fade
completes and is followed by a forward step. The running transition rushes (≤ 0.6 s left).
Precedence: the ≤ 0.6 s cap wins, so a reversal plays at max(1.5×, the rate needed to finish within 0.6 s).
Checkpoints passed through skip their content.

- **ICX-SIGNED.1** N same-direction gestures during a transition move `dest` by exactly N (subject to OPEN-5 at the
  ends); `rendered` changes only at a landing (Terms).
- **ICX-SIGNED.2** Forward seam from origin `o` toward `o + 1`, `dest = o + 1`, one opposite gesture: `dest = o`, the
  seam plays backwards and lands on `REST(o)`.
- **ICX-SIGNED.3** Back-fade from `o` toward `o − 1`, one forward gesture: the fade completes, then a forward step
  plays (`o − 1 → o`).
- **ICX-SIGNED.4** The arithmetic is always ±1 per gesture; an opposite gesture removes one pending same-direction
  step before any reversal can happen. Example: forward seam `o → o + 1` with `dest = o + 3`. One back gesture →
  `dest = o + 2` (no reversal: `dest` is not the origin). A second → `dest = o + 1` (all pending steps cancelled; the
  seam keeps going to `o + 1`). A third → `dest = o` (the origin) → the seam plays backwards (ICX-SIGNED.2). When the
  "distance ≥ 2" decision is taken while a transition runs (so whether the first back gesture lands inside a dip
  already under way): OPEN-4.
- **ICX-SIGNED.5** After any gesture during a running transition, its remaining play time is ≤ 0.6 s (OPEN-6 for the
  trigger). A reversal runs at max(1.5×, remaining / 0.6 s).
- **ICX-SIGNED.6** A checkpoint passed through on the way to `dest` renders none of its content frames.

### ICX-DIP — Dip rule

Rule: when `distance ≥ 2` at decision time: one 220 ms dip (fade out → cut to `dest`'s rest-entry → fade in → play its
content). Input during the fade-out updates `dest`, committed at the dark frame. Input during the fade-in or after the
cut counts as a new step from the new `rendered`. Cooldown: at most one dip per 600 ms. Gestures inside the cooldown
still update `dest` (which is preserved); when the cooldown ends, `distance = 1` → step, `≥ 2` → dip.

- **ICX-DIP.1** `distance ≥ 2` at decision time → exactly one dip, 220 ms total; no intermediate checkpoint renders
  (ICX-SIGNED.6). After the cut, `dest`'s content plays from its rest-entry (OPEN-7) to its rest.
- **ICX-DIP.2** A gesture during the fade-out changes where the cut lands: the cut target is `dest` as it stands at the
  dark frame.
- **ICX-DIP.3** The cut is the dip's landing: `rendered` becomes the dip's target there (onLand, `aria-current`). A
  gesture during the fade-in or after the cut is a new step from that `rendered`.
- **ICX-DIP.4** Two dips never start less than 600 ms apart. Gestures inside the cooldown still change `dest`. At the
  cooldown's end: `distance == 1` → a step (ICX-STEP/ICX-BACK), `distance ≥ 2` → a dip, `distance == 0` → nothing.
- **ICX-DIP.5** "3 gestures = 3 pages": three gestures in quick succession from `REST(b)` land on `REST(b + 3)`.

### ICX-JUMP — Explicit jump (rail/menu click, Home/End, logo, deep link)

Rule (vault §3, quoted): target ±1 → the same as a step. Otherwise → one dip to the target, then play its content
(deep links play the demo). Back/Forward (popstate): the same visual behaviour, but never writes history.
Read with ICX-JUMP.0: "otherwise" means distance ≥ 2; a jump at rest to the checkpoint already landed (distance 0)
moves nothing and writes no history.

- **ICX-JUMP.0** Zero distance: a jump at rest whose target is the checkpoint already landed (`target == rendered`,
  e.g. a rail click on the current chapter, or End at `REST(last pinned)`, ICX-KEY.6) moves nothing: no dip, no content
  replay, no history write. DEFAULT, pending Daniel (OPEN-26). During a transition, `target == rendered` is ordinary
  signed input (ICX-SIGNED: `dest` becomes the target).
- **ICX-JUMP.1** A jump to `rendered + 1` behaves exactly as ICX-STEP; to `rendered − 1` exactly as ICX-BACK.
- **ICX-JUMP.2** Any other pinned target (`|target − rendered| ≥ 2`): one dip (ICX-DIP) to the target, then its content
  plays to rest, in either direction.
- **ICX-JUMP.3** A deep link (`/#<slug>` on load) to a pinned row plays that row's content and rests there. How it
  starts (dip or not) and what reload does: OPEN-8.
- **ICX-JUMP.4** popstate: the same visuals as .1/.2, and no `pushState`/`replaceState` call (ICX-HIST.3).
- **ICX-JUMP.5** A jump to a row that is `native` in the current mode: OPEN-9.

### ICX-REST — Never rest mid-transition

Rule: invariant: if there is no input for (transition + content + 1 s), `phase == "rest"` on a checkpoint. A test
checks it under fuzz.

Scope: the invariant applies in a mode with pinned rows, with the story's pinned track in play, and counts only time
while the tab is visible.

- **ICX-REST.1** Fuzz (random wheel, key, touch, rail clicks, popstate, foreign `scrollTo`, resize), pinned mode, tab
  visible: after the last input, within the target checkpoint's transition + content + 1 s of visible time,
  `phase == "rest"`, `rendered == dest`, and ICX-CHECKPOINT.2 holds. Whether RELEASED (below the pin) also satisfies
  it: OPEN-16.
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
- **ICX-RELEASE.2** Scrolling back up into the pin lands on `REST(last pinned)`, never mid-transition and never on an
  earlier checkpoint; the next back gesture is an ordinary ICX-BACK.
- **ICX-RELEASE.3** Last pinned per mode: desktop `end`, tablet `chase`, phone `end` (OPEN-14 on the phone's order).

### ICX-HIST — History (by navigation source)

Rule (vault §3, quoted): user steps → `replaceState`. User jumps (rail, menu, Home/End, logo) → `pushState`.
Initialization (deep link, reload) and history traversal (popstate) never push or replace. Hash = the checkpoint slug
from the destination table. Read with ICX-JUMP.0: a zero-distance jump at rest is not a move and writes nothing.
The theme toggle never writes the hash.

- **ICX-HIST.1** A step changes `location.hash` to `dest`'s slug with `history.length` unchanged.
- **ICX-HIST.2** A rail, menu, Home/End or logo jump that moves (`target ≠ rendered`, ICX-JUMP.1/.2) adds exactly one
  history entry, whose hash is the target's slug. A zero-distance jump at rest (ICX-JUMP.0) leaves `location.hash` and
  `history.length` unchanged.
- **ICX-HIST.3** Load with a hash, reload, and popstate make no `pushState`/`replaceState` call (spy on both).
- **ICX-HIST.4** Toggling the theme leaves `location.hash` and `history.length` unchanged.
- **ICX-HIST.5** Every hash the story writes is one of the nine slugs (or empty, OPEN-10).
- Not stated by the vault: the first checkpoint's hash (OPEN-10), legacy and theme hashes (OPEN-11), FREE settles and
  native-mode scrolling, and whether the URL is written on the decision or on the landing (OPEN-12).

### ICX-HL — Highlight

Rule: rail, menu and tour chips: the visual highlight follows `dest` on input. `aria-current="location"` moves on
landing (`rendered`). One owner in every mode, the nav module (`rail.js`): pinned mode → the engine's
`onDest`/`onLand`; FREE settling inside the track → the nearest destination; calm/classic/native sections →
scroll-spy (IntersectionObserver) on the destination anchors.

- **ICX-HL.1** After each input, before landing, the highlighted rail/menu/chip item is `dest`'s.
- **ICX-HL.2** Exactly one item carries `aria-current="location"`, and it is `rendered`'s. It changes only on a
  landing as defined in Terms (a step's seam end; a dip's or back-fade's cut), so it never waits for content.
- **ICX-HL.3** In FREE, the highlight is the destination nearest `scrollY` (ICX-SETTLE-2's `nearest`).
- **ICX-HL.4** In calm/classic/native sections, highlight and `aria-current` follow an IntersectionObserver on the
  destination anchors (threshold OPEN-17).
- **ICX-HL.5** Only `rail.js` sets the highlight or `aria-current` on nav items (a source grep finds no other
  writer).

### ICX-CLASS — Gesture classification

Rule: notch vs smooth is decided on a gesture's first event and held until that gesture ends at the quiet threshold.
It resets for each new gesture.

- **ICX-CLASS.1** The detector's class for every event of a gesture equals the class of its first event.
- **ICX-CLASS.2** The gesture ends after a quiet gap longer than `QUIET_NOTCH` (notch) or `QUIET_SMOOTH` (smooth);
  the next event starts a new gesture and is classified afresh.
- **ICX-CLASS.3** A smooth flick whose first delta is ≥ 50 px (so it gets the notch hint) still steps once
  (ICX-SETTLE-D1).

### ICX-NOPROG — No progress UI

Rule: no counters, numbers, fills, progress bars, timecodes or Pause anywhere (DEC-4).

- **ICX-NOPROG.1** In every mode, the rail, menu, tour chips and caption eyebrows contain no digits and no "n / N"
  or "n of N" text.
- **ICX-NOPROG.2** No `<progress>`, `role="progressbar"`, `role="meter"` or `aria-valuenow` on the homepage or tour;
  no element whose size or fill tracks the story or tour position.
- **ICX-NOPROG.3** No timecode and no Pause/Play control. The WCAG 2.2.2 stop control is the classic-view toggle
  (ICX-CLASSIC.6), DEFAULT (DEC-6), pending Daniel.

### ICX-CLASSIC — Classic view / reduced motion

Rule: no autoplay. The story = native sections with anchors. The tour = chapter end states. Steps and jumps are
instant.
Classic view — DEFAULT (DEC-7), pending Daniel: a visible, persistent toggle switches to the calm/static layout
(native sections, no autoplay); it keeps the reading place and is remembered per visitor.
Global stop — DEFAULT (DEC-6), pending Daniel: the classic-view toggle is the global stop control.

- **ICX-CLASSIC.1** With `prefers-reduced-motion: reduce`, or with classic view on: nothing autoplays; every
  destination is `native` (ICX-DEST); each has its anchor.
- **ICX-CLASSIC.2** The tour shows each chapter's end state, with no autoplay.
- **ICX-CLASSIC.3** Steps and jumps are instant: no transition, no dip, no smooth scroll.
- **ICX-CLASSIC.4** The toggle is visible without scrolling in every mode and stays reachable while the page scrolls.
- **ICX-CLASSIC.5** Switching either way keeps the reading place and focus (ICX-DEST.4).
- **ICX-CLASSIC.6** Switching to classic stops every running autoplay at once.
- **ICX-CLASSIC.7** The choice survives a reload and a new visit in the same browser. Placement, label, storage and
  scope: OPEN-18.

### ICX-HIDDEN — Hidden tab

Rule: autoplay pauses and resumes at rest. DEFAULT (DEC-6), pending Daniel: autoplay pauses when the tab is hidden.

- **ICX-HIDDEN.1** On `visibilitychange` to hidden, story and tour time stop advancing.
- **ICX-HIDDEN.2** After returning to visible, the page ends at rest on the same `dest`. Whether it finishes the
  paused run or goes straight to the rest frame: OPEN-19.

### ICX-KEY — Keyboard

Rule: arrows, PgUp/PgDn, Space/Shift+Space, Home/End → steps and jumps inside the pinned story. `aria-live` announces
the landed checkpoint name. Focus is not moved. DEFAULT (DEC-6), pending Daniel: `aria-live` announces keyboard
landings without moving focus.

- **ICX-KEY.1** Inside the pinned story: ArrowDown, PageDown, Space → step +1; ArrowUp, PageUp, Shift+Space →
  step −1; Home → jump to the first checkpoint; End → jump to the last pinned. (Left/Right: OPEN-20.)
- **ICX-KEY.2** On a keyboard landing, an `aria-live` region's text becomes the landed checkpoint's name
  (ICX-DEST); nothing is announced mid-transition.
- **ICX-KEY.3** `document.activeElement` is the same before and after any key step or jump.
- **ICX-KEY.4** A held key (`e.repeat`) steps at most once per `KEY_REPEAT_MS` (config).
- **ICX-KEY.5** At the last pinned, a forward step key (ArrowDown, PageDown, Space) passes natively
  (ICX-RELEASE.1). The ignore list and announcements for non-keyboard landings: OPEN-20.
- **ICX-KEY.6** Home and End always jump (vault Keyboard row; C0a S8 / ICX-SETTLE-8), from the pinned story and from
  below it (RELEASED): Home → the first checkpoint, End → the last pinned. End at `REST(last pinned)` is a jump to the
  checkpoint already landed (`distance == 0`): nothing moves, and End is not passed to the page. R1 §3.4's "End at the
  last beat passes through to the page end" is superseded (vault §3 supersedes R1–R3).

### ICX-BYPASS — Bypass

Rule: Ctrl/⌘ + wheel (zoom), pinch, and input inside dialogs or form fields are never intercepted.

- **ICX-BYPASS.1** A wheel event with `ctrlKey` or `metaKey` is never `preventDefault`ed and never steps.
- **ICX-BYPASS.2** A pinch (a second finger) never steps; a touch while pinch-zoomed pans (ICX-SETTLE-9).
- **ICX-BYPASS.3** Wheel, key and touch whose target is inside an open dialog, `input`, `textarea`, `select` or
  `[contenteditable]` are never `preventDefault`ed and never step.
- **ICX-BYPASS.4** Horizontal wheel and nested scroll containers: OPEN-21.

## ICX-SETTLE — settle rules from C0a

From `docs/cp-spike-verdict.md` ("Settle rules: the ICX patch for C0b"). The evidence cited is that file's verdict row
and its files under `scratch/cp-spike/evidence/<column>/` (C0a branch, final run on 801bae3). Constants are in
`docs/checkpoint-config.md` § "Settle (C0a)".

| Id | Rule | Test asserts | Evidence |
|---|---|---|---|
| **ICX-SETTLE-1** Acknowledge by position | `syncScroll(y)` rounds `y` to an integer and clamps it to the scroll range. If `abs(scrollY − y) ≤ 0.5` it does nothing and arms nothing. Otherwise it stores `pending = {y, until: now + ACK_MS}` and calls `scrollTo({top: y, behavior: "instant"})`. A `scroll` event with `abs(scrollY − pending.y) ≤ ACK_TOL` before `until` is ours. No boolean "next event is ours" flag. | Every landing's own scroll is acknowledged and never enters FREE; a no-op `syncScroll` arms nothing; source has no boolean ack flag. | verdict row R1 (PASS on all three proxies): `R1__*.json` |
| **ICX-SETTLE-2** FREE | Any other `scroll` event with `storyTop − 1 ≤ scrollY ≤ storyEnd + 1` enters FREE: the stage keeps its frame, and the rail previews `nearest = round((scrollY − storyTop) / BEAT_PX)`. Below `storyEnd + 1` it is RELEASED; above `storyTop − 1` it is the page above. | A foreign `scrollTo` inside the track: phase FREE, the stage frame unchanged, the highlight = `nearest`. Below: RELEASED. FREE is entered synchronously or within one frame of a foreign scroll (OPEN-23). | verdict rows R2, R3 (footnote 3) |
| **ICX-SETTLE-3** Settle trigger | With `onscrollend`: settle `SCROLLEND_GRACE` after a `scrollend`, only if no `scroll` came in that time. Without `scrollend`: settle after `SETTLE_IDLE` of no scroll events. Always: a `SETTLE_BACKSTOP` timer re-armed on every scroll event. Feature-detect and carry both paths. | A 1 s scroll stream gives exactly one settle (both paths, `?noscrollend` forcing the idle path); the backstop fires if neither does. | verdict rows R6 (`R6__*-nograce.json`: 30 settles without the grace), R7 (≈ 167 ms idle latency) |
| **ICX-SETTLE-4** Settle target | The nearest beat, as a jump (ICX-JUMP: ±1 = a step, ≥ 2 = a dip). Distance 0 (the nearest beat is the one already landed, the page merely scrolled off it): a re-alignment only — the page scrolls back to that beat's position, no dip, no content replay, no history write (unlike ICX-JUMP.0, the scroll position does move). The settle's own scroll is acknowledged (ICX-SETTLE-1). Re-entry from below: a FREE episode that began in RELEASED settles on the last pinned beat unless a scrollbar hold was seen in it; a new FREE episode within `REENTRY_STICKY_MS` of such a settle still counts as re-entry. | After a settle, no second FREE, and `phase == "rest"` on: the last pinned, if the FREE episode is a re-entry (it began in RELEASED with no scrollbar hold seen in it, or began within `REENTRY_STICKY_MS` of such a settle); otherwise `nearest`. A momentum stream from below lands on the last pinned and never walks back. | verdict row R8 (844×390 walked back to beat 7 before the rule) |
| **ICX-SETTLE-5** Settle cancellation | An intercepted gesture (wheel, key, touch) during FREE cancels the pending settle and counts from the beat nearest the current `scrollY`, not from the stage's frame. A further foreign scroll restarts the timers. If the settle wins the race, the outcome is the same beat. | Scrollbar drag then an immediate wheel or key: exactly one move, to `nearest ± 1`, whichever path ran. | verdict row R3 (Chromium 1440×900 intermittent, footnote 3; OPEN-23) |
| **ICX-SETTLE-6** Scrollbar hold | A capture-phase `mousedown` on `document` with `clientX ≥ documentElement.clientWidth` (or `clientY ≥ clientHeight`) means held: the settle waits. The hold ends on `mouseup`/`pointerup`, a `mousemove` with `buttons === 0`, window `blur`, or `HOLD_MAX`. Overlay scrollbars are invisible to this test; there the settle relies on ICX-SETTLE-3. | Classic scrollbar: no settle during a 1 s still hold; exactly one settle on release. | verdict row R5 (`R5__*-classicbar.json`, footnote 5) |
| **ICX-SETTLE-7** Resize / rotation | On every `resize`, re-measure at once (no debounce for the re-snap). `BEAT_PX = round(100svh − header)` in integer CSS px; the pin height is the same integer. Inside the story: `syncScroll(y_dest)`. RELEASED: keep the distance below `storyEnd`, from the last scroll position seen at the old viewport size, clamped to the new room below the story. Browser scroll corrections within `RESIZE_GRACE` after a real geometry change are re-snapped, never FREE. Page boot is not a geometry change. `overflow-anchor: none` on `html` and `body`. A height-only change where 100svh did not move is a no-op. Measure with offsets and `scrollY` only, never `getBoundingClientRect`. | Resize/rotate on a beat: the same beat, `scrollY` on its track position, no FREE. Below the story: distance kept (or clamped). Source has no `getBoundingClientRect` in the input/settle layer. | verdict row R4 (footnote 4) |
| **ICX-SETTLE-8** Release / re-entry | At `REST(last)`, a forward wheel, key or swipe is not intercepted. Wheel from below: events pass while `scrollY + dy ≥ storyEnd`; the event that would cross is prevented, `syncScroll(storyEnd)` lands `REST(last)`, and the rest of that gesture is swallowed. Keys from below pass natively (then ICX-SETTLE-2/4). Home and End always jump. | ICX-RELEASE.1/.2 plus: the crossing wheel event is prevented and the rest of that gesture steps nothing. | verdict row R2 (footnotes 1, 2) |
| **ICX-SETTLE-9** Bypass | Ctrl+wheel is never prevented (it scrolls natively, then FREE and settle). A touch while `visualViewport.scale > 1.01` pans and never steps. A second finger ends the touch with no step. | ICX-BYPASS.1/.2 plus: a Ctrl+wheel inside the track never steps. If the browser scrolls natively on it (as headless Chromium did in C0a), exactly one settle follows (via FREE); if it does not scroll, no settle. | verdict row R9 (footnote 8: iPhone partial) |
| **ICX-SETTLE-D1** Detector note | R1 §3.4 counts a notch gesture as "sustained" by any event. Fix: notch gestures also need `vNow ≥ SUSTAIN_K · peakSinceStep` to repeat (smooth gestures already did). | A smooth flick with a ≥ 50 px first delta and a decaying tail longer than `REPEAT_MS` steps once; a sustained notch spin still repeats every `REPEAT_MS`. | `S1__*-r1notch.json` (R1's rule fails), verdict row R2 (WebKit first run) |

## Not machine-testable (judged by a person)

- "The designed speed" and the story feel, including the Ride and Make→Look: Daniel judges on frame strips (DEC-8).
  ICX-STEP.2/.3 check only the numbers (the Ride's 1.45 s ± 0.1 s is DEFAULT (DEC-8), pending Daniel).
- "≤ 5 s where feasible": a test can check only the list of accepted exceptions (OPEN-2).
- "Visible" toggle: ICX-CLASSIC.4 checks it is in the viewport, not that people notice it.
- The device feel of every ICX-SETTLE row (C0a's last column, below): only the M1 device session can judge it.

## OPEN for Daniel

Decisions pending: DEC-4 (names, slugs), DEC-6 (autoplay accessibility), DEC-7 (classic view), DEC-8 (story feel).
Every "DEFAULT (DEC-n), pending Daniel" above changes with them. Daniel's approval is to be recorded in the Decision
log.

Questions the vault table leaves open:
- **OPEN-1** (ICX-CHECKPOINT.3) The tour's chapter list and slugs: does the tour get its own destination table
  (DEC-11, child F), and do its chips share the story's names?
- **OPEN-2** (ICX-STEP.2/.4) Today (R1 §2.6, computed): Make→Look transition 2.55 s with caption at 1.59 s;
  Yours→Price 1.54 s; Price→Note 1.77 s; phone Yours→End 1.58 s; Email (`chase`) content ≈ 6.03 s. Which are trimmed
  (C5) and which become named exceptions? The DEC-8 default names only Make→Look (≤ 1.6 s) and the Ride (1.45 s ± 0.1 s).
- **OPEN-3** (ICX-BACK.5) A back gesture at the first checkpoint: ignored, or passed natively (to the page above, and
  pull-to-refresh on touch)?
- **OPEN-4** (ICX-SIGNED.4, ICX-DIP.1) The ±1 arithmetic is settled (`o + 3` → one back gesture → `o + 2`). Open is
  the "decision time" for the dip rule while a transition runs: (a) at each gesture, so `dest = o + 3` during the seam
  `o → o + 1` starts a dip to `o + 3` at once and the back gesture lands in its fade-out (ICX-DIP.2, cut on `o + 2`);
  or (b) at the running transition's landing, so the seam rushes (≤ 0.6 s) to `o + 1`, lands, and then
  `distance = 1` → a step to `o + 2`. R1 §3.3 did (b) only when the rushed seam took ≤ 0.35 s, (a) otherwise.
- **OPEN-5** (ICX-SIGNED.1) Gestures that push `dest` past the first or the last pinned: clamp, or does a surplus
  forward gesture at the end count toward release?
- **OPEN-6** (ICX-SIGNED.5) What triggers the rush (≤ 0.6 s left): any extra gesture, or only one that changes
  `dest`? R1 had a 0.35 s seam rush and a 0.6 s content rush; the vault states one 0.6 s cap.
- **OPEN-7** (ICX-DIP.1) "Rest-entry": is it the target's content start (R1 §3.3 `S_dest`, so its content plays), as
  assumed here?
- **OPEN-8** (ICX-JUMP.3) A deep link on load: one dip from the page's first paint, or a dip-less start at the
  content? And reload: replay the content, or land still on the rest frame (R1 §3.5's policy)?
- **OPEN-9** (ICX-JUMP.5) A rail/menu jump to a row that is `native` in this mode (tablet "Price", phone "A note"):
  instant native anchor scroll? Does it push history like other jumps?
- **OPEN-10** (ICX-HIST.5) The first checkpoint's URL: `/` with no hash (R1 §3.5), or `/#new-invoice`?
- **OPEN-11** (ICX-HIST) Legacy hashes `#top`, `#how`, `#pricing`, `#download` (site.js `ANCHOR`) and the theme hashes
  `#dark`/`#light` (A5 reads them on load): resolved and replaced by the slug, or left alone?
- **OPEN-12** (ICX-HIST) History for FREE settles (R1: `replaceState`), for scroll-spy in native modes (write the hash
  or not), and the write time (on the `dest` decision, R1 §3.5, or on landing).
- **OPEN-13** (ICX-DEST anchor) Six sections have no id today (New invoice, Invoices, Dashboard, Email, Your data,
  A note). Does C3 add ids, and should every anchor id equal its slug so `/#<slug>` works with no JS? Today
  `#pricing`/`#download`/`#how` differ from the slugs `price`/`get-the-app`/`templates`.
- **OPEN-14** (ICX-DEST, ICX-RELEASE.3) Phone: `end` (the offer card) is pinned at the end of the track, but `price`
  and `note` are native and follow it in the document. What does `/#get-the-app` target on a phone, and what does the
  reader meet after release?
- **OPEN-15** (ICX-DEST modes) Today a short touch screen (coarse pointer, 100svh < 600 px, `SHORT_TOUCH` in site.js)
  goes calm. Does that stay a calm trigger? C0a probed 375×548 as pinned.
- **OPEN-16** (ICX-REST.1) Does RELEASED (below the pin, after a release) satisfy the invariant, as R1 §3.3 I1 had it?
- **OPEN-17** (ICX-HL.4) The scroll-spy threshold that makes a native section "current".
- **OPEN-18** (ICX-CLASSIC.7) The toggle's placement and label (NEW COPY for fe:claims), its storage
  (e.g. `localStorage`), whether it also appears on `/tour` and stops the tour's autoplay, and whether a
  reduced-motion visitor may switch the story on.
- **OPEN-19** (ICX-HIDDEN.2) "Resumes at rest": finish the paused run on return, or jump straight to the rest frame?
- **OPEN-20** (ICX-KEY) Left/Right arrows; R1 §3.4's ignore list (modifiers, `defaultPrevented`, Space on buttons/links); does `aria-live` also announce
  wheel/touch/rail landings?
- **OPEN-21** (ICX-BYPASS.4) R1 §3.4 also passes horizontal wheel (`|dx| > |dy|`) and events inside a nested scroll
  container that can still scroll. Adopt them as bypass rows?
- **OPEN-22** (ICX-NOPROG.3) DEC-6 asks fe:claims / a11y to confirm the classic toggle meets WCAG 2.2.2 with no Pause
  control.
- **OPEN-23** (ICX-SETTLE-2/5, C3) Chromium 1440×900 R3 was intermittent: FREE was sometimes not yet entered 40 ms after
  a foreign `scrollTo`. C3 must prove FREE is entered synchronously or within one frame under load.
- **OPEN-24** (ICX-SETTLE-3) Whether shipping Safari has `onscrollend` is UNVERIFIED-DEVICE; C3 carries both paths.
- **OPEN-25** (ICX-STEP.7) A forward gesture during a checkpoint's content (landed, before rest): the vault's step
  row starts from rest and its signed row covers only transitions. Options: (a) the content finishes at 1×, then the
  next transition plays; (b) the content rushes to its rest within ≤ 0.6 s, then the next transition; (c) the content
  is skipped (cut to its rest frame, or a dip), then the next transition. R1 §3.3 did (b) when ≤ 0.6 s of content was
  left, otherwise a dip to the rest frame.
- **OPEN-26** (ICX-JUMP.0) A jump at rest to the checkpoint already landed (a rail click on the current chapter, End at
  the last pinned). The vault's jump row says "±1 → step, otherwise dip" and is silent on distance 0. Default: nothing
  moves. Alternative: replay that checkpoint's content from its rest-entry (a dip, then content) — some readers click
  the current chapter to see it again.

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
