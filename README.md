# Freelance Easy — landing page

Static landing page for [freelance-easy.com](https://freelance-easy.com). Plain HTML + CSS + a tiny bit of JS — no build step, no framework. Drops straight into Cloudflare Pages.

> **Deploying this?** Read **[HANDOFF.md](./HANDOFF.md)** first — it has the full canonical-fact compliance audit, framework decisions, and known TODOs.

## Local development

There is no build. Just open the folder in any static server.

```bash
# pick one
npx serve .
python3 -m http.server 8000
# or use VS Code Live Server
```

Then visit `http://localhost:8000`.

## Cloudflare Pages

| Setting | Value |
| --- | --- |
| Build command | _(leave blank)_ |
| Build output directory | `/` (the repo root) |
| Root directory | `/` |
| Node version | _(not used)_ |

Cloudflare Pages picks up `_redirects`, `_headers`, and `404.html` automatically.

## File map

```
freelance-easy-site/
├── index.html              landing page
├── privacy.html            placeholder
├── terms.html              placeholder
├── 404.html                branded 404
├── styles.css              all styles, dark default + light scope
├── script.js               theme toggle + OS-aware CTA reorder
├── favicon.ico
├── robots.txt
├── sitemap.xml
├── _redirects              /download/win, /download/mac, etc.
├── _headers                cache + security headers
├── assets/
│   ├── logo.svg
│   ├── og-image.png        1200×630 social card
│   └── fonts/              vendored Inter + Playfair (Inter currently inert; see HANDOFF)
├── HANDOFF.md              ← read this before deploying
└── README.md
```

## Hardcoded URLs

- **Windows download** — `https://github.com/Freelance-Easy/InvoiceGenerator-releases/releases/latest/download/Freelance-Easy-Setup.exe` (stable filename via electron-builder `artifactName`; never moves per release)
- **Mac download** — `https://github.com/Freelance-Easy/InvoiceGenerator-releases/releases/latest/download/Freelance-Easy.dmg` (Apple Silicon arm64, signed + notarized; same stable-filename convention as Windows)
- **All releases** — `https://github.com/Freelance-Easy/InvoiceGenerator-releases/releases`
- **Contact** — `mailto:support@freelance-easy.com`
- **Privacy email** — `mailto:privacy@freelance-easy.com`
- **Pretty redirect URLs** — `/download/win`, `/download/mac`, `/download`, `/releases` (see `_redirects`)

## Things to wire up later

- `<!-- ANALYTICS: insert tracking script here when ready -->` in `<head>` of every HTML file — drop Plausible or Cloudflare Web Analytics here.
- Real privacy & terms copy — currently honest placeholders.
- Real OG image — current is a generated text card; replace with a richer screenshot when one is ready (`assets/og-image.png`, 1200×630).
- **Universal Mac binary** — current Mac build is arm64-only (Apple Silicon). When Intel Mac support becomes a need, expand the electron-builder `mac.target.arch` from `["arm64"]` to `["universal"]` in `electron/package.json` of the InvoiceGenerator repo, plus the corresponding PyInstaller universal2 merge step. URL stays the same.

## Browser support

Targeted at modern evergreen browsers (Chrome/Edge/Safari/Firefox last 2 versions). Graceful degradation: no JS = no theme toggle, no OS-aware reorder; Windows download button still visible and functional.

## License

Source for the landing page is private. The product itself is closed-source during beta.
