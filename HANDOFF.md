# Freelance Easy site — handoff to deploy Claude

## Framework

**Plain HTML / CSS / JS — no framework, no build step.** Three files load at runtime: `index.html`, `styles.css`, `script.js`. The folder _is_ the deployable artifact.

## Build command

**None.** Static HTML — just serve the folder.

## Build output directory

**The root folder _is_ the output.** Point Cloudflare Pages at the repo root.

## Local dev command

```bash
npx serve .
# or
python3 -m http.server 8000
```

Then `http://localhost:8000`. No watch step needed; refresh the browser after edits.

## Node version (if applicable)

**Not used.** No Node at build or runtime.

## External resources used

- **Google Fonts** — Montserrat, Lato, Playfair Display, loaded via `<link>` from `fonts.googleapis.com` / `fonts.gstatic.com`. Self-host swap is straightforward (download the .woff2 files into `assets/fonts/` and replace the `<link>` with `@font-face` blocks) but unnecessary for first-deploy.
- **No CDN images, no third-party scripts, no analytics yet** (analytics insertion point is marked with `<!-- ANALYTICS: ... -->` in every HTML `<head>`).

## URLs hardcoded (paste actual values)

- **Windows download:** `https://github.com/Freelance-Easy/InvoiceGenerator-releases/releases/latest/download/Freelance-Easy-Setup.exe` (stable filename — the version-suffixed URL pattern was retired in v0.2.5; in-app `/download/win` is the canonical entry point in `index.html`)
- **Mac placeholder approach:** `<button disabled aria-disabled="true">` with label "macOS · Coming soon · 4–7 weeks". Not a link — clicks do nothing. Visually a muted secondary button. When Mac ships, swap the `<button>` for an `<a href="...dmg">` and update `_redirects`.
- **GitHub releases link:** `https://github.com/Freelance-Easy/InvoiceGenerator-releases/releases`
- **Footer email:** `mailto:support@freelance-easy.com`
- **Privacy email:** `mailto:privacy@freelance-easy.com` (in `privacy.html`)
- **Privacy/Terms:** relative `/privacy` and `/terms` (placeholder pages exist; `_redirects` catches trailing-slash variants)

## Canonical-fact compliance

- **Legal entity in footer:** `Freelance Easy LLC` ✅
- **Copyright year:** `© 2026` ✅
- **Contact email:** `support@freelance-easy.com` ✅ (no personal Gmail anywhere)
- **Privacy email:** `privacy@freelance-easy.com` ✅
- **Color palette match:** `#080a0f` (bg-0), `#0d1117` (bg-1), `#2c7a7b` (accent), `#1a5456` (accent-strong) ✅ — declared as CSS custom properties at `:root` in `styles.css`.
- **Logo:** ✅ Swapped to the canonical FE-tile in v0.2.9-beta refresh (2026-05-05). `assets/logo.png` + `favicon.ico` carry the mark (the canonical source is InvoiceGenerator `electron/build/source-master.png`, 1024²); brand-mark spans in `index.html` header + footer reference `assets/logo.png` directly. `assets/logo.svg` was an Arial Black look-alike, never the real mark, and no page used it: removed 2026-10-05.
- **Fonts:** Montserrat (logo + headings), Lato (body), Playfair Display (italic accents). All canonical. ✅ Loaded via Google Fonts. _Note: there are also `Inter-Variable-*.woff2` and `PlayfairDisplay-*.ttf` files in `assets/fonts/` from an earlier iteration — they are currently unreferenced and can be deleted, or kept as a self-host fallback._
- **"7-day free trial" mentioned:** ✅ in hero CTA meta line ("7-day free trial · no card required") just below the Windows download button.
- **Local-first leads the hero:** ✅ Hero lede now opens with "**Freelance Easy** is local-first invoicing for freelancers. Your invoices, clients, and PDFs live on your own machine — not in someone else's cloud." and continues into the retainer angle.
- **Retainer angle:** ✅ Hero copy explicitly names "monthly retainers and ongoing client relationships." The "Recurring + reminders" feature card reinforces with "Set a monthly retainer once; the invoice generates itself on the day you choose, drafted and ready for you to send." (Local-first means we auto-generate, not auto-send.)
- **Beta/version pill:** ✅ "Closed beta · v0.2.9" pill at top of hero (bumped 2026-05-05 with the logo refresh).
- **No code-signing claims:** ✅ Audited — no "verified publisher", "signed", or trust-badge language anywhere.
- **Mac status:** ✅ Disabled button labeled "Coming soon · 4–7 weeks" (no broken link).

## Known TODOs / placeholders

1. ~~**Logo** — current F+E mark is my placeholder design. Swap in the canonical mark from the app~~ **DONE 2026-05-05** in v0.2.9-beta. New tile generated from a 1024×1024 source via tight alpha-bbox crop (~84% canvas fill) and downsized to 16/24/32/48/64/128/256 for the .ico, plus a 256 PNG and a hand-authored SVG. OG card was also updated to composite the new tile in the top-right.
2. **OG image** — ✅ Now composites the new FE-tile via `_paste_brand_tile()` in `scripts/generate-og-image.py`. The bg gradient + headline + wordmark composition is unchanged. Replace with a real screenshot composite later if a richer card is wanted.
3. **Privacy & Terms copy** — both pages have honest "real policy at public launch" placeholders. Real copy is pending.
4. **Mailing address** — none on the page. Canonical guidance is to leave it off until public launch (full Nashville address is being added then).
5. **Mac DMG wiring** — when Mac build ships, two changes:
   - In `index.html`, swap each `<button class="btn btn-secondary btn-soon" data-platform="mac">` for an `<a class="btn btn-secondary" href="...dmg" data-platform="mac">` with normal CTA label.
   - In `_redirects`, change `/download/mac` to point at the real `.dmg` URL.
6. **Analytics** — `<!-- ANALYTICS: insert tracking script here when ready -->` placeholder is in the `<head>` of every HTML file. Drop Plausible / Cloudflare Web Analytics there.
7. **Inter font files** — `assets/fonts/Inter-Variable-*.woff2` are vestigial (the page now uses Montserrat/Lato/Playfair via Google Fonts). Safe to delete, or keep as a no-network fallback if you ever want to self-host.

## Decisions worth flagging

- **Google Fonts via `<link>`** — not self-hosted. If you want strict zero-third-party loads (e.g. for stricter CSP), self-host: download Montserrat/Lato/Playfair Display .woff2 files, drop into `assets/fonts/`, and replace the Google `<link>` with `@font-face` blocks at the top of `styles.css`.
- **Hero visual is HTML/CSS, not a screenshot** — the dashboard mock in the hero is a pixel-crisp HTML/CSS recreation of the app's dashboard (themed via the same CSS tokens, scales perfectly, theme-aware). This was deliberate — no PNG to maintain, perfect dark/light parity. If you'd rather use real product screenshots, replace the `.hero-visual > .macwin` block in `index.html`.
- **`_redirects` and `_headers`** — Cloudflare Pages-specific. If the deploy target ever changes (Vercel, Netlify, S3+CloudFront), these need translation:
  - Netlify: `_redirects` works as-is, `_headers` works as-is.
  - Vercel: use `vercel.json` `redirects` and `headers`.
  - S3+CloudFront: redirects via CloudFront Functions, headers via Response Headers Policy.
- **Theme toggle uses `localStorage`** with key `fe-theme`. Pre-paint inline script in every HTML `<head>` reads this before stylesheet loads, so there's no FOUC on theme switch + reload.
- **Mac CTA is a real `<button disabled>`, not an anchor or div** — semantically correct and screen-reader-friendly. Has `aria-disabled="true"` and `title` for the 4–7 week timeline.

## Build verification

Confirmed: opened `index.html` in the preview, no console errors, page renders correctly in dark and light, theme toggle persists, Windows download link points at the canonical GitHub Releases URL, Mac button is non-clickable. Folder is ready to `git init && git push` to a new public repo.

The page targets modern evergreen browsers and degrades gracefully without JS (theme toggle and OS-aware CTA reorder go away; Windows download button still works).

---

## v2 landing (2026-09-20) — what changed and the publish gate

**Branch `feat/v2-landing` — the original gate was "do not merge until v0.2.18 is in staged rollout and the LicenseServer annual/no-trial/promo-code change is deployed", because the v2 copy ("your first invoice is free — no card", "$50 a year") describes that product. Superseded 2026-09-21: Daniel published with the offer matched to today's product instead; see "Published 2026-09-21" below for the interim strings and the flip-back.** Spec and plan live in the FREELANCE EASY VAULT: `04 - Future/Gate 0 — Lean Build Spec.md` §4 and `04 - Future/Landing v2 — Build Plan.md`.

- **Copy contract (decided):** "Make your first invoice in 60 seconds. Free — no card. $5 a month (or $50 a year) when you need more." Never: "nothing leaves your machine", "anonymous heartbeats", "7-day trial", "closed beta", "coming soon", "first 3 invoices", "signed" for Windows until the cert flip, invented quotes.
- **`index.html`** rewritten: hero with a real screenshot (`assets/screenshots/dashboard-{dark,light}.png`, theme-swapped by CSS), how-it-works, features, "Straight answers", pricing (Free / Yearly featured / Monthly), final CTA, footer with the current version line (bump at each release). Testimonials section deliberately absent until real, disclosed quotes exist.
- **Campaign pages:** `mac-audio.html` (`/mac-audio`, Google Demand Gen final URL — Mac button only, `noindex`) and `audio.html` (`/audio`, Reddit — both platforms + the Windows note, `noindex`). `audio.html` was generated from `mac-audio.html`; keep them in step.
- **`script.js` v2:** OS detection (mac / win / mobile / other), Windows-only SmartScreen note, Intel link (no download), phone → "Send this page to my computer" (Web Share), campaign download paths `/dl/<os>/<campaign>` from `?utm_campaign` or `<body data-campaign>`, Plausible events `Download Click {os, campaign, page}`, `Intel Notify`, `Share To Computer`.
- **`worker.js` + `wrangler.toml`:** a Worker now fronts the assets only to proxy Plausible (`/js/script.js`, `/api/event`); everything else goes to the ASSETS binding so `_redirects` / `_headers` are unchanged in behaviour. `SCRIPT_UPSTREAM` holds a placeholder until the Plausible site exists (`https://plausible.io/js/pa-<id>.js`); until then the script route 404s harmlessly. `.assetsignore` keeps worker.js, wrangler.toml, docs and scripts out of the upload.
- **`_redirects`:** `/dl/mac/*` and `/dl/win/*` (campaign splat) beside the existing `/download/*`; `/mac-audio/` and `/audio/` trailing-slash normalisation. **`_headers`:** screenshots cached a month; `X-Robots-Tag: noindex` on the campaign pages.
- **Legal:** `privacy.html` and `terms.html` are now real pages built from the vault's Privacy Policy Draft + the 2026-09-19 required additions, restricted to what the product verifiably does today (no data-export claim — that route is a stub; account closure by email; Sentry is server-side only). Two visible placeholders remain until Daniel supplies them: the publication date and the LLC mailing address.
- **Assets:** `scripts/capture-screenshots.py` (Playwright) regenerates the dashboard screenshots from the DEV app seeded with fictional demo data — run after any UI release. `scripts/generate-og-image.py` now finds the fonts on either machine and carries the v2 headline.
- **Local preview:** `python3 -m http.server 8765` from the repo root; `_redirects` does not apply locally, so download buttons 404 there — expected.

### v2.1 (2026-09-20, same branch) — after four design reviews

Daniel's verdict on v2.0: "looks so AI sloppy." Four independent GPT-6 Astra reviews (conversion, UI craft, copy/voice, trust — verbatim in the vault: `05 - Reference/GTM Research 2026-09/13-landing-v2-design-reviews.md`) converged; v2.1 applies them:

- **`styles.css` rewritten from scratch** (no dashboard-mock CSS, no card grids, no eyebrows; Playfair italic only in the H1 and wordmark; `--text-3` now ≥ 4.5:1). **Fonts self-hosted** in `assets/fonts/` (Lato, Montserrat, Playfair TTFs; Inter files removed) — every page makes zero third-party requests.
- **Hero** = offer + one download block left, **rendered invoice PDF** right (`assets/screenshots/invoice-day-rate.png`; full PDF at `assets/sample-invoice.pdf`).
- **One download component** (`[data-dl]`, see `script.js`) reused in hero / pricing / close: filled button for the detected OS, plain link for the other, 14 px compatibility text, "Google sign-in required", version · release files · install help; phones get "Share this page" / "Copy page link" with an `aria-live` status. `data-single-platform` keeps the Mac campaign page Mac-only.
- **Sections:** editor screenshot + three plain steps · dashboard + plain list · first-person maker note (**first name only until Daniel decides**; the note's wording is his to confirm) · one pricing panel (free first invoice → $5/mo → $50/yr) · "Before you download" `<dl>` · short close · two-row footer.
- **New `install.html`** (`/install`): Gatekeeper, SmartScreen incl. Smart App Control, data folder, uninstall. Added to the sitemap.
- **Legal:** privacy's Plausible paragraph matches Plausible's data policy (daily-rotating hash of IP + UA); narrowed claims; terms say "made and run by one person".
- **Demo data:** fictional persona **Jordan Wexcombe / jordan@example.com** (never a real name or email; renamed 2026-10-05, see the demo-data section at the end). `scripts/seed-demo-profile.py` seeds the account into a throwaway profile; `scripts/capture-screenshots.py --profile <that profile>` regenerates the dashboard images and rewrites the mock session's display name; it asserts the persona is on screen. Requires `playwright pymupdf pillow`.
- **`script.js`:** per-block wiring; events `Download Click {os, campaign, page, placement}`, `Compatibility Help Opened`, `Share To Computer {how}`; clipboard failure shows the URL.

Still to do before merging #6 (besides the publish gate): the two orange placeholders on `/privacy` and `/terms`, Daniel's read-through, his credit-line choice, and the Plausible script id in `worker.js`. *(2026-09-21: placeholders resolved, credit line stays first-name-only, Plausible deferred — see "Published 2026-09-21".)*

### v2.2 (2026-09-20, same branch) — "even more natural, easy, and not look AI slop"

Four more Astra reviews of v2.1 (tells / three first visits / line edit / layout — verbatim in the vault: `05 - Reference/GTM Research 2026-09/14-landing-v2.2-reviews.md`) agreed the loudest remaining tell was **repetition**, then the template skeleton, the italic-serif headline, and product shots too small to read. v2.2:

- **One download component, in the hero only.** Pricing has a text link back to it; the closing CTA section and the pricing copy of the block are gone; the version line moved to the footer; the maker is named once. Every fact is said once, where the reader needs it.
- **Headings flattened:** H1 in Montserrat only (Playfair italic stays in the wordmark), `text-wrap: balance`, ~48 px; section headings are short nouns without terminal periods ("Making an invoice", "Keeping track", "Pricing", "A few things to know", "A note from Daniel"). Doc-page H1s and the 404 lost the serif flourish too. No em dashes in page copy.
- **The product carries the page:** editor and dashboard run the full content width and **follow the theme** (`.shot-dark` / `.shot-light` pairs; the light page finally shows the light app). On phones `<picture>` swaps in detail crops (`editor-items-*.png`: the line items through the Qty column; `dashboard-attention-*.png`: the "Needs attention" panel).
- **Every image and the sample PDF come from ONE invoice** (INV1045, session day + kit fee) — the editor caption "The invoice above, open in the editor" is now literally true, and "Open the PDF" opens that invoice. `scripts/capture-screenshots.py` shoots the editor scrolled to its line items at a 1440×872 viewport (the scroller bottoms out with the heading 53 px down at 900), crops the phone details, and pins `HERO_CROP_HEIGHT` (1470 px, keep in step with the `<img height>`).
- **Copy:** three-step block → two paragraphs; bold-lead-in bullets → prose; pricing = two prices + renewal/cancel + "stays on your computer", payment mechanics in a `<details>`; Q&A = three real questions + one plain limits sentence; maker note = one paragraph + the support address, no signature. The "60 seconds" qualification sits in the lede ("After installing and signing in with Google, a new invoice is a client, a few line items and a PDF").
- **`script.js` fix:** `data-single-platform="mac"` now keeps the Mac campaign page's **button** on Mac for a Windows visitor (it previously switched the button to Windows next to text saying the page is Mac-only) while still showing that visitor the "Windows download is on the main page" note. Labels are "Download for Mac / Windows" on both the button and the link; copy-fallback text is plainer. `.dl-status:empty` no longer reserves space.
- **`scripts/derive-audio-page.py`** generates `audio.html` from `mac-audio.html` (each substitution must match exactly once; a leftover Mac-only phrase fails the run). Edit `mac-audio.html`, then run it.
- **OG image** regenerated to match (Montserrat headline, plain kicker, no pill).
- **Verified locally:** `check_states.py` (session scratchpad) asserted, per visitor OS × page: one download block, OS detection, campaign path (`?utm_campaign` sanitised to `[a-z0-9-]`), primary/alt/notes, the phone copy fallback (clipboard = page URL), the theme image swap, and zero non-local requests. Windows states were captured with a CDP `platform` override — a UA-only override still reports `MacIntel`, which is why v2.1's "Windows" screenshot was identical to the Mac one.

### v2.3 (2026-09-21, same branch) — "a simpler experience"

Daniel: "lets refine it into a simpler experience, have the video be a shorter gif that shows the flow without having to click play, and we dont need like step 1, 2, 3 to take so much damn space, we want to refine the site so it feels natural to understand how someone might use the app and why they want it." v2.3:

- **The loop.** "Making an invoice" is now a **silent auto-playing loop** (`<video autoplay muted loop playsinline>`, ~10.7 s, ~535 KB dark / ~620 KB light) cut from the same raw recording: navigation at 2×, the typing at 3×, the finished invoice at 1.5× and then **held 1.2 s** before the repeat (`SPEEDS` / `HOLD` in `scripts/encode-process-video.py`; the hold is a `tpad` placed *after* `fps=30`, because `setpts` leaves the frame rate unknown and `tpad` then pads nothing). A literal `.gif` at this size would have been 10 MB+. The poster is the loop's first frame, so autoplay doesn't flash. The caption says "Sped up" and links the **real-time file** (`make-an-invoice-<theme>.mp4`, 24.8 s) for the honest pace.
- **Two recordings, one per app theme.** `capture-process.py --video … --theme light` records the same flow in the light app (the pass normalises the app's remembered theme first). The encoder writes a set per theme: `assets/video/make-an-invoice-loop-{dark,light}.mp4`, `…-loop-{dark,light}-poster.jpg`, `make-an-invoice-{dark,light}.mp4`. `script.js` swaps `-dark`/`-light` in the video's source, poster and the real-time link with the page theme (`syncDemoTheme`); the HTML carries the dark set for no-JS. **Reduced motion:** no autoplay, poster + native controls. **Autoplay refused** (iOS Low Power Mode): the controls appear, so the poster is never a dead end (an `AbortError` from a `load()` interrupting `play()` is ignored). The "Demo Played" event is gone: with autoplay it would count everyone.
- **Steps collapsed.** The three full-width frames (`create-*.png`, twelve files) are deleted; under the loop sit three one-line moments in a row under a hairline (`.process`: teal numeral, bold lead-in from the app's own labels — New invoice / Line items / Create Invoice — one sentence each; single column under 900 px). The stills stage of `capture-process.py` is kept but unused.
- **Story of use.** Each section opens with a one-line lede naming the moment: "The job's done and it's time to bill it…" (`#how`), "An invoice is outstanding until the money arrives and you mark it paid…" (`#track`; statuses per the app: outstanding / paid, overdue derived, marked paid from the invoice page). "Keeping track" prose shortened to the follow-up email, the recurring invoice and the PDF import. Hero, pricing, Q&A and the maker note unchanged. Page height at 1440 px: 4139 px (the layout-pass build measured 5570).
- **Verified locally:** `check_states.py` — the earlier matrix plus: the loop is muted/loop/playsinline and playing without controls by default; paused with controls and no `autoplay` under `reduced_motion="reduce"`; a light-theme visitor gets the light source/poster/link, the toggle brings the dark set back playing; all six video files resolve. PII scan clean (the recordings show only the persona). The app's number counter climbed again: the dark loop shows INV1055, the light one INV1056 — cosmetic.
- **Shown on the Cloudflare branch preview** (`https://feat-v2-landing-freelance-easy-site.lively-breeze-6443.workers.dev`, rebuilt on every push), not localhost. Production still serves v1 until the PRs merge.

### v2.4 (2026-09-21, same branch) — the framing: for freelancers, the advantages, the niche as provenance

Daniel: "i feel like the framing and presentation on the site should be more focused on the vision that i have and the info you have in 'a note from daniel' … if we're highly targetting users in a certain market or that might be interested in the local hosting, super cheap price, and niche usecase of a straightforward software like this, then we want to lean into that brand yeah?" then "i want it focused on freelancers but also on the advantages of my program and the niche case its in as well." So: freelancer-first, the advantages carried up front, the audio niche as the credible origin rather than the audience.

- **Hero lede** now says who it's for and why: "A desktop invoicing app for freelancers, on Mac and Windows. Your clients and invoices live in a folder on your own computer, not on a web app's servers. Made by a mix engineer who bills with it; it works for any freelance job." (The install/sign-in qualification moved to the close; the loop caption qualifies the 60 seconds.)
- **The close** is now **"Why it's built this way"**: three statements in the `.qa` rows (*It lives on your computer.* / *It does one thing.* / *One person makes it.*), absorbing the three questions and the limits paragraph (`.limits` removed), beside **A note from Daniel**, which adds "Nothing in it is specific to audio. It's just written by someone who bills freelance work." Still his to confirm.
- **Mac page:** same close with Mac wording; its lede is the audio-flavoured version ("A desktop invoicing app for audio work, on your Mac: day rates, kit fees, per-song mixes…"). `derive-audio-page.py` substitutions updated (three new, one changed); `audio.html` regenerated.
- **`_headers`:** `styles.css` / `script.js` now `max-age=0, must-revalidate` (ETag 304s). Found the hard way: Daniel's tab had reused the hour-old stylesheet against the new v2.3 HTML, so the three lines rendered stacked until a hard reload.
- Verified with the local matrix + PII scan; page height 4273 px.
- **Chrome and occluded windows:** a page whose window is fully behind another app reports `visibilityState: hidden`, and Chrome defers the autoplay video's load entirely (`loadstart` → `stalled`, no bytes); it loads and plays when the window comes forward. Not a site bug: the loop autoplays from the preview in a visible browser (headless Playwright: dark t=3.5 s, light t=3.7 s).

### v2.5 (2026-09-21, same branch) — "$5 for everything, you're in control", a polish pass, two reviews

Daniel: "i feel like somewhere we should emphasize that its 5 dollars a month for ALL features, nothing paywalled, unlimited invoice. they are in control they have the power … do a strong revision of that sentiment with our previous sentiment as well and honestly do some tasteful redesign to make the website even more pleasurable to look at and interact with … have /astra do a review and /sol do a review as well."

**Built (`6990826`), then reviewed by GPT-6 Astra (design / interaction / copy) and GPT-5.6 Sol (code / a11y), findings applied (`aa73a2a`).** The reviews and the reconciliation table are in the vault (`05 - Reference/GTM Research 2026-09/15-landing-v2.5-reviews.md`).

- **Copy.** Offer: "Your first invoice is free. No card, no time limit. After that, $5 a month or $50 a year includes every feature and unlimited invoices." (Astra's sentence.) Lede: three short sentences. "Pricing" → **"One price"**: the two prices first, then "Every feature. Unlimited invoices and clients. Nothing paywalled.", "Your first invoice is free: no card, no time limit. In US dollars, for one person, on Mac or Windows.", an **Included** list of six evened labels, one-sentence terms. The close → **"You're in control"**: three one-sentence statements (Your files stay with you / You decide what gets sent / Clients pay you directly) in the `.qa` rows, the Google sign-in, subscription check, limits and privacy@ line in a `<details>` "Sign-in and account details"; the price argument is made once, in the band. Steps and the "Making an invoice" lede shortened; "Keeping track" prose says the follow-up/recurring facts once (the control statements say what waits for you).
- **The template picker.** `scripts/build-hero-collage.py compose` now writes **four** stacks, `invoice-stack-{modern,bold,classic,minimal}.png` (1398×1719, the front sheet at the same y in every variant: `BAND` per template, `SLOTS` per position). The hero's `.stack-link` holds two absolutely positioned layers (`aspect-ratio: 1398/1719`) that crossfade; `wireStack()` in `script.js` turns the caption's PDF links into `role="button"` picks (Enter and Space), queues a pick made mid-load (last wins), updates the image link and the "Open the <template> PDF" link, and preloads the other three stacks on idle only on fine-pointer, non-data-saver connections. Without JS the names are the four PDF links and the Open link is hidden.
- **The loop's Pause / Play.** HTML: `<video muted loop playsinline controls preload="none" poster=…>` (no `autoplay`), so no-JS gets a poster with native controls and a light-theme visitor never fetches the dark file. `wireDemo()` picks the theme's set, removes the native controls, starts the loop unless `prefers-reduced-motion` (then poster + native controls), shows the caption's `[data-demo-toggle]` button, keeps a visitor's pause across a theme switch (`demoPausedByVisitor`; the toggle handler calls `restartDemos(syncDemoTheme(next))`), listens for the motion preference changing, and brings the native controls back if `play()` is refused.
- **Header.** Sticky, translucent (`color-mix` over `var(--bg-0)` with a plain fallback), `backdrop-filter`, a hairline once scrolled (`.is-stuck` via an `IntersectionObserver` on `[data-header-sentinel]`, no scroll listener); `html { scroll-padding-top: 80px }` so `#pricing` / `#download` land below it; the wordmark text hides below 360 px.
- **Polish.** Soft tinted shadows under `.figure img` and the loop; `.btn:hover` lift; the theme toggle fades (`body`, `.band`, images); all transforms and transitions off under reduced motion.
- **Bytes.** Fonts converted to WOFF2 by `scripts/convert-fonts.py` (733 → 261 KB; the TTFs are gone). `_headers`: `assets/screenshots/*` and `assets/video/*` a day with revalidation (their names don't change across refinements), the rest of `assets/*` a month, fonts a year, `styles.css` / `script.js` revalidate every load.
- **Also from the reviews:** dashboard alt text true for both the full image and the phone crop; Web Share failure falls back to the copy path (a cancelled share sheet stays silent).
- **Deferred:** a phone-specific cut of the loop (Astra: 720×900 crops of the client, line items and preview in sequence; the desktop recording is small on a phone); a real Playfair Display italic for the wordmark (today it's a synthetic italic of the Regular; needs the OFL font fetched from Google's GitHub — Daniel's OK).
- **Verified locally** (`check_states.py`): the OS × page matrix; the loop playing without native controls by default, paused with native controls and the button hidden under reduced motion, the button pausing and relabelling, the pause surviving a theme switch, Play resuming the light file; the picker's default, Bold, Minimal, rapid Modern→Classic ending on Classic, Space on Bold; the four stack images 200; the header not stuck at top and stuck after a scroll; zero non-local requests. PII scan clean. Page height at 1440 px: 4106.

### v2.6 (2026-09-21, same branch) — the hero pile is real sheets that shuffle

Daniel: "four templates, more to come" and "make the invoice carousel more high fidelity and nicely animated and stuff. so its not like flicking between diff pictures and stuff we want high fidelity website please."

- **The pile.** No more stack PNGs. `scripts/build-hero-collage.py sheets` rasters the top of each template's PDF to `assets/screenshots/sheet-<style>.webp` (1120×897, 27–39 KB each, no edge or shadow) and prints the pile geometry. In the HTML each template is an `<a class="sheet">` holding its image, positioned by inline custom properties: `--x` / `--y` in percent of the pile's width (the `.stack` is a `container-type: inline-size` box, so the values are `cqw`), `--r` degrees, `--z` order. The geometry is the same as before: the front sheet at y 56.098, a sheet behind rises by its template's **band** (modern 15.244, bold 27.439, classic/minimal 13.415), the slot sets x (0 / 4.878 / 9.756 / 14.634) and tilt (0 / 1.1 / −1.3 / 0.8). `.stack { aspect-ratio: 1312 / 1665 }` reserves the height. Edges (`1px rgba(20,20,24,.16)`) and shadows are CSS, so the light theme gets real hairlines.
- **The shuffle.** `wireStack()` in `script.js` holds the same geometry (`PILE`); `arrange(front)` sets the four sheets' properties and the sheets glide (`transform` and `box-shadow` transition, 620 ms, `cubic-bezier(.3,.7,.15,1)`). The chosen sheet gets `.is-moving` for 700 ms: `z-index: 9` so it rides above the pile, a scale 1 → 1.025 → 1 keyframe on its image (the lift), a deeper shadow. Picks come from the names under the pile (Enter / Space, `aria-pressed`) **or a click on a sheet in the pile**; **a click on the front sheet flips to the next template** (Daniel, `41bf681`: "when you click on the front invoice i dont want it to go to the pdf page bc they are going to be clicking it a lot"), so the PDF is only ever the "Open the <template> PDF" link (and, without JS, the sheets' hrefs). Sheets behind are `aria-hidden` with empty alt until they come forward; the front sheet carries the alt and an aria-label. Rapid picks re-arrange immediately (nothing to load). Under `prefers-reduced-motion` the global rule kills the transitions, so the pile just re-lays. Without JS the pile is the HTML's Modern-front layout and the names are the PDF links.
- **Copy:** "One invoice, the four templates so far." The Included list: "Four templates, with more to come" and "Your logo and accent color" (seven items now).
- **Assets:** `invoice-stack-*.png` and `invoice-<style>.png` removed (1.4 MB → 131 KB for the hero).
- **Verified locally:** the matrix plus: four sheets, Modern in front at the front y with `z-index` 4 and the others hidden to AT; Bold via the name (link, label, alt, geometry follow, nothing navigates); Classic via a click on its sheet; rapid Modern→Minimal ends on Minimal; Space on Bold; the four WebP files 200. Frames of the shuffle at 0 / 160 / 320 / 480 / 700 ms looked at in both themes (session scratchpad `shoot_shuffle.py`). PII scan clean.

### v2.7 (2026-09-21, same branch) — the deck: fixed slots, a pull choreography, two reviews

Daniel, on v2.6: "think deeply on how to improve the UX of the carousel it feels super sloppy rn, have /astra and /sol review as well." The diagnosis: the pile's silhouette changed on every pick (per-template bands), all four sheets moved at once (a re-sort to canonical order), stacking order swapped mid-flight, and tilted rasters aliased. **Built (`bad5512`), then reviewed by Astra (motion) and Sol (code/a11y), findings applied (`08121fa`);** the reviews and the reconciliation are in the vault (`05 - Reference/GTM Research 2026-09/16-landing-deck-reviews.md`). Astra's proposal to replace the deck with a stationary crossfade viewer was declined (it is the image swap Daniel rejected); its complaint about the t=0 pop is fixed inside the model.

- **The geometry (final).** Four fixed slots, front → back: x `0 / 4.878 / 9.756 / 14.634`, y `36 / 24 / 12 / 0`, scale `1 / .985 / .97 / .955` (percent of the deck's width; the `.stack` is a `container-type: inline-size` box with `aspect-ratio: 1312 / 1400`, so the values are `cqw`), `transform-origin: 0 0`, no tilt. Every sheet behind shows a **12 %** band of its top. The silhouette never changes; a pick moves sheets between slots. The same numbers live in the sheets' inline `--x/--y/--s/--z` (Modern-front, for no-JS), `styles.css` and `DECK` in `script.js`; `build-hero-collage.py sheets` only emits the rasters.
- **The pull.** `pull(k)`: the sheet in slot k gets `--from` (its slot), `--mid` (4 % sideways, 45 % of the way down, +1.2 % scale) and `--to` (the front slot), plus `--hidden` (the fraction of it below its visible band, ≈ 82 %); `sheet-pull` (440 ms, `cubic-bezier(.22,.61,.36,1)`) animates `transform` through those and `clip-path` from `inset(0 0 var(--hidden) 0)` to `inset(0)` by 55 %, so the sheet **emerges** from under the ones ahead rather than popping over them; it has `z-index: 9` and a deeper shadow while `.is-moving`. Only the sheets that were ahead of it shift back one slot (`transition` 340 ms, delayed 70 ms by `.stack.is-shuffling`). Sheets behind it don't move. **One pull at a time:** a pick made during a pull is `pending` and runs on `animationend` (fallback timer 520 ms); the latest wins. Reduced motion commits synchronously.
- **Navigation.** `next()` / `previous()` follow `TEMPLATES` (Modern → Bold → Classic → Minimal) whatever the deck's arrangement. Front click = next; a sideways drag on the deck (one primary tracked pointer, horizontal lock after 12 px, the front sheet follows the finger via `--drag-x` ×0.35 capped ±32 px, commit at 40 px: left = next, right = previous; the following click is swallowed; `draggable=false` + `dragstart` cancelled; `pointercancel`/`lostpointercapture` clear state but keep `downSheet` for the click that follows a plain tap, because pointer capture retargets that click to the deck); ArrowRight/Down/Space = next, ArrowLeft/Up = previous on the focused front sheet, **focus moving to the new front**; the names (Enter/Space, `aria-pressed`, marked by colour + accent underline only, no weight change) and a click on any sheet in the deck pick directly.
- **Lift and hover.** `translate: var(--drag-x, 0) var(--lift-y, 0)` on the whole `.sheet` (paper, edge and shadow together): hover `-4px` (front `-2px`); reduced motion zeroes it. `will-change` only while shuffling.
- **AT and copy.** Front sheet `role="button"` "<Template> template in front. Show the next template."; the other three `aria-hidden` + `tabindex=-1` + empty alt; a visually-hidden polite status "Bold template, 2 of 4"; the picker `role="group"` "Invoice template"; a JS-only hint in the caption: "Click the invoice to flip through them, or pick one:". Caption: "One invoice, the four templates so far. The client is fictional."
- **Also this round:** the Included list flows in two CSS columns (a wrapped item no longer opens a gap beside it; `82883f3`, Daniel's screenshot in `references/2026-09-21-included-list-spacing.png`) and says "Four templates, more to come".
- **Verified locally** (`check_states.py`): the matrix plus the deck: four sheets, Modern at the front slot; Bold via the name with only the sheets ahead shifting; Classic via a click on its sheet; rapid Modern→Minimal ends on Minimal, settled; Space on Bold; the front click shows the next in order and four clicks come round; the status text; a drag left = next, right = previous; ArrowRight/ArrowLeft with focus on the new front; the hint shown; the four WebP files 200. Frames of the pull at 0 / 60 / 130 / 200 / 300 / 520 ms looked at in both themes (`shoot_shuffle.py`). PII scan clean.
- **Deferred / open:** a phone-specific cut of the loop; a real Playfair italic (Daniel's OK to fetch); Astra's stationary-viewer alternative, on record in the review file if the deck ever needs a fallback.

### 2026-09-22 — the flip target changed: a free trial, not "first invoice free"

Daniel (2026-09-22): "sure 7 days everything, then free plan that lets them send one more invoice". v0.2.18 now gives a never-subscribed account **every feature for seven days, no card** (the LicenseServer starts one trial per account, never resettable), then the free plan with **one more invoice**; $5 a month or $50 a year to keep going. So the flip-back in the table below is **superseded**: the strings to publish are on the local branch **`feat/free-trial-copy`** (hero offer, `$50 a year` in `.bill`, pricing note, meta/OG/JSON-LD, Terms §2 "Free trial" + "Paid ($5 a month or $50 a year)", Terms §5 monthly-or-yearly + the switch bullet, Privacy §2 trial start + plan/attribution + the signed-out bug report + "the free plan is counted on your own computer", Privacy §4 tips/how-you-heard; `audio.html` regenerated). **Publish it at Mark Latest of v0.2.18, not before** (the live app still has the card trial), and set both legal pages' "Last updated" to that day. Not pushed: the repo is public and `main` deploys.

### Published 2026-09-21 — with the offer matched to today's product (the flip-back is one commit)

Daniel: "lets push the website update live, make sure that all the links and connections and everything works." The v2.7 offer ("first invoice free, no card, $5 a month or $50 a year", promotion codes, wallets at checkout) describes v0.2.18 + the LicenseServer Gate 0 change, neither built; the app as released (0.2.17-beta) redirects anyone without an active subscription to `/inactive` → Stripe Checkout with `trial_period_days: 7` (a card is collected), one monthly price, no `allow_promotion_codes`. Daniel chose to **publish now with the copy matched to the product as it is**, and to flip it back the day the product catches up.

- **Interim copy (this commit) — every string, so the flip-back is mechanical:**

  | Where | Live today (interim) | Flip back to (v2.7, when v0.2.18 + the LS PR are deployed) |
  |---|---|---|
  | `index.html` + `mac-audio.html` hero `.offer` | Free for seven days. After that, $5 a month includes every feature and unlimited invoices. | Your first invoice is free. No card, no time limit. After that, $5 a month or $50 a year includes every feature and unlimited invoices. |
  | `.bill` | `$5 a month` only | add `<li><span class="price">$50</span><span class="per">a year</span></li>` |
  | `.pricing-note` | The first seven days are free. Stripe asks for a card when you start, and nothing is charged if you cancel before the trial ends. In US dollars… | Your first invoice is free: no card, no time limit. In US dollars… |
  | Payment details `<details>` | ~~interim~~ **restored 2026-09-21 (same day):** "Checkout is handled by Stripe: card, Apple Pay, Google Pay or Link. There's a field for promotion codes at checkout. Stripe keeps your card details; we never see them." — Google Pay was enabled in the Dashboard and the LicenseServer (PR #30) turned on `allow_promotion_codes` for every Checkout. Mac page says "card, Apple Pay or Link"; the derive script adds Google Pay. Nothing to flip here. | — |
  | `<meta name=description>`, `og:description`, `twitter:description` | Free for seven days, then $5 a month for every feature… | Free, no card. $5 a month or $50 a year when you need more… |
  | JSON-LD `offers` | one Offer, 5.00 USD "Monthly, after a seven-day free trial" | three Offers: 0 "First invoice free, no card", 5.00 Monthly, 50.00 Yearly; description "The first invoice is free; $5 a month or $50 a year after that." |
  | `terms.html` §2 | Trial: the first seven days after you start a subscription are free… / Paid ($5 a month) | Free: your first invoice — make it, send it, get paid. No card, no time limit. / Paid ($5 a month or $50 a year) |
  | `terms.html` §5 | renew every month; no yearly-switch bullet; promotion-code bullet **restored 2026-09-21** | "monthly or yearly depending on the plan you chose"; "Switching from monthly to yearly is billed at the time of the switch." (the Customer Portal now allows the switch, prorated, charged immediately) |
  | `privacy.html` §2 "On our servers" | The date your account was created | The plan you chose, which plan the app showed you first, the week your account was created, and — if you answered it — how you heard about us (from a fixed list)… (**only once the LS PR stores them**) |
  | `privacy.html` §2 last paragraph / §4 | no "free tier is counted on your own computer"; tips "only if you opt in (nothing of the kind is sent today)"; channels = campaign parameters only | "— the free tier is counted on your own computer."; "only if you ticked the box at sign-in (it is unticked by default)"; "The optional 'how did you hear about us' answer and the campaign parameters…" (**once Checkout's `consent_collection` and the question exist**) |
  | `scripts/derive-audio-page.py` | the meta-description substitution reads "Free for seven days, then $5 a month" (the Stripe-wallets substitution is back) | restore the meta-description substitution |

- **Legal placeholders resolved:** "Last updated: September 21, 2026 · Effective the same day." on both pages; the mailing-address line **removed** (Daniel's call: emails only; nothing about the LLC's address is published). `.doc .placeholder` CSS removed with it.
- **Analytics:** Daniel chose "later" for Plausible. `worker.js` answers `/js/script.js` with an empty script (200, 5-minute cache) while `SCRIPT_UPSTREAM` still says `REPLACE_ME`, so no page logs a console error and no event leaves the site. To turn it on: create the Plausible site, put its `pa-<id>.js` URL in `SCRIPT_UPSTREAM`, redeploy.
- **Verified before merging** (`scratchpad/site_review/check_links.py <origin>`, the publish sweep): every page 200; every href/src/srcset/poster/CSS `url()` resolves; `/download/{mac,win}` and `/dl/{mac,win}/*` → GitHub "latest" → `Freelance-Easy.dmg` 153.6 MB / `Freelance-Easy-Setup.exe` 134.3 MB (v0.2.17-beta); `/download`, `/releases`, the four trailing-slash 301s; `X-Robots-Tag: noindex` on `/audio` and `/mac-audio` only; cache and security headers; branded 404; sitemap URLs; robots; no third-party request on any page; JSON-LD parses; `worker.js`/`wrangler.toml`/docs/scripts/`references/` not served (`references/` was, until this round's `.assetsignore` fix). Product claims checked against the code: card at checkout (`billing.py` `mode="subscription"`, `trial_period_days: 7`, no `payment_method_collection`), monthly only (`STRIPE_PRICE_ID`), 7-day offline grace (`session.py` `DEFAULT_GRACE_DAYS`), Customer Portal from Settings (`/billing/portal`), Windows installer unsigned (`releases/0.2.16-beta.json` `"signed": false`; 0.2.17 has no log on this machine), Mac signed and notarized (since v0.2.15).

#### Layout pass: rhythm (same day, follow-up)

Daniel: "make the layout even nicer, do deep thinking on how to best present the product and then do it." The story order stayed (deliverable → process → tracking → price → caveats → maker); what changed is the page's rhythm, which had become five dark app windows in the same text-left/image-right shape followed by three stacked text blocks. Now: **hero** has one bold block (the H1; the offer is a 20 px regular line; the kicker folded into the lede, so the headline sits higher against the stack) · **Making an invoice** leads with the recording (still opt-in) and the three steps follow as the reference, with 26 px numerals · **Keeping track** stays the one full-width screen · **Pricing** is a split (prices large on the left, terms on the right) on a full-bleed **band** (`.band`, `--bg-1`, hairlines; same theme, one shade up) · **A few things to know** and **A note from Daniel** sit side by side (`.two-col`, 1.35fr/1fr) so the page ends in two columns instead of three stacked text sections. Single column under 900 px. Same structure on `mac-audio.html` (its kicker stays: it is the ad's message match); `audio.html` regenerated.

#### Hero = one invoice in the four templates, stacked (same day, follow-up)

Daniel: "i want the first invoice picture to be a cooler collage of different styles and such." The hero image is now `assets/screenshots/invoice-stack.png`: the hero invoice (INV1045) rendered by the app's own `pdf_gen` in all four templates with four muted accents (Modern teal `#2c7a7b` in front; Bold navy `#2b4a6f`; Classic forest `#2f5d50`; Minimal graphite `#4a4f57`), composed as a paper cascade on a transparent canvas. `scripts/build-hero-collage.py render` (run with the **InvoiceGenerator venv**, it imports the app's `db`/`pdf_gen` against the dev profile) writes `assets/samples/invoice-<style>.pdf`; `… compose` (pymupdf + pillow) writes the stack and the per-style top crops `invoice-<style>.png`. Each sheet behind the front one rises by a band sized to that template's signature (Bold 360 px so its navy title and table header show; Classic and Minimal 176 px), side-steps stay inside the page's own right margin so the right edges are blank paper, tilts are ±1°. The image links to the Modern PDF; the caption links all four. `invoice-day-rate.png` and `assets/sample-invoice.pdf` are gone; `capture-screenshots.py` now produces only the dashboard shots.

#### "Making an invoice" = the real creation flow (same day, follow-up)

Daniel: "present a better representation of the invoice creation process." The single editor screenshot became **three frames of a real invoice being made** plus **a 25-second screen recording**, all captured by `scripts/capture-process.py`, which drives the actual UI as the fictional persona (new invoice → title → Net 30 → client → two line items → note → Create), screenshots each stage in both themes with phone crops, then **deletes the invoice** via `POST /invoices/<id>/delete` so the demo data is unchanged (19 invoices). `--video` records one dark pass with a drawn cursor and typing-speed input (Playwright records no cursor) and writes `marks.json`; `scripts/encode-process-video.py` trims and encodes it to `assets/video/make-an-invoice.mp4` (H.264 1280×800, ~770 KB, 25 s) and a poster from the line-items moment. The page shows the recording as **poster + native controls, no autoplay** (`preload="none"`); `script.js` counts a "Demo Played" event once. The old `editor*.png` assets are gone; `capture-screenshots.py` now produces only the dashboard shots, the hero crop and the sample PDF. Notes: use `http://localhost:50506` (the app redirects `127.0.0.1` → `localhost`, which turns the delete POST into a GET; 50506 is the dev app's port since 2026-09-25, and both capture scripts refuse `:50505`, the installed app); the app's `next_invoice_number` counter still advances after the delete, so the number in the frames (INV1054) and in the video (INV1055) differ by one and will climb on every re-capture — cosmetic. Observed in the app while capturing: the new-invoice form's Payment Terms control shows "On Receipt" while the Due field is pre-filled +30 days (the script picks Net 30 explicitly).

### 2026-09-29 — privacy: "On our servers" matched to what the LicenseServer keeps (branch `fix/privacy-data-list`, local only)

The live `/privacy` (byte-identical to `main`) listed less than the LicenseServer stores: the Gate 0 columns and ledgers went live on the server while the privacy rows of the flip-back table above waited for the offer flip. This branch changes **`privacy.html` only** (and this entry), cut from `main`, so it can ship without the flip. Checked against LicenseServer `main` (`c17c026`) and InvoiceGenerator `v0.2.19-beta` (every app file cited is identical on `dev`).

- **Added to §2 "On our servers":** the trial start (`users.trial_started_at`); how you heard, the plan shown first and the tips opt-in with its date (`_GATE0_COLUMNS`, `set_user_attribution` — they arrive only with `/subscribe`, the first answer wins, an unticked box sends nothing); the promotion code (`set_user_promotion_code`) and the Stripe subscription id; the `checkout_starts` and `paid_events` ledgers; what a bug report holds (`BugReportSubmit` / `AnonymousBugReportSubmit` plus the two lines `routes/bug_report.py` appends — `data_root_health.bug_report_line`, `signin_counters_line`; the signed-out cap keys on the IP in memory only, `_sender_address`).
- **Corrected:** the server's own log carries the account id (`check-license ok user_id=…` and the sign-in, checkout and payment INFO lines); Sentry strips email and name but not `user_id` or request bodies (`_PII_FIELDS` / `_is_pii_key`), so "personal information removed" overclaimed; the app checks at launch and after sign-in, plus the `/inactive` and `/activating` pollers — not "once each time it starts"; Stripe receives the email (`stripe.Customer.create`) and the checkout `metadata`; §4's charge and channels lines; the TL;DR.
- **Against `feat/free-trial-copy`:** it edits the same `privacy.html` lines and will conflict. This branch covers its privacy changes except two offer strings ("the free plan is counted on your own computer" and its tips sentence), so when it lands keep this `privacy.html` and decide those two then. Of the flip-back table above, the §2 `privacy.html` row is done here, and the channels part of the next row.
- **Before publishing:** set "Last updated" to the publish day. Not pushed: the repo is public and `main` deploys.

### 2026-09-29 — freshness pass: the trial copy published, every claim re-checked (branch `fix/site-freshness-2026-09`)

Daniel: "on the live site not being updated, i think that we should definitely update the site, so no information is stale". Checked against InvoiceGenerator `main` `a6b32be` (v0.2.19-beta, Latest since 2026-09-27), LicenseServer `main` `c17c026`, and the live site. The code wins over any note.

- **Both local branches merged:** `feat/free-trial-copy` (the 2026-09-22 flip above: seven days of every feature, no card, then one more invoice; $5 a month or $50 a year) and `fix/privacy-data-list`. In the `privacy.html` conflict the privacy branch's list won; "the free plan is counted on your own computer" was kept (`session.py`, `free_tier.py`: the count never leaves the computer); the tips line keeps the one-click-unsubscribe promise and says the box is on the app's setup page, unticked (`onboarding_name.html`). Both legal pages are dated September 29, 2026.
- **Trial length in production:** `FREE_TRIAL_DAYS` is not declared in LicenseServer `.railway/railway.ts` and is not set on the production `web` service (`railway variables` filtered to that one key, 2026-09-29), so the code default applies: 7 (`config._trial_days`).
- **Corrected:** the version line (v0.2.19-beta); "An overdue invoice comes with a drafted follow-up email" / "Email and drafted follow-ups" / "overdue follow-ups are drafted" (no such draft exists: the only drafts are recurring ones and the one you compose; the dashboard flags invoices due within three days); `/privacy` "SMTP password … stored encrypted" (it is plaintext in the local SQLite, `db/types.py`); `/privacy` said the site uses Plausible (it doesn't yet, see below); the polling sentence; Terms §6 without "grace period"; Terms §12's data list; macOS 12 or later on `/install` and in the JSON-LD (`LSMinimumSystemVersion` 12.0 in the v0.2.19 app); the OG image, which still carried the retired "Your first invoice is free. No card, no time limit." (regenerated; only the offer lines changed).
- **Independent review (GPT-6.1 Sol, same day), all nine findings applied after re-checking each against the code:** `/privacy` names Sentry's sampled performance traces (`traces_sample_rate=0.1`; sentry-sdk 2.29.1 skips `before_send` for transactions) and says redaction is by field name only; `/privacy`'s date line says the update corrects disclosures of existing practices, and §12 separates material changes (30 days' notice) from corrections; deletion (and correction) in the app only while the account permits editing (a lapsed subscription is read-only, `free_tier.lapsed_may`); the polling sentence (payment and lapsed-subscription screens; `activating.html` 1 s then 3 s, `inactive.html` 5 s then 15 s); PDF import described as it is (text-based, `INV\d+` numbers, numbering only when the format matches); recurring invoices generated when you open the app (`_catchup_done_<user_id>`); macOS 12 beside the download button; Terms §5 without a tax claim; the OG card renamed `assets/og-image-2026-09-29.png` with absolute `og:image` / `twitter:image` URLs, because `/assets/*` is cached for 30 days — **a changed card needs a new dated filename.**
- **When Plausible goes live** (`SCRIPT_UPSTREAM` in `worker.js`): `/privacy` must change the same day — the TL;DR's "runs no analytics today", §3's first sentence and "will be served", and the §5 Plausible row's "(not in use today)" — and its date line. §12 now promises 30 days' notice of material changes to data practices; the page has named Plausible as the planned analytics since 2026-09-29.
- **Left for Daniel, not changed here:** the H1 "Make your first invoice in 60 seconds" is a speed number, but it is the decided copy contract (Gate 0 spec §4.1) and the page links the 25-second real-time recording; `/terms` still says "Effective the same day" (its §8 notice promise covers feature changes for paying customers, and these edits describe what is already live). *(Superseded 2026-10-04, next section.)*

### 2026-10-04 — G1: the speed claim out of the headline (branch `fix/g1-speed-claim`)

The legal audit (vault `03 - Operations/Legal & Compliance Audit — 2026-10-03`, row G1) found "Make your first invoice in 60 seconds" unsubstantiated: the real-time recording (24.76 s) starts at New invoice with a client already set up, and a first invoice also needs the install, Google sign-in, setup and a new client, none of it timed. Daniel's headline replaces it (vault `04 - Future/GTM Decision Register`, A21, decided 2026-10-04: one general message, no audio-vs-freelancer split): **"Invoice your next client for $5 a month"**, the flight-1 ads' LEAD.

- **`/`:** the H1; the meta description ("Invoice your next client for $5 a month (or $50 a year). Every feature free for seven days, no card. …"); `og:title` and `twitter:title` ("Freelance Easy — invoice your next client for $5 a month").
- **`/mac-audio`:** the `<title>` and the H1. **`/audio`** regenerated by `scripts/derive-audio-page.py`, whose title substitution changed to match.
- **The OG card** carried the claim in the image itself: renamed `assets/og-image-2026-10-04.png` (the cache rule above) and regenerated by `scripts/generate-og-image.py` with the new headline; the offer lines are unchanged. From a worktree under `.claude/worktrees/` the script can't find the InvoiceGenerator fonts on its own: set `FE_FONTS_DIR` to `InvoiceGenerator/static/fonts`.
- **Unchanged on purpose:** the `#how` lede "from a new invoice to a PDF ready to send, in about a minute" (the real-time recording backs it: it starts at New invoice with an existing client, and the lede starts there too); the hero offer line.
- **Still showing audio-flavoured sample data (a later option for Daniel, not changed here):** the hero deck and the sample PDFs (INV1045) and the making-an-invoice recording. The ads move to a general invoice, INV1056. *(Superseded 2026-10-05 by the demo-data section below; the earlier demo names were retired under legal G11.)*
- **Against legal v2** (`fix/legal-pages-2026-10`, local): no shared hunks. v2 edits the pricing note, "Your files stay with you", the footer version, `install.html`, `_headers` and the legal pages. `git merge-tree` of the two branches is clean, and the merged `audio.html` is byte-identical to a fresh `derive-audio-page.py` run, so neither order needs a regeneration.
- **Legal chat's claims check (2026-10-04):** approved, and G1 ships ahead of v2. Its one change: the meta description ends "we never host your invoice database" (v2's wording; with folder sync the data folder can sit in Dropbox, so "stays on your computer" was an absolute). Evidence for the kept lede: vault `05 - Reference/Marketing and Video/Claim Substantiation/G1 — about a minute — 2026-10-04`.
- **Verified locally** (`python3 -m http.server`, the in-app browser): the H1, `<title>`, meta description, `og:`/`twitter:` titles and image URLs on `/`, `/mac-audio`, `/audio`; no "60 seconds" in any served page; the new card 200 and the old one 404; the hero H1 wraps in two lines at 800 px and three at 375 px. **The same on the branch preview** (`https://fix-g1-speed-claim-freelance-easy-site.lively-breeze-6443.workers.dev`), through Cloudflare's own routing.
- **Independent review (GPT-6.1 Sol, read-only, 2026-10-04): VERDICT MERGE, no findings.** It confirmed the claim is gone from every served page and the card, the card matches its generator byte for byte, `audio.html` matches the derive script (also after combining the legal branch's edits), and this section is accurate.
- **Two rulings from the legal chat after that review (2026-10-04), carried on this branch:**
  - **The caption's number is gone:** "Sped up. In real time it took 25 seconds." → "Sped up." on `/`, `/mac-audio` and `/audio`, and the link to the real-time file is gone too. The recording's typing is scripted at 38 ms a keystroke (about 316 words a minute), so 25 s read as a person's pace. The lede's "in about a minute" stays: at 25–40 words a minute the same steps take about 43–56 s (the evidence note). The real-time files stay in `assets/video/` as evidence; to show a number again, re-record with human-speed typing and caption the true length. `script.js`'s `a[data-demo-realtime]` swap now finds nothing, which is harmless.
  - **"The app is signed and notarized by Apple"** → "The app is signed with an Apple Developer ID and notarized by Apple." (the LLC signs it, Apple notarizes it; the old line read as if Apple signed or vouched for it). Changed under the download button on `/`, `/mac-audio`, `/audio`. `/install` carries the same sentence beside a line legal v2 edits, so it is left to v2.
- **A third ruling (2026-10-04, approved in advance):** the pricing band's "No tiers, no add-ons." → "**No paid tiers**, no add-ons." on `/`, `/mac-audio`, `/audio`. After the trial a limited free plan exists, so "no tiers" overstated it; there is one paid plan, monthly or yearly.

### 2026-10-04 — analytics ready to switch on in one step (branch `feat/analytics-switch`, off `fix/g1-speed-claim`)

Plausible goes on the day legal v2 publishes (v2's `/privacy` §3 describes it); the two-week baseline before flight 1 starts then. This branch is everything that can live in the repo beforehand. **It is inert: merging it switches nothing on.** `feat/mac-landing` stacks on it, so the switch never waits for `/mac`'s renders: this branch can merge first, any time after G1.

- **`worker.js` — the one switch.** `SCRIPT_UPSTREAM` still holds `pa-REPLACE_ME.js` (off). While it does, the script route answers an empty script and the event route **drops** events (202, nothing forwarded); before, it forwarded any POST to Plausible. **Switching on means putting the site's own script URL there** (Plausible → Site settings → General → Site installation).
  - Even when on, only `freelance-easy.com` and `www.freelance-easy.com` load the real script or forward events. Branch previews (`*.workers.dev`) and local servers stay silent, so our own checks never reach the statistics.
  - **The event contract (`FORWARDED_EVENTS`):** only what `/privacy` §3 lists is forwarded:
    - `pageview` with no properties;
    - Plausible's own `engagement` event (time on page, scroll depth) with no properties;
    - `Download Click` with only `os`, `campaign`, `page`, `placement` (strings of up to 64 characters).
    - Anything else is dropped (202): another event (outbound links, file downloads, forms, a future event), extra or non-string properties. Adding one means a §3 line first, then an entry here.
  - **How it's enforced: Plausible gets a rebuilt copy, never the raw body.**
    - The body is read only if its content type is `text/plain` or `application/json` (what Plausible's script sends), up to 8,192 bytes (a declared larger size is refused before reading; a stream is cut off at the cap), and must be strict UTF-8 JSON.
    - The event must name our domain (`d`) and a page on `freelance-easy.com` or `www` (`u`).
    - The page URL goes on in its canonical form, the WHATWG parser's `href` (http(s) only, no credentials), so Plausible's own parser reads the host that was checked: `https://freelance-easy.com\@evil.example/x` goes on as `https://freelance-easy.com/@evil.example/x`.
    - A referrer that isn't an http(s) URL goes on as `null`, and one longer than 2,048 characters is cut to its origin and path. A referrer never drops its event.
    - It's then rebuilt from the browser format's known fields only (`n u d r v h i`, `sd e` for engagement, `p` checked against the list) and sent on as `text/plain`.
    - So a field nobody listed (a legacy property field `m`, `meta` or `props`, revenue `$`) never reaches Plausible, a form-encoded body can't make Plausible read different fields, and what Plausible parses is exactly what was checked.
  - **`scripts/test-worker.mjs`** (`node scripts/test-worker.mjs`, Node 20+, offline with a mocked fetch): 46 checks, all passing.
    - Beyond the switch and the hostnames, they cover each attack Sol found: the legacy property fields, form-encoded and multipart bodies, a missing content type, a 9,000-byte Unicode body under 8,192 characters, a streamed 2 MiB body (cut off after 3 chunks), invalid UTF-8, duplicate keys, `__proto__` properties, another host or domain, the backslash-userinfo URL, credentials, `javascript:`, a long and a non-http referrer.
    - The suite expects `worker.js` to be off.
    - `--payloads <file>` replays captured real events through the same code. It runs switched on (as the file is, or with a test id), so it also works after the switch. Each event is replayed with its own content type. Its domain is kept unless `--substitute-domain` is given.
- **`script.js`:**
  - **The campaign allowlist.** `CAMPAIGNS = ["f1"]`: a download path (`/dl/<os>/<label>`) and the `campaign` property carry `?utm_campaign` only when its value is on the list (any case); otherwise they carry the page's own label (`site`, `mac-audio`, `audio`, `mac`). Before, any value sanitised to `[a-z0-9-]` went through. Add each flight's label before its ads run.
  - **The Windows link isn't a download.** On Mac-only pages the "Need the Windows version?" link (a link to `/`) no longer sends `Download Click`, so the Mac goal is simply `os=mac`.
  - The deck's `data-alt` / `href` reading, which `/mac` needs.
  - **Two events removed:** "Compatibility Help Opened" and "Share To Computer". v2's `/privacy` §3 says the site counts pages, referrer or campaign, browser, OS, rough location and "which download button was clicked". It doesn't cover those two, and the weekly report doesn't use them. A new event needs a §3 line first; the file's header says so.
- **`_redirects`:** the corrected `/dl/` comment (it passes query strings on; ads land on `/mac` only).
- **`scripts/check-download-wiring.py`** (new): the repeatable check of the download links and events, described in the one-step list below.
  - With `--tracker <pa-….js URL>` it also loads `/mac` with a REAL Plausible script. Events are answered locally, and anything addressed to plausible.io is blocked.
  - It captures what that script sends, with each event's content type; clicks the Mac button; simulates a tab switch; and replays every captured event through `worker.js`'s contract.
  - A pageview, a `Download Click` and an engagement event must all be captured, and each must be forwarded, so a change in Plausible's event format can't silently drop our counts.
  - With the site's own script the events must already name `freelance-easy.com`. `--public-tracker` lets Plausible's own public script stand in by substituting our domain; without that flag its events are dropped (checked: 4 of 4).
  - 2026-10-04, with Plausible's own public build (`pa-6_srOGVV9SLMWJ1ZpUAbG.js`, script version 36): all 4 real events were forwarded intact.
    - pageview `{n, v, u, d, r}`;
    - `Download Click` `{n, v, u, d, r, p}` with exactly our four properties;
    - engagement `{n, sd, d, u, e, v}`;
    - a second pageview.
  - The script masks `navigator.webdriver` in that run only: Plausible's script ignores automated browsers.
- **What the site sends once on:**
  - pageviews;
  - `Download Click` `{os, campaign, page, placement}`;
  - Plausible's own engagement event (time on page, scroll depth), which the script sends when a visitor leaves or switches tabs. v2's §3 lists it since legal commit `7fd949a` ("how long they stay open and how far they're scrolled").
  - The Worker forwards nothing else.
- **Independent review (GPT-6.1 Sol, read-only, 2026-10-04): FIX FIRST, two findings, both fixed.**
  - P1: activation would forward the undisclosed engagement event. Now it's disclosed in §3, and the Worker enforces the whole list above.
  - P2: the production check expected Daniel's realtime visit after his IP shield excluded it. The shield now comes after the check.
  - Everything else passed (89 checks): the inert state, the one-line switch, the hostname guard (resists Host-header spoofing; runs before the cache), the forwarded headers, the single `Download Click` call, the allowlist (case, whitespace, encoding, empty and repeated parameters), the Windows link, the deck fallback.
- **Sol's re-check of the filter (same day): both fixes confirmed, four new findings, all fixed** in the rebuilt-copy design above.
  - P1: the legacy property fields (`m`, `meta`) passed. Plausible reads them before `p`.
  - P1: a form-encoded content type would make Plausible read different fields.
  - P2: the size cap counted characters, not bytes, and read the whole body first.
  - P2: this check script only printed the `/js/script.js` result. It now asserts it: on a preview a 200 with the exact empty script, on a local server a 404.
  - While fixing that last one: Cloudflare answers a top-level *navigation* to `/js/script.js` with the 404 page without running the Worker. Script loads (what visitors do) and plain requests reach it, so the check uses a plain request.
- **Sol's third pass: the four re-check fixes confirmed, and the rebuilt-field design judged sound. Four narrower findings, all fixed.**
  - P1: the page URL was checked with one URL parser and parsed by Plausible with another. It now goes on in its canonical form.
  - P2: the replay refused an activated Worker. It no longer does.
  - P2: a long referrer dropped its event. It's now cut.
  - P2: the real-tracker replay ignored the content type and the domain and didn't require engagement. It now checks all three.
  - Verified after the fixes: the suite (46), the real-tracker check (4 of 4 forwarded with `--public-tracker`, 4 of 4 dropped without it), and a replay of own-domain events through a switched-on copy of `worker.js` (3 of 3 forwarded).
- **Sol's fourth and final pass (`a0b8611..e98ae8e`): VERDICT MERGE (inert), no findings.** All four fixes check out, with no regression or new bypass in the edge cases asked about: canonical URLs past the limit, IDN hosts, `www`, the referrer cut, the domain flags and the replay's URL rewrite.

**The v2-day checklist:**

*Daniel, in Plausible (before the switch; about 25 minutes):*
1. Create the account on the **Business** plan (30-day free trial). Custom properties, funnels and the Stats API are Business features. Accept the data processing agreement (https://plausible.io/dpa).
2. Add the site `freelance-easy.com`, timezone **America/Chicago** (the Ads account's and the report's).
3. **Site settings → General → Site installation:** copy the script URL (`https://plausible.io/js/pa-….js`) and send it to Claude. Leave every optional measurement **off**: outbound links, file downloads, form submissions, 404 pages, revenue, hash-based routing. The site sends only pageviews, Plausible's engagement event and `Download Click`, and the Worker drops anything else; adding more needs a `/privacy` line first.
4. **Site settings → Goals → + Add goal**, all before the switch (Plausible doesn't backfill goals):
   - a pageview goal for `/mac`;
   - custom event `Download Click`, narrowed to the property `os` = `mac` (name it "Mac download");
   - the same narrowed to `os` = `win` ("Windows download").
5. **Funnels:** `/mac` pageview → "Mac download".

*Claude, the one step (same day, right after v2 is live):*
1. On `feat/analytics-switch` (or a branch off `main` once it has merged), replace `REPLACE_ME`: `SCRIPT_UPSTREAM = "https://plausible.io/js/pa-<id>.js"`. Push.
2. Run `uv run --with playwright python3 scripts/check-download-wiring.py <preview URL> --tracker https://plausible.io/js/pa-<id>.js` on the switch branch's preview, with the site's OWN script and without `--public-tracker`: its events must name `freelance-easy.com`, which catches a site added under another name. It needs the installed Chromium, and it refuses production, where a click would count as a real download. Run the full suite `node scripts/test-worker.mjs` before putting the id in (it expects `worker.js` to be off); the replay inside the check works after.
   - It checks 8 cases; the `/js/script.js` route, which must still answer `/* analytics off here */` on a preview (previews never count); and that every event the site's real script sends passes the Worker's contract.
   - Then merge to `main` on Daniel's word.
   - It checks: the two flight-1 ad URLs (`/mac?utm_campaign=f1…`, `ta` and `tb`) wire the button to `/dl/mac/f1`; a value not on the allowlist falls back to the page label; `Download Click` carries exactly `{os, campaign, page, placement}`; the Windows link on Mac-only pages sends nothing; nothing else fires.
   - Proven both ways on 2026-10-04: ALL PASS on the `feat/mac-landing` preview, and 4 FAILED on the G1 preview's old `script.js` (the extra event, leaked campaign values, the Windows link counted).
3. **Production check:**
   - `curl -s https://freelance-easy.com/js/script.js` returns Plausible's script, not the empty one;
   - one visit to `/` from this Mac shows in Plausible's realtime view. Do this before Daniel's IP shield below: this Mac shares his IP, so after the shield its visits don't count;
   - don't click a download button on production (it would add a fake download to the baseline). The `Download Click` wiring is checked on the preview, where events are queued but never sent.
4. Tell the data chat the baseline start (date and time, Chicago). The data chat's rule: the clean baseline starts the day after, so the check visit doesn't count in it.

*Daniel, after BOTH Claude's production check and the data chat's fresh-Mac funnel test* (playbook step **6c**; the funnel test also runs from this Mac and checks Plausible's realtime view): **Shields → IP addresses**: add your own IP so your visits don't count. If Shields also offers hostnames, allow only `freelance-easy.com` and `www.freelance-easy.com`; that's optional, because the Worker already enforces it.

*Later, when the weekly report moves off hand entry:* a **Stats API key**. Plausible → your account → Settings → API Keys → New API Key → **Stats API**. It is team-scoped and Business-plan only, limited to 600 requests an hour, and queried with `POST https://plausible.io/api/v2/query` and `Authorization: Bearer …`. It goes to the report's owner as a secret, never into the vault or git.

### 2026-10-04 — `/mac`: the general Mac landing page for the ads (branch `feat/mac-landing`, stacked on `feat/analytics-switch`)

Spec: vault `03 - Operations/Execution Playbook — $1,500 (2026-10)` §4 and §8, the A24 list in `04 - Future/GTM Decision Register`, and the ad text v3 (`_creative-raw/2026-09/spike/price-drop/out/infeed/ad-copy.txt`). Flight 1's ads land here: `/mac?utm_source=google&utm_medium=demandgen&utm_campaign=f1&utm_content=ta` (and `tb`). It goes live only after legal v2 (flight 1 needs v2 and Plausible).

- **The page** (`mac.html`, `noindex`): `/mac-audio`'s structure with the homepage's general copy.
  - Hero: kicker "For Mac, M1 or later." (the ads' long headline ends "Mac M1 or later."); the H1 is the ads' LEAD, "Invoice your next client for $5 a month"; the offer line was "$5 a month is less than a cup of coffee, …" (A25: the coffee line on the same line as the $5; replaced 2026-10-05 by legal G10 v2's latte wording, see below); the homepage's lede, saying "Mac" and "Made by a freelancer who bills with it" (the homepage says "a mix engineer"; Daniel's note further down still does).
  - The making-an-invoice caption is "Sped up." with no real-time number (the legal ruling on G1, above).
- **The download block** (Mac only, `data-single-platform="mac"`):
  - under the button: Apple Silicon, macOS 12, "signed with an Apple Developer ID and notarized by Apple", "Freelance Easy is in beta." (no version number to go stale; the footer has it);
  - the button's no-JS `href` is `/dl/mac/mac`, the page's own label (script.js replaces it);
  - the install disclosure Google's software policy asks for (A24 item 6): drag to Applications, Google sign-in, a folder you choose on your Mac, the subscription check and the update check at each start, and an update installing when you choose to restart.
  - Each clause was checked against v0.3.0-beta: the arm64-only DMG (`electron/package.json`); `LSMinimumSystemVersion` 12.0 (the built app's Info.plist); `/check-license` at launch; `electron/main.js` (`autoDownload = true`, `autoInstallOnAppQuit = false`, the banner's "Restart now").
- **The hero deck is the ads' invoice:** INV1056 (the invoice-film chat's `invoice-film/data/inv1056.json`, a draft until Daniel's styleframe OK; its client was renamed under legal G11 on 2026-10-04, see the 2026-10-05 sections below).
  - `assets/samples/inv1056-<style>.pdf` are the invoice-film chat's **draft** renders (2026-10-04). They're the app's own `pdf_gen` output from `invoice-film/data/inv1056.json`: title "October work", accent `#4a7c7e` in all four templates, fictional persona and client. `assets/screenshots/inv1056-<style>.webp` are rastered from them. They replaced the labelled placeholders the same day. **Don't merge before Daniel's styleframe OK.**
  - If the data or template changes at that OK: copy the new `invoice-film/kit/pdf/INV1056-<style>.pdf` over `assets/samples/inv1056-<style>.pdf` (lowercase), then run `uv run --with pymupdf --with pillow python3 scripts/build-hero-collage.py sheets --set inv1056`.
  - Check that the front template matches the ad's. The deck starts Modern-front; another front means changing the sheets' inline geometry and script.js's starting order.
  - Update the `data-alt` text if the content changed.
- **A24, item by item:**
  1. the H1 ✓;
  2. the ad's invoice ✓ (placeholder until the renders arrive);
  3. macOS 12 under the button ✓;
  4. the sending explanation, as step 3: "Set up your email account in Settings to send it from your own address, or save the PDF and send it yourself." ✓;
  5. the beta beside the download ✓ (the version number is in the footer);
  6. the install disclosure ✓;
  7. no crossed-out price ✓;
  8. the tagged link in the YouTube description is the ad chat's.
- **Legal v2's wording, taken now** (the page ships after v2): the pricing note's "Where sales tax applies, it's added at checkout."; "doesn't host it, and the app never uploads it to us"; v0.3.0-beta in the footer. The band's lead line says "No paid tiers, no add-ons." like the other pages (the third G1 ruling above).
- **Kept from the homepage, flagged as later options for Daniel** *(superseded 2026-10-05: everything is re-captured on the G11 account, see below)*:
  - The making-an-invoice recording and the dashboard screenshots still show the audio demo data (mixes, mastering, studios).
  - The light recording's invoice is also numbered INV1056, a different invoice.
  - A general re-capture, or the invoice film's `?cut=film`, would replace them.
- **`script.js`** (built here, now carried by `feat/analytics-switch`, which this branch stacks on; that branch also removed the two events `/privacy` doesn't list):
  - **The campaign allowlist.** `CAMPAIGNS = ["f1"]`: a download path carries `?utm_campaign` only when its value is on this list (any case); otherwise the page's own label is used (`/dl/mac/mac` on `/mac`, `site` on `/`). Before, any value sanitised to `[a-z0-9-]` went into the path and the `campaign` property. Add each flight's label before its ads run.
    - The legal rule behind it: the path carries only the campaign label, with no other query value and no per-visitor id. The DMG's name never changes.
    - **`_redirects` does not drop a query string:** Cloudflare passes it on to GitHub (checked on the branch preview, `/dl/mac/f1?probe=1` → `…/Freelance-Easy.dmg?probe=1`). The old comment saying it did was wrong. The rule holds because no link we make adds one: the buttons' paths come from script.js, the ads land on `/mac`, and GitHub gets only our origin as the referrer (`Referrer-Policy: strict-origin-when-cross-origin`). If a hard guarantee is ever wanted, `worker.js` can answer `/dl/*` itself and drop the query (the redirect lines then leave `_redirects`).
  - **The Windows link isn't a download.** On a single-platform page, "Need the Windows version?" (a link to `/`) no longer sends `Download Click`. The Mac goal is `Download Click` with `os=mac`.
  - **The deck reads its data from the HTML.** It takes each sheet's PDF from its `href`, and the front sheet's description from `data-alt`. The homepage's deck (no `data-alt`) falls back to `SHEET_ALT` and is unchanged.
- **`_redirects`:** `/mac/` → `/mac` (301); the campaign comment updated. **`_headers`:** `X-Robots-Tag: noindex` on `/mac`.
- **Bump at each release:** `/mac`'s footer "v0.3.0-beta", like every page's.
- **Verified locally** (`python3 -m http.server`, the in-app browser):
  - **Campaign resolution in 10 cases** across `/`, `/mac`, `/mac-audio`, `/audio`: `f1` and `F1` pass; a name, a click-id-like value, `f1x` and an empty value fall back to the page label.
  - **Events:** on `/mac`, one `Download Click {os: mac, campaign: f1, page: mac, placement: hero}`, and nothing for the Windows link. The homepage still sends both of its clicks.
  - **The deck:** Modern in front with its `data-alt`; Bold from the picker gets its own description, and "Open the Bold PDF" points at `inv1056-bold.pdf`. The homepage's deck is unchanged (`SHEET_ALT`, `invoice-bold.pdf`). All eight INV1056 files answer 200.
  - **Layout:** at 800 px the hero column ends level with the deck; at 375 px phones get "Copy page link".
- **Accessibility (axe-core 4.10.2, WCAG 2.1 A/AA, headless Chromium on the branch preview, 2026-10-04):** `/mac` has **0 violations in the dark and the light theme**, and nothing left for review under `color-contrast` or `link-in-text-block`; `/mac-audio` (control) the same.
  - The scan is proven able to fail: on the same preview, `/privacy` with `main`'s styles shows the doc-link problems legal v2's `393c7fd` fixes (dark 3.93:1 contrast, light 2.5:1 link-in-text-block).
  - Re-run before merging once the real INV1056 sheets are in.
- **Reviews (2026-10-04):**
  - **GPT-6.1 Sol (read-only): FIX FIRST, two findings, both fixed.** The no-JS button went to `/download/mac`, skipping the page label (now `/dl/mac/mac`); "Made by a mix engineer" was audio wording in the general hero (now "a freelancer"). Its checks otherwise passed: 336 routing and event cases, the deck on four pages, and `sheets` byte-identical to before for the homepage set.
  - **Legal chat: approved,** with "signed with an Apple Developer ID and notarized by Apple" (applied here and, via G1, on `/`, `/mac-audio`, `/audio`) and no version number beside the button. Its conditions: the hero must be the app's real render (fictional data) before the merge, and any later claim-bearing change goes back to it. The `/dl/` rule stays "by construction"; if a link ever has to point straight at `/dl/`, do the Worker version first.

### 2026-10-05 — demo data: the persona and every client cleared (legal G11) (branch `fix/demo-data-g11`, off `fix/capture-scripts-dev-port`)

Legal's demo-data rule G11 (vault `03 - Operations/Legal & Compliance Audit — 2026-10-03` §7) found real-business collisions and a payment brand in the site's demo data, and ruled the persona renamed. The earlier demo names, all retired, are listed in the private NAMES-LOG (Dropbox `_creative-raw/2026-09/spike/invoice-film/data/NAMES-LOG.md`), never in this public repo. Every product image now shows the fictional account the ads use (the invoice-film chat's dashboard kit), so `/`, `/mac` and the ads show one world. This branch carries `fix/capture-scripts-dev-port` (the capture scripts default to :50506 and refuse :50505).

- **On the pages** (every product image, re-captured from the released app, v0.3.0-beta, in dev mode on :50506):
  - **The hero deck and the four sample PDFs:** INV1056 for Halvard & Wren, $1,500 (project work 16 × $75, revisions 4 × $75), the ads' invoice, in the four templates with the same four accents as before. Was INV1045, on a retired demo name.
  - **The dashboard shots** (dark, light and both phone crops): Jordan Wexcombe in the sidebar; one overdue invoice (INV1049, Ostrander & Bell) instead of three on unsearched names; the KPIs, chart and Recent invoices match the ads' dashboard ($19,950 collected YTD).
  - **The making-an-invoice recording, both themes:** a new invoice INV1057 for Quillmont Roasters ("Menu board design", $450, plus print-ready files, $75 = $525), with the note "…payment by bank transfer within terms." (no payment brand). Was a client name that had never been searched, with a payment brand in the note.
  - **Alt text only:** the hero sheet (here, `/mac-audio`, `/audio` and the deck alts in `script.js`) and the dashboard ("a fictional overdue invoice"). No other copy changed. `/audio` and `/mac-audio` share these images, so they show the general account too.
- **The data: `scripts/seed-demo-profile.py` (new).** It seeds a throwaway dev profile and refuses Dropbox, Application Support, iCloud, a checkout's `.dev-profile` or an account that already has data.
  - Persona Jordan Wexcombe, jordan@example.com, Nashville.
  - Four clients, each invented and web-searched clean on 2026-10-04: Halvard & Wren, Ostrander & Bell, Quillmont Roasters, Larkhaven Audio (the log, with queries and dates: `_creative-raw/2026-09/spike/invoice-film/data/NAMES-LOG.md`).
  - INV1031–INV1056 exactly as the kit has them; the script asserts the kit's monthly totals and the $19,950.
  - Emails on `*.example`, no phone numbers, city-only addresses.
  - A backup folder is set (no "Set up a backup folder" row, as in the ads' dashboard), and the first PDF is marked long since downloaded (v0.3.0's "Get started" card is complete, as for any account a year in).
- **Script fixes found on the way:**
  - `capture-screenshots.py` waited a fixed 800 ms, but v0.3.0's KPI figures count up for about 1.1 s, so the Overdue tile was shot reading $449. It now waits until every figure shows its target and no animation is running.
  - `build-hero-collage.py render` renders INV1056 and reads the seeded pre-sync database (folder sync off in that process; 0.3.0 keeps the live copy outside the data folder).
  - The docstrings point at the seed, not the shared `.dev-profile` (the Mac's holds no demo data).
- **`_headers`: the sample PDFs are cached for a day, then revalidated,** like the screenshots and the video, instead of `/assets/*`'s month. They keep their names across re-renders, so with the month a browser that had opened one could keep showing the old copy. A browser that cached an old PDF before this deploy may still show it until its own month runs out; every new visitor gets the clean one. A hard guarantee would mean new filenames (the OG card's dated-name rule).
- **How it ran (2026-10-05, the Mac):**
  - a detached InvoiceGenerator worktree at `v0.3.0-beta`;
  - the mock LicenseServer on :5001 with a scratch SQLite database;
  - the app with `FE_DEV_PROFILE` at a scratch profile and a scratch HOME;
  - Playwright 1.63.0 (Chromium 1243);
  - one freshly seeded profile per recording, so both show INV1057;
  - ffmpeg from the `imageio-ffmpeg` wheel.
  - Nothing reached :50505, and `lsof` showed nothing left on 5001, 50505 or 50506 afterwards.
- **Checked:**
  - pdfplumber on the four PDFs: the persona, the client, INV1056, $1,500.00 and the clean note are present; no retired demo name (the NAMES-LOG list), payment brand or Daniel's name, metadata included;
  - every image, and frames across both recordings, by eye;
  - `git grep`: no retired name in any served file.
  - The branch preview (`https://fix-demo-data-g11-freelance-easy-site.lively-breeze-6443.workers.dev`) serves all three pages and all 18 files byte-identical to the branch.
- **Legal chat (2026-10-05): PASS** (its own pdfplumber scan; the dashboard by eye: four cleared clients, one overdue on a searched name; the alt texts accurate). Invented generic line items and titles are fine under G11. One guardrail for future items: no trademarked product or platform names and no real venues or events. Its two public-repo cleanups are applied: the persona line above, and the retired names replaced by a pointer to the private NAMES-LOG.
- **Independent review (GPT-6.1 Sol, read-only, 2026-10-05): FIX FIRST, four findings.** Three are fixed:
  - P1: the seed's refusals ran after some writes (a symlink planted in an existing profile could steer them). The seed now creates the profile directory itself, refuses one that already exists, and checks that the data root, the account folder and the database file resolve inside it before the first database write.
  - P2: it refused only the given checkout's `.dev-profile`. It now refuses any `.dev-profile` in the path.
  - P3: two deck alts in `script.js` misdescribed their sheets: Bold's "Invoice" is black (only the number is navy), and Classic's name and job are not in a serif.
  - Not taken: its claim that Minimal's title sits at the upper right. In the raster it's centred, as the alt says.
  - Its fourth finding is `/mac`'s (see that section).
  - Everything else passed: the served files and images clean, the dashboard and Modern alts, the header stacking (one Cache-Control value), `audio.html` equal to the generator's output, the dataset assertions, and the KPI wait (it ignores infinite animations on purpose).
- **Also on this branch (2026-10-05):**
  - the four stale version lines → v0.3.0-beta (the Latest release since 2026-10-03): `install.html` and the footers of `/`, `/mac-audio`, `/audio`. They're identical to legal v2's edits of the same lines, so either merge order is clean;
  - `assets/logo.svg` removed.
  - Re-checked on the preview after these commits: the changed pages and `script.js` byte-identical to the branch; `/assets/logo.svg` 404. axe 4.12.1: `/` and `/mac-audio` 0 violations in both themes. `/install` keeps two link findings (dark contrast, light link-in-text-block) that production shows identically; they're the doc pages' link styles that legal v2 fixes.
- **Legal's final pass on the delta (2026-10-05): PASS** (its `git grep` of the tracked files for the retired names and payment brands finds none; no history rewrite, agreed). One fix was applied first: `install.html` had lost the space after the "·" (the edit tool trims trailing whitespace from a replacement). That rendered "v0.3.0-beta ·Release files…" and made `git merge-tree` conflict with v2. The line is byte-identical to v2's now, and `git merge-tree --write-tree` is clean both against `fix/legal-pages-2026-10` and into `origin/main`. **The branch is cleared to merge on Daniel's yes, on its own, ahead of v2.**

### 2026-10-05 — `/mac` caught up: the renamed INV1056, the latte line, the theme-matched hero (branch `feat/mac-landing`)

- **Merged in:** `main` (e9c3a97: G1 + the inert analytics switch) and `fix/demo-data-g11` (above). The conflicts were the HANDOFF appends (all kept, in date order) and the collage script's docstring.
- **The deck's PDFs are the renamed INV1056:** `assets/samples/inv1056-<style>.pdf` re-copied from the invoice-film chat's `kit/pdf/INV1056-<style>.pdf` after its G11 renames (Jordan Wexcombe, Halvard & Wren, the note without a payment brand; pdfplumber clean), then `build-hero-collage.py sheets --set inv1056`.
- **The offer line (Daniel approved it 2026-10-05: "i like it just needs to be formatted aesthetically"; legal G10 v3):** under the h1, "Unlimited invoices for less than a cup of coffee.* / Every feature included. Free for 7 days, no card.", with the note "*vs. a typical café latte" directly beneath.
  - **Legal's G10 v3 conditions:** the note sits directly under the line and is always visible (no hover, tooltip or collapse; phones too); it is ≥ 15 px in normal body-text colour (not faded), ≥ 4.5:1 in both themes; it reads as part of the line, not fine print; no plain or drip coffee imagery nearby. Why: a regular cup is $3.77 (Toast median, Aug 2026) and a café latte $5.60 (vault `05 - Reference/Marketing and Video/Claim Substantiation/G10 — less than a cup of coffee — 2026-10-04`).
  - **The layout:**
    - a `<br>` after the coffee sentence;
    - a non-breaking space so "coffee.*" never sits alone;
    - "Free for 7 days, no card." kept on one line (`.keep`, nowrap), so phones break after "included." (four even lines);
    - `text-wrap: balance`;
    - the note at 16 px in `--text-1` (the body-text colour in both themes, and Tier 1's offer colour too), 6 px under the line, while the lede starts 14 px below, so it groups with the offer.
    - The two small rules sit in a page-scoped `<style>` in `mac.html` (`styles.css` belongs to the premium pass); fold them in with Tier 1.
  - Looked at in both themes at 1280 px and 375 px.
  - The meta description is tightened to the same voice: "Desktop invoicing for freelancers on your Mac. $5 a month, every feature, unlimited invoices. Free for 7 days, no card." (no coffee claim, so G10 doesn't apply).
  - Superseded: the G10 v2 line "$5 a month is less than a typical café latte, and it includes …" (Daniel: "too wordy").
- **The dashboard alt** says one fictional overdue invoice (the re-captured shots).
- **The hero is theme-matched: the invoice film's FINAL stills, in Classic (2026-10-05).** The four-template deck is gone from `/mac`. In its place:
  - One figure (`hero-invoice shot`) holds two images of INV1056 as light paper, in the motion chat's frame: 1200×1400, transparent, the page whole with its shadow baked in. `mac-hero-light.webp` has a soft shadow, for the light site; `mac-hero-dark.webp` is the same paper with a deeper shadow and a faint rim, for the dark site. The page theme picks one with the dashboard's `.shot` rules.
  - The invoice stays light paper in both themes, as Daniel asked ("the invoice itself should be light mode"), and there's no lifted totals box.
  - No new CSS. `.figure` is left off, because its border and box would frame the transparent image. The two images carry `width: 100%; height: auto` inline, so `styles.css` (the premium pass's file) is untouched.
  - Loading: both images are `loading="lazy"`, so the hidden one never loads, and the head script preloads the visible theme's image at high priority. This is Sol's P2: before, a light-theme visitor downloaded the hidden dark image eagerly and lazy-loaded their own.
  - The caption: "An invoice made in Freelance Easy; the names on it are fictional. Open the PDF" (`inv1056-classic.pdf` since Daniel's template pick; `inv1056-modern.pdf` before). Legal's wording: "The client is fictional" implied the sender might be real, and the persona shown using the product would read as a real customer (an implied endorsement).
  - **Daniel picked CLASSIC** for the film and the hero (the motion chat's Motion Picks, 2026-10-05 17:14Z; its recommendation was Bold).
  - **The final stills** (the motion chat's `review/hero/hero-{light,dark}.png`, 2026-10-05) are now `mac-hero-{light,dark}.webp`: WebP with alpha, quality 90.
    - The source: INV1056 in Classic from the film kit's real markup (the in-app invoice card), whole, no callout, no cursor. The paper is 1000×1172 at x 100, y 114.
    - The two interiors are pixel-identical. Light has the house soft shadow; dark has a deeper, softer shadow plus a 1 px `rgba(255,255,255,.06)` hairline. Every shadow fades to alpha 0 before the canvas edge.
    - Checked on install: 1200×1400, transparent corners, opaque paper, alpha kept in the WebP. By eye over both site backgrounds, everything is cleared demo data (Jordan Wexcombe, Halvard & Wren, example.com/.example).
    - **The one difference from the PDF is the date format.** The in-app card shows ISO dates ("2026-10-05", due "2026-11-04"); the PDF prints "Oct 05, 2026" / "Nov 04, 2026". They're the same data in the app's two real formats, so the PDF stays as it is (the motion chat checked the rest of the text matches). Whether "Open the PDF" needs a note went to legal; my recommendation is no note.
    - The alt describes the content, which is the same in both, so it stands.
    - The placeholders before them: a render of `inv1056-classic.pdf` (after the pick), and before that a Modern render, which had itself replaced the app's invoice page with its toolbar (1200×1012).
  - **Removed with the swap:** the deck's unused files, `inv1056-{bold,modern,minimal}.pdf` and all four `inv1056-*.webp`. The collage script's `--set inv1056` is undone too, so `scripts/build-hero-collage.py` equals `main`'s. `inv1056-classic.pdf` stays: it's the "Open the PDF" link.
- **Checked on the branch preview (2026-10-05):**
  - before the hero change: `node scripts/test-worker.mjs` 46/46; `check-download-wiring.py` 8/8 plus the inert `/js/script.js`; axe-core 4.12.1 (WCAG 2.1 A/AA, headless Chromium) finds 0 violations on `/mac` and `/` in the dark and the light theme, while the control (`/privacy` with `main`'s styles) still fails on the link issues legal v2 fixes;
  - after it (`1ad2344`): every served file byte-identical to the branch; axe 0 violations on `/mac` in both themes (the `/privacy` control fails as expected); download wiring 8/8 plus the inert analytics route.
  - Locally: a dark load fetches only `mac-hero-dark.webp` and a light load only `mac-hero-light.webp`, each through the preload; both render at the 6:7 shape (480×560 in an 800 px window).
- **Legal (2026-10-05): PASS** on the delta and on the first hero placeholder (every visible button a real shipped feature). The final stills get a 2-minute G11 look.
- **Legal (2026-10-05, 17:25Z): PASS on the offer line (`0a070ce`), explicitly.** Daniel's line plus "*vs. a typical café latte" directly beneath it meets G10 v3: 16 px in `--text-1` (13.2:1 / 11.3:1), always visible, no coffee imagery. The caption fix and the meta description are fine. The first-visit `sessionStorage` theme flag raises no privacy issue: no page claim covers browser storage, and it's a session-only display flag.
- **The pricing note carries legal v2's before-Link line now** (legal, 2026-10-05): "Checkout shows the currency and the full total, including any tax, before you pay." It replaces "Where sales tax applies, it's added at checkout." word for word, the same as the before-Link branch's `/mac-audio` note.
  - **So `/mac` no longer waits for Stripe's Managed Payments switch-on.** Its gates now:
    - legal v2 (the before-Link branch) published first, or in the same deploy;
    - the film stills' G11 look;
    - Daniel's merge yes.
  - The old tax line was the page's only sentence that depended on Managed Payments. Legal checked the rest of `mac.html`: the renewal line ("Cancel in the app's Settings, through the Stripe billing portal…") and "Checkout is handled by Stripe: card, Apple Pay or Link…" are true before and after the switch, since Stripe keeps the Customer Portal for Managed Payments subscriptions.
  - When `/mac` merges `main` after v2, `/`, `/mac-audio` and `/audio` arrive with the same line. If Daniel picks a v2 variant other than before-Link, legal tells the orchestrator, and this line follows it.
- **`/mac` opens LIGHT for a first visit** (Daniel picked a light flight-1 ad; agreed with the premium pass chat, 2026-10-05). A choice made with the toggle (`localStorage` `fe-theme`) still wins; the rest of the site stays dark-first.
  - `mac.html`'s head script sets light unless the stored choice is "dark". With no stored choice it also writes `sessionStorage` `fe-theme-visit=light`, so the light look can carry to other pages for the visit.
  - The read side (a stored choice first, then `fe-theme-visit`, else dark) goes into the head scripts of `/` and `/mac-audio` (so `/audio` too) with the premium pass's Tier 1 head lines; until then those pages ignore the key and open dark. The legal pages don't read it.
  - `script.js` now keeps the theme each page's head script chose, instead of recomputing it from `localStorage` (which would have flipped `/mac` back to dark after load). It's the same outcome on every other page: each one that loads `script.js` has the head script.
  - Checked locally (8 paths, Playwright, fresh contexts):
    - a first visit to `/mac` is light, writes the visit key and fetches only the light hero;
    - then `/` opens dark (no read side yet);
    - the toggle on `/mac` stores dark, and a reload keeps it;
    - a stored dark gives dark on `/mac` (only the dark hero), and a stored light gives light;
    - the homepage is unchanged on a first visit (dark) and with a stored light.
  - Checked on the branch preview after `8ea92b1`: the same 8 paths pass; axe 0 violations on `/mac` and `/` in both themes (each pass sets its theme explicitly now, since `/mac` opens light); download wiring 8/8.
  - The privacy page (live or v2) doesn't list browser storage; the theme keys are a display preference (no cookie, nothing sent). Flagged to legal as an FYI.
- **When Tier 1 lands:** add its two `<head>` lines to `mac.html`: `document.documentElement.classList.add("js");` as the first statement of the theme IIFE, and `<link rel="preload" href="/assets/fonts/Inter-Variable-latin.woff2" as="font" type="font/woff2" crossorigin />` right before the stylesheet link. Then merge `main` and re-run axe in both themes and the wiring check.
