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
- **Logo:** ✅ Swapped to the canonical FE-tile in v0.2.9-beta refresh (2026-05-05). `assets/logo.png` + `assets/logo.svg` + `favicon.ico` all carry the new mark; brand-mark spans in `index.html` header + footer reference `assets/logo.png` directly.
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

**Branch `feat/v2-landing` — do not merge until v0.2.18 is in staged rollout and the LicenseServer annual/no-trial/promo-code change is deployed.** Until then the copy ("your first invoice is free — no card", "$50 a year") is false. Spec and plan live in the FREELANCE EASY VAULT: `04 - Future/Gate 0 — Lean Build Spec.md` §4 and `04 - Future/Landing v2 — Build Plan.md`.

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
- **Demo data:** fictional persona **Jordan Reyes / jordan@example.com** (never a real name or email). `scripts/capture-screenshots.py --profile <.dev-profile>` regenerates all five images + the sample PDF and rewrites the mock session's display name; it asserts the persona is on screen. Requires `playwright pymupdf pillow`.
- **`script.js`:** per-block wiring; events `Download Click {os, campaign, page, placement}`, `Compatibility Help Opened`, `Share To Computer {how}`; clipboard failure shows the URL.

Still to do before merging #6 (besides the publish gate): the two orange placeholders on `/privacy` and `/terms`, Daniel's read-through, his credit-line choice, and the Plausible script id in `worker.js`.

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

#### "Making an invoice" = the real creation flow (same day, follow-up)

Daniel: "present a better representation of the invoice creation process." The single editor screenshot became **three frames of a real invoice being made** plus **a 25-second screen recording**, all captured by `scripts/capture-process.py`, which drives the actual UI as the fictional persona (new invoice → title → Net 30 → client → two line items → note → Create), screenshots each stage in both themes with phone crops, then **deletes the invoice** via `POST /invoices/<id>/delete` so the demo data is unchanged (19 invoices). `--video` records one dark pass with a drawn cursor and typing-speed input (Playwright records no cursor) and writes `marks.json`; `scripts/encode-process-video.py` trims and encodes it to `assets/video/make-an-invoice.mp4` (H.264 1280×800, ~770 KB, 25 s) and a poster from the line-items moment. The page shows the recording as **poster + native controls, no autoplay** (`preload="none"`); `script.js` counts a "Demo Played" event once. The old `editor*.png` assets are gone; `capture-screenshots.py` now produces only the dashboard shots, the hero crop and the sample PDF. Notes: use `http://localhost:50505` (the app redirects `127.0.0.1` → `localhost`, which turns the delete POST into a GET); the app's `next_invoice_number` counter still advances after the delete, so the number in the frames (INV1054) and in the video (INV1055) differ by one and will climb on every re-capture — cosmetic. Observed in the app while capturing: the new-invoice form's Payment Terms control shows "On Receipt" while the Due field is pre-filled +30 days (the script picks Net 30 explicitly).
