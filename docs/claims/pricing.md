# /pricing — the sentence ledger (PR-1, 2026-10-16)

Every sentence `src/pages/pricing.html` marks `<!-- NEW COPY -->` is a row below, verbatim, with the source it was
checked against this run and the ruling it relies on. `tests/pages/test_pricing.py::test_every_sentence_logged` pins it:
a sentence on the page with no row here fails the test. Change a sentence = change its row (and re-run fe:claims).

Sources, as read 2026-10-16:
- **Terms** = `src/pages/terms.html` (Terms v2, effective 2026-10-11).
- **LS** = LicenseServer `origin/main` @ ddec001 (`git -C ~/work/ls-w0 show origin/main:<path>`).
- **App** = InvoiceGenerator tag `v0.3.2-beta` (`git -C ~/work/ig-ux-base show v0.3.2-beta:<path>`).
- **2026-10b** = vault `05 - Reference/Renewal Disclosure — 2026-10b.md` (the renewal wording, verbatim; any edit needs
  a version bump, so these rows are copies, never rewrites). LS `server/config.py` `RENEWAL_DISCLOSURE_VERSION = "2026-10b"`.
- **R5** = `_creative-raw/2026-10/site-consolidation/research/R5-legal-claims.md` § C.1 (rulings G1, G1b, G3, G6, G7,
  G8, G10, Seller) and § C.3 (web path).

| # | Sentence | Source | Ruling |
|---|---|---|---|
| 1 | Pricing — Freelance Easy | Page title; the bar's existing "Pricing" label (`src/partials/header.html`) | none needed (a label) |
| 2 | $5 a month or $50 a year. | Terms §2 "Paid ($5 a month or $50 a year …)"; App `templates/_pro_plans.html` plan cards | R5 C.1 G8 (same features both plans) |
| 3 | Try every feature free for seven days, no card. | Terms §2 "Free trial: every feature for seven days … No card."; LS `server/config.py` `_trial_days` default 7 | R5 C.1 draft 2; G1 (no speed claim) |
| 4 | How to buy, how to pay and how to cancel. | The page's own sections (How to buy, Paying, Cancelling) | none needed (describes the page) |
| 5 | Pricing | The bar's existing "Pricing" label | none needed (a heading) |
| 7 | One subscription, no add-ons. | Terms §2 (one paid plan, two billing periods); App `free_tier.py` `PRO_FEATURES["plans"]` "Every feature … for one price" | R5 C.1 G7 (allowed form; never "no extra fees", "$5 total") |
| 8 | Pro: every feature, unlimited invoices and clients. | App `templates/_pro_plans.html` `.plan-fineprint` (verbatim) | R5 C.1 G8 |
| 9 | $5 a month | App `templates/_pro_plans.html` monthly card `$5` `a month` | R5 C.1 G8 |
| 10 | Billed monthly. | 2026-10b monthly card (verbatim); App `templates/_pro_plans.html` | R5 C.1 draft 3 (verbatim, no edit) |
| 11 | Renews every month until you cancel. | 2026-10b monthly card (verbatim) | R5 C.1 draft 3 (verbatim, no edit) |
| 12 | $50 a year | App `templates/_pro_plans.html` annual card `$50` `a year` | R5 C.1 G8 |
| 13 | Two months free. | 2026-10b annual card (verbatim) | R5 C.1 draft 3 (verbatim, no edit) |
| 14 | $4.17 a month, billed once a year. | 2026-10b annual card (verbatim) | R5 C.1 draft 3 (verbatim, no edit) |
| 15 | Renews every year until you cancel. | 2026-10b annual card (verbatim) | R5 C.1 draft 3 (verbatim, no edit) |
| 16 | Cancel any time in Settings, under Manage or cancel subscription. | 2026-10b "under the cards" (verbatim); App `templates/settings.html` button "Manage or cancel subscription" | R5 C.1 renewal wording (verbatim, no edit); DO: cancel route near the price |
| 17 | You keep Pro until the end of the period you've paid for. | 2026-10b (verbatim); Terms §7 "you keep access until the end of the period you've paid for" | R5 C.1 renewal wording (verbatim, no edit) |
| 18 | Plus any tax shown at checkout. | 2026-10b (verbatim); Terms §2 "plus any tax shown at checkout" | R5 C.1 G7 tax ruling (approved sentence) |
| 19 | When the trial ends, nothing is charged: you keep everything you made, and you can make one more invoice free. | Terms §2 "When it ends nothing is charged: you keep everything you made, and you can make one more invoice free."; App `session.py` `DEFAULT_FREE_INVOICE_LIMIT = 1` | R5 C.1 draft 2; G1b/G8 (the free-plan description is on this page) |
| 20 | Not happy with a charge? | Terms §7 "Refunds: if you're unhappy with a charge …" | R5 C.1 draft 5 |
| 21 | Email support@freelance-easy.com within 14 days and we'll refund it in full. | Terms §7 "email support@freelance-easy.com within 14 days of it and we'll refund it in full" | R5 C.1 draft 5; DO: refund near the price |
| 22 | How to buy | Daniel's feedback note ("exactly how to purchase") | none needed (a heading) |
| 23 | Download the app. | `src/pages/install.html` (desktop app, Mac + Windows installers) | R5 C.1 DO (platform notes beside any download: next row) |
| 24 | For Apple Silicon Macs (M1 or later) and Windows 10 or 11, 64-bit. | `src/pages/install.html` Requirements ("M1 or later", "Windows 10 or 11, 64-bit"); `src/pages/index.html` support line | R5 C.1 DO "Apple Silicon Macs (M1 or later)", "Windows 10 or 11, 64-bit" |
| 25 | Intel Macs aren't supported. | `src/pages/install.html` Mac requirements (verbatim) | none beyond R5 C.1 DO |
| 26 | The Windows installer isn't code-signed yet, so Windows shows a security warning when you run it, and some Windows 11 PCs with Smart App Control block it outright: what to do. | `src/pages/install.html#windows` ("the installer isn't code-signed yet … Windows protected your PC"; "some Windows 11 PCs have Smart App Control turned on, which blocks unsigned apps outright"); main's round-two ruling 3 (fe:claims wording) | R5 C.1 (a catch, stated plainly) |
| 27 | Open it and sign in with Google. | `src/pages/install.html` "Both versions ask you to sign in with Google the first time" | R5 C.1 G1 (no time claim beside sign-in) |
| 28 | Your seven-day trial starts the first time you sign in, one trial per account. | LS `server/services/subscriptions.py` header (clock starts at the first sign-in from a trial-aware app; `sign_in_trial_ends_at`); Terms §2 "starting the first time you sign in … (one trial per account)" | R5 C.1 trial fact; G1 |
| 29 | To subscribe, click See plans in the app, then Continue monthly or Continue yearly. | App `templates/base.html` trial and free-plan bars "See plans"; `templates/settings.html` "See plans"; `templates/_pro_plans.html` buttons "Continue yearly", "Continue monthly" | R5 C.1 (the app path is today's only path) |
| 30 | Checkout opens in your browser. | App `templates/_pro_plans.html` comment ("Stripe opens in the user's browser, never inside the app window") | none beyond R5 C.1 Seller |
| 31 | Start on the web | Web-account contract snapshot `children/E-web-account-contract.md` § 6 (`data-flag="web-signup"`, PR-1 web path) and § 2 (`/start`) | R5 C.3: hidden placeholder only, no purchase flow, no consent wording; shown only when the web path ships |
| 32 | Paying | Daniel's feedback note ("exactly how to pay") | none needed (a heading) |
| 33 | Payment is handled by Stripe; checkout shows the seller. | Terms §7 "Who sells and processes your subscription"; LS `server/config.py` `STRIPE_MANAGED_PAYMENTS` (default off; the live value is unread) | R5 C.1 Seller (verbatim; never name the seller) |
| 34 | Prices are set in US dollars. | Terms §7 "Prices and tax: prices are set in U.S. dollars." | R5 C.1 G7/G8 (no tax-included claim) |
| 35 | Checkout shows the currency and the full total, including any tax, before you pay. | Terms §7 "checkout may show the price in your local currency … Checkout always shows the full total before you pay." | R5 C.1 G7 tax ruling (approved sentence, verbatim) |
| 36 | Have a promotion code? | App `templates/_pro_plans.html` `.plan-promo` (verbatim); LS `server/routes/billing.py` `"allow_promotion_codes": True` | none beyond G7 |
| 37 | There is a field for it at checkout. | App `templates/_pro_plans.html` `.plan-promo` (verbatim); LS `billing.py` `allow_promotion_codes` | none beyond G7 |
| 38 | Before you buy | Daniel's feedback note ("all the gotchas") | none needed (a heading) |
| 39 | After the trial, these need a subscription: Reports, recurring invoices, sending email from the app, your logo and colors, all four templates, documents, automatic backups, your own invoice numbers and default notes. | App `free_tier.py` `PRO_FEATURES` (reports, recurring, email, theme, templates, documents, backup, numbering, notes) | R5 C.1 draft 2; DO "list the Pro features by name"; G1b/G8 |
| 40 | Opening and downloading your invoices isn't a Pro feature: the free plan and a lapsed subscription can do both. | App `free_tier.py`: not in `PRO_FEATURES`; `PRO_EXEMPT_ENDPOINTS` (`backup.zip_all`); `LAPSED_READABLE` (`invoices.invoice_detail`, `invoices.invoice_pdf`, `backup.zip_all`) | R5 C.1 free-plan fact; main's round-two ruling 2 (fe:claims wording, no absolute) |
| 41 | One person per account. | Terms §3 (verbatim) | R5 C.1 "for one person" (Terms §3), never "on one computer" |
| 42 | If more people in your business need the app, each needs their own account. | Terms §3 (verbatim) | R5 C.1 (Terms §3) |
| 43 | You can install it on the computers you own or control. | Terms §4 "install and use the app on computers you own or control" | R5 C.1 "Do not copy … on one computer" (Terms §4) |
| 43a | The app checks your subscription when it starts. | Terms §8 "The app checks your subscription with our server when it starts and after you sign in." | main's round-two ruling 4 (Terms §8 facts only) |
| 43b | A subscribed app keeps working offline for at least seven days after its last successful check, then asks you to sign in again; your files stay on your computer. | Terms §8 "a subscribed app keeps working offline for at least seven days after its last successful check … After that, the app asks you to sign in again before it opens; your files stay on your computer." | main's round-two ruling 4 (Terms §8 facts only); G6 (no "never leaves") |
| 44 | There's no minimum term. | Terms §7 (verbatim) | R5 C.1 (renewal terms near the price) |
| 45 | Cancelling, refunds and price changes | Terms §7 | none needed (a heading) |
| 46 | You can also cancel by emailing support@freelance-easy.com. | Terms §7 "Cancel any time: … or by emailing support@freelance-easy.com" | R5 C.1; 2026-10-18 release check (qa/PRICING-release-claims.md): the Link clause dropped — Managed Payments is off in production, no checkout names Link, the route is unverified |
| 47 | Cancelling stops the next renewal. | Terms §7 (verbatim) | R5 C.1 |
| 48 | When the period you've paid for ends, the app turns read-only the next time you open it or sign in. | App `session.py` `plan_state` (`canceled` → `PLAN_LAPSED`, "read-only"); `free_tier.py` docstring "A LAPSED subscription … is read-only: it can open and download everything it made", `LAPSED_READABLE` | R5 C.1 "A lapsed subscription is read-only"; 2026-10-18 release check: the switch happens at the next app start or sign-in, no grace period, not "at once" |
| 49 | Cancelling doesn't refund the rest of a period you've paid for, except as the Terms describe. | Terms §7 (14-day refund, billing mistakes, rights the law gives you), §10 (refund on cancelling over a Service change), §11 (refund of the unused period on cancelling over new terms), §12 (termination) | R5 C.1 refund fact; main's round-two ruling 1 |
| 50 | If we change the price of your plan, we'll email you between 14 and 30 days before your first renewal at the new price. | Terms §7 "Price changes" (verbatim opening) | R5 C.1 price-change fact |
| 51 | The full rules are in the Terms: §2 for the trial and plans, §7 for payment, cancelling and refunds. | Terms §2 "What you get", §7 "Payment" | none needed (a pointer) |

## Omitted — needs Daniel

Not on the page because neither Terms nor code proves it:
- **Payment methods shown at checkout.** LS `billing.py` never passes `payment_method_types` (Stripe decides per
  buyer), so no list is provable.
- **Switching between monthly and yearly.** No in-app switch route found in the v0.3.2-beta templates; the Stripe
  portal's plan-switch setting is dashboard-only (unread).
- **A failed payment.** It makes the app read-only at once (`past_due` → `PLAN_LAPSED`, App `session.py` `plan_state`), not at the end of the period; the Terms are silent on it.
- **Live values not read:** `FREE_TRIAL_DAYS` and `STRIPE_MANAGED_PAYMENTS` on Railway (the page relies on the code default of 7 days and on Terms §2), and the Stripe portal's "cancel at period end" setting (the page relies on Terms §7 and the 2026-10b wording).
- **Who the seller is.** Managed Payments' live state (`STRIPE_MANAGED_PAYMENTS` on Railway) is unread; the page only
  says checkout shows the seller.
