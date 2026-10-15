#!/usr/bin/env python3
"""Digest scratch/cp-spike/evidence/ into the numbers quoted in docs/cp-spike-verdict.md.

  python3 "<worktree>/scratch/cp-spike/digest.py"            # prints the matrix, counts and the measured facts
"""
import json, pathlib, collections

E = pathlib.Path(__file__).resolve().parent / "evidence"
COLS = ["chromium", "webkit", "webkit-iphone"]


def load(col, name):
    p = E / col / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def main():
    summ = json.loads((E / "summary.json").read_text())
    cells = summ["cells"]
    rows = sorted({k.split("|")[0] for k in cells})
    print("| row | " + " | ".join(COLS) + " |")
    for r in rows:
        print(f"| {r} | " + " | ".join(cells.get(f"{r}|{c}", "-") for c in COLS) + " |")
    cnt = {c: collections.Counter(cells.get(f"{r}|{c}") for r in rows if not r.startswith("S")) for c in COLS}
    print("\ncounts over R1-R9:", {c: dict(v) for c, v in cnt.items()})
    runs = collections.Counter(r["status"] for r in summ["results"])
    print("individual runs:", dict(runs), "of", len(summ["results"]))
    print("retried after a first-attempt FAIL:", [(r["column"], r["viewport"][:2], r["row"], r["variant"], r["status"]) for r in summ["results"] if r.get("retried")])
    for r in summ["results"]:
        if r["status"] == "FAIL":
            print("  FAIL", r["column"], r["viewport"], r["row"], r["variant"], r["failed"])

    print("\n-- measured facts --")
    for col, vp in (("chromium", "1440x900"), ("webkit", "1440x900"), ("webkit-iphone", "390x664")):
        r1 = load(col, f"R1__{vp}")
        if r1:
            d = r1["data"]
            print(f"R1 {col}: native scrollend={d.get('native_scrollend')} scrollTo synchronous={d.get('scrollTo_applied_synchronously')}"
                  f" events/sync={collections.Counter((p['acks'], p['scrollend']) for p in d.get('events_per_sync', []))}")
        r3 = load(col, f"R3__{vp}")
        if r3:
            print(f"R3 {col}: settle trigger={r3['data'].get('settle_trigger')} latency={r3['data'].get('settle_latency_ms')} ms wheel path={r3['data'].get('wheel_path')}")
        for v in ("", "-nograce"):
            r6 = load(col, f"R6__{vp}{v}")
            if r6:
                print(f"R6{v} {col}: settles={len(r6['data'].get('settles', []))} scrollend during stream={r6['data'].get('scrollend_during')} status={r6['status']}")
        r7 = load(col, f"R7__{vp}")
        if r7:
            print(f"R7 {col}: idle latency={r7['data'].get('latency_ms')} ms")
        for v in ("", "-classicbar"):
            r5 = load(col, f"R5__{vp}{v}")
            if r5:
                d = r5["data"]
                print(f"R5{v} {col}: bar={d.get('scrollbar_px')} px status={r5['status']} mouseup_seen={d.get('mouseup_seen')}"
                      f" undetected stationary hold settles after 1 s={d.get('undetected_hold_settles_after_1s')}")
        r8 = load(col, f"R8__{vp}")
        if r8:
            ge = r8["data"].get("geometry_events", [])
            print(f"R8 {col}: pointer coarse={r8['data'].get('pointer_coarse')} touch steps={r8['data'].get('touch_steps')}"
                  f" bar-change geometry same={[g.get('same') for g in ge]}")
        r9 = load(col, f"R9__{vp}")
        if r9:
            d = r9["data"]
            print(f"R9 {col}: legacyZoom={d.get('legacyZoom')} ctrl-wheel={d.get('ctrl_wheel')} pinch vvScale={d.get('pinch_vvScale')}")
    for col in COLS:
        for vp in ("844x390",):
            r4 = load(col, f"R4__{vp}")
            if r4:
                print(f"R4 {col} {vp}: released={r4['data'].get('released')} resize-grace snaps={r4['data'].get('resize_grace_snaps')}")


if __name__ == "__main__":
    main()
