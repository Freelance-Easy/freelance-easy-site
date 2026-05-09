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
