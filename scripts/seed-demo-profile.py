#!/usr/bin/env python3
"""Seed the site's fictional demo account into a THROWAWAY InvoiceGenerator dev profile.

Every product image on the site is captured from the DEV app signed in as this
account: the dashboard shots (capture-screenshots.py), the hero sheets and the
sample PDFs (build-hero-collage.py render), the making-an-invoice recording
(capture-process.py). The data is the shared fictional account the ads use
(the invoice-film chat's dashboard kit, DASH-KIT.md), so the site, /mac and the
ads show one world:

  - the persona Jordan Wexcombe, jordan@example.com, Nashville (renamed on
    2026-10-04 under legal G11; the earlier demo names, all retired, are
    listed in the private NAMES-LOG below, never in this public repo);
  - four clients, each invented and web-searched before use (G11 rule 1; the
    log, query and date: _creative-raw/2026-09/spike/invoice-film/data/NAMES-LOG.md);
  - 26 invoices, INV1031–INV1056, Nov 2025 – Oct 2026, $75 an hour, monthly
    totals rising through the year. INV1056 (Halvard & Wren, $1,500) is the
    hero invoice, the ads' invoice. INV1049 is the one overdue invoice, on a
    name that passed the search (G11 rule 4);
  - contact details in reserved ranges (rule 3): emails on *.example or
    example.com, no phone numbers, city-only addresses. Notes and line items
    name no payment service, bank or software (rule 2).

Safety: it creates the profile directory itself and refuses one that already
exists, so nothing inside it (a symlink into real data, say) can predate the
run. It refuses a path inside Dropbox, Application Support, iCloud or any
.dev-profile. The app's own dev-profile guards run before the data folder is
made, and the data root, the account folder and the database file must all
resolve inside the profile before the first database write; every write goes
through the app's db API. Folder sync is off in this process, so the rows land
in the account's pre-sync users/<id>/invoices.db, which the app brings up
(imports) at its first sign-in.

Run it with the InvoiceGenerator venv against a checkout of the RELEASED app
(the screenshots must show what ships):
  git -C <InvoiceGenerator> worktree add --detach /tmp/ig-release v0.3.0-beta
  <InvoiceGenerator>/venv/bin/python scripts/seed-demo-profile.py \
      --profile /tmp/fe-demo-profile --app-dir /tmp/ig-release
Then run that checkout in dev mode with FE_DEV_PROFILE=<profile> (it serves
:50506, never the installed app's :50505), sign in as "Daniel (Google, active)"
against the local mock LicenseServer, and run the capture scripts.
"""
from __future__ import annotations

import argparse
import calendar
import os
import pathlib
import sys
from datetime import date, timedelta

USER_ID = "google_oauth_sub_daniel_001"  # the mock user behind "Daniel (Google, active)"

PERSONA = {"name": "Jordan Wexcombe", "city": "Nashville", "state": "TN", "country": "US", "email": "jordan@example.com"}
NOTE = "Thanks for the work — payment by bank transfer within terms."
STYLE, ACCENT = "modern", "#4a7c7e"  # the ads' template and accent (invoice-film data/inv1056.json)
RATE = 75

# name → (billing email, default terms). Terms: 30 days, or on receipt.
CLIENTS = {
    "Halvard & Wren": ("hello@halvardwren.example", "net_30"),
    "Ostrander & Bell": ("accounts@ostranderbell.example", "net_30"),
    "Quillmont Roasters": ("billing@quillmontroasters.example", "net_30"),
    "Larkhaven Audio": ("studio@larkhavenaudio.example", "on_receipt"),
}

# (number, created, client, total, paid?) — the kit's rows, $75 an hour.
INVOICES = [
    (1031, "2025-11-06", "Ostrander & Bell", 900, True),
    (1032, "2025-11-20", "Quillmont Roasters", 750, True),
    (1033, "2025-12-04", "Halvard & Wren", 1200, True),
    (1034, "2026-01-08", "Ostrander & Bell", 1125, True),
    (1035, "2026-01-22", "Quillmont Roasters", 750, True),
    (1036, "2026-02-05", "Halvard & Wren", 1425, True),
    (1037, "2026-03-05", "Ostrander & Bell", 1200, True),
    (1038, "2026-03-19", "Quillmont Roasters", 900, True),
    (1039, "2026-04-02", "Halvard & Wren", 1350, True),
    (1040, "2026-04-23", "Quillmont Roasters", 600, True),
    (1041, "2026-05-07", "Ostrander & Bell", 1425, True),
    (1042, "2026-05-21", "Quillmont Roasters", 900, True),
    (1043, "2026-06-04", "Halvard & Wren", 1275, True),
    (1044, "2026-06-18", "Quillmont Roasters", 750, True),
    (1045, "2026-07-18", "Larkhaven Audio", 750, True),
    (1046, "2026-07-28", "Ostrander & Bell", 1800, True),
    (1047, "2026-08-04", "Halvard & Wren", 1350, True),
    (1048, "2026-08-14", "Quillmont Roasters", 600, True),
    (1049, "2026-08-27", "Ostrander & Bell", 450, False),  # due Sep 26: the overdue one
    (1050, "2026-09-02", "Ostrander & Bell", 1200, True),
    (1051, "2026-09-11", "Quillmont Roasters", 675, False),  # due Oct 11
    (1052, "2026-09-23", "Halvard & Wren", 900, True),
    (1053, "2026-10-01", "Quillmont Roasters", 750, True),
    (1054, "2026-10-02", "Ostrander & Bell", 525, True),
    (1055, "2026-10-02", "Larkhaven Audio", 375, True),
]
# The hero: INV1056 exactly as the ads show it (invoice-film data/inv1056.json).
HERO = {
    "number": 1056,
    "created": "2026-10-05",
    "client": "Halvard & Wren",
    "title": "October work",
    "items": [("Project work", RATE, 16), ("Revisions", RATE, 4)],
}
NEXT_NUMBER = 1057

# The kit's monthly table (DASH-KIT.md), by creation month: paid, open.
EXPECTED_MONTHS = {
    "2025-11": (1650, 0), "2025-12": (1200, 0), "2026-01": (1875, 0), "2026-02": (1425, 0),
    "2026-03": (2100, 0), "2026-04": (1950, 0), "2026-05": (2325, 0), "2026-06": (2025, 0),
    "2026-07": (2550, 0), "2026-08": (1950, 450), "2026-09": (2100, 675), "2026-10": (1650, 1500),
}


def due(created: str, terms: str) -> str:
    if terms == "on_receipt":
        return "On Receipt"
    return (date.fromisoformat(created) + timedelta(days=int(terms.split("_")[1]))).isoformat()


def check_dataset() -> None:
    """The rows still add up to the kit's documented numbers."""
    months: dict[str, list[int]] = {}
    for _num, created, _client, total, paid in INVOICES:
        assert total % RATE == 0, (_num, total)
        m = months.setdefault(created[:7], [0, 0])
        m[0 if paid else 1] += total
    hero_total = sum(rate * qty for _d, rate, qty in HERO["items"])
    assert hero_total == 1500, hero_total
    months.setdefault(HERO["created"][:7], [0, 0])[1] += hero_total
    assert {k: tuple(v) for k, v in months.items()} == EXPECTED_MONTHS, months
    ytd = sum(t for _n, c, _cl, t, paid in INVOICES if paid and c.startswith("2026"))
    assert ytd == 19950, ytd  # the kit's Collected YTD before INV1056 is paid


def refuse_real_storage(profile: pathlib.Path, app_dir: pathlib.Path) -> None:
    if any(part.startswith(".dev-profile") for part in profile.parts):
        sys.exit(f"refusing: the profile must not be inside a .dev-profile: {profile}")
    home = pathlib.Path.home()
    real = [home / "Library" / "Application Support", home / "Library" / "CloudStorage",
            home / "Library" / "Mobile Documents", app_dir / ".dev-profile"]
    real += [p for p in (home / "Dropbox", home / "MUSIC PRODUCTION" / "Dropbox") if p.exists()]
    for r in real:
        r = r.resolve()
        if profile == r or r in profile.parents:
            sys.exit(f"refusing: the profile must be a throwaway directory, not under {r}: {profile}")


def require_inside(path: str | None, profile: pathlib.Path, what: str) -> None:
    """`path`, with every symlink resolved, lies inside the profile."""
    real = pathlib.Path(os.path.realpath(path)) if path else None
    if real is None or (real != profile and profile not in real.parents):
        sys.exit(f"refusing: the {what} {path!r} resolves outside the profile {profile}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, help="a throwaway directory that doesn't exist yet")
    ap.add_argument("--app-dir", required=True, help="an InvoiceGenerator checkout at the release tag")
    args = ap.parse_args()
    profile = pathlib.Path(args.profile).expanduser().resolve()
    app_dir = pathlib.Path(args.app_dir).expanduser().resolve()
    refuse_real_storage(profile, app_dir)
    check_dataset()
    try:
        profile.mkdir(parents=True)  # exclusive: nothing inside it predates this run
    except FileExistsError:
        sys.exit(f"refusing: {profile} already exists (seed into a new directory)")

    os.environ["FE_DEV_PROFILE"] = str(profile)
    os.environ["INVOICEGEN_LICENSE_DEV_MODE"] = "1"
    os.environ.pop("INVOICEGEN_PORT", None)
    sys.path.insert(0, str(app_dir))
    os.chdir(app_dir)

    import config  # noqa: E402  (the app's own; resolves every path inside the profile)

    config.ensure_dev_profile_configured()
    config.assert_dev_profile_isolation()
    require_inside(config.get_data_dir(), profile, "data root")

    import db  # noqa: E402
    import folder_sync  # noqa: E402

    folder_sync.configure(enabled=False, threads=False)
    config.set_current_user_id_override(USER_ID)
    config.ensure_data_dirs()
    config.ensure_user_data_dirs()
    data_dir = pathlib.Path(config.get_user_data_dir() or "").resolve()
    require_inside(str(data_dir), profile, "account folder")
    require_inside(config.get_db_path(), profile, "database")
    db.init_db()
    if db.get_clients() or db.get_invoices():
        sys.exit("refusing: this account already has data (seed a fresh profile)")
    print("seeding", data_dir)

    # An account a year in: a backup folder is set, so the dashboard's "Set up a
    # backup folder" nudge stays out of the shots (the ads' dashboard has no such
    # row; auto backup stays off, so nothing is ever written there), and its
    # first PDF is long downloaded, so the "Get started" card is complete.
    backup = profile / "backup"
    backup.mkdir(exist_ok=True)
    db.update_settings(**PERSONA, default_notes=NOTE, default_notes_enabled=1, invoice_prefix="INV",
                       invoice_number_format="prefix_number", invoice_style=STYLE, accent_color=ACCENT,
                       backup_folder_path=str(backup), backup_auto_enabled=0,
                       first_pdf_at=f"{INVOICES[0][1]}T10:00:00")

    ids = {}
    for name, (email, terms) in CLIENTS.items():
        ids[name] = db.create_client(name=name, city="Nashville", state="TN", country="US", email=email,
                                     default_payment_terms=terms)

    def create(num: int, created: str, client: str, title: str, items: list[tuple[str, int, int]]) -> int:
        terms = CLIENTS[client][1]
        return db.create_invoice(invoice_number=f"INV{num}", title=title, client_id=ids[client],
                                 date_created=created, date_due=due(created, terms), notes=NOTE,
                                 payment_terms=terms,
                                 line_items=[{"description": d, "rate": r, "quantity": q} for d, r, q in items])

    for num, created, client, total, paid in INVOICES:
        month = calendar.month_name[int(created[5:7])]
        inv_id = create(num, created, client, f"{month} work", [("Project work", RATE, total // RATE)])
        if paid:
            db.toggle_invoice_status(inv_id)
    create(HERO["number"], HERO["created"], HERO["client"], HERO["title"], HERO["items"])
    db.update_settings(next_invoice_number=NEXT_NUMBER)

    invoices = db.get_invoices()
    assert len(invoices) == len(INVOICES) + 1, len(invoices)
    assert sorted(c["name"] for c in db.get_clients()) == sorted(CLIENTS)
    print(f"{len(CLIENTS)} clients, {len(invoices)} invoices (INV1031–INV1056); next number INV{NEXT_NUMBER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
