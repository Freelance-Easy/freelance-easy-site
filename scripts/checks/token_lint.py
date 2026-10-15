#!/usr/bin/env python3
"""F1 token lint (R7 §4): no raw hex/rgb/hsl, ms/s durations or cubic-bezier in CSS.

Usage: token_lint.py [--json] [--allow-file FILE] FILE.css [...]
Exit 0 = clean, 1 = violations, 2 = usage/IO error.

Exempt: any path containing /assets/fe/ (the app's own CSS); a declaration
carrying `token-lint: allow` in a comment on the same or preceding line; lines
matching a substring listed in --allow-file (one per line, # comments).
Files named site-tokens.css must also pass the line rule: every custom
property is `var(--app-*)`, or marked SITE-ONLY / DEVIATION: in a comment on
its line or the line before.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAW = [
    ("raw-hex", re.compile(r"#[0-9a-fA-F]{3,8}\b")),
    ("raw-colour-fn", re.compile(r"\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(", re.I)),
    ("raw-duration", re.compile(r"(?<![\w.#-])(?:\d+\.?\d*|\.\d+)m?s\b")),
    ("raw-easing", re.compile(r"\bcubic-bezier\(", re.I)),
]
ZERO_TIME = re.compile(r"^0*\.?0+m?s$")
CHUNK = re.compile(r"[^{};]*[{};]|[^{};]+$")


def _blank_comments(text: str) -> tuple[str, list[str]]:
    """Text with comment bodies blanked (newlines kept) + the comment text per line."""
    per_line: dict[int, str] = {}
    out = []
    pos = 0
    for m in re.finditer(r"/\*.*?\*/", text, re.S):
        out.append(text[pos:m.start()])
        start_line = text.count("\n", 0, m.start())
        for i, part in enumerate(m.group(0).split("\n")):
            per_line[start_line + i] = per_line.get(start_line + i, "") + part
        out.append(re.sub(r"[^\n]", " ", m.group(0)))
        pos = m.end()
    out.append(text[pos:])
    n = text.count("\n") + 1
    return "".join(out), [per_line.get(i, "") for i in range(n)]


def lint_text(text: str, name: str = "<css>", allow: list[str] | None = None) -> list[dict]:
    allow = allow or []
    if "/assets/fe/" in name.replace("\\", "/"):
        return []
    clean, comments = _blank_comments(text)
    src_lines = text.splitlines()
    out: list[dict] = []
    is_tokens = Path(name).name == "site-tokens.css"
    pos = 0
    for m in CHUNK.finditer(clean):
        chunk = m.group(0)
        start = pos
        pos = m.end()
        if chunk.endswith("{") or not chunk.strip(" \n\t;}"):
            continue
        body = chunk.rstrip(";}")
        if ":" not in body:
            continue
        first_off = len(body) - len(body.lstrip())
        line0 = clean.count("\n", 0, start + first_off)
        line1 = clean.count("\n", 0, start + len(body))
        ctx = " ".join(comments[max(0, line0 - 1): line1 + 1])
        prop, _, value = body.strip().partition(":")
        prop = prop.strip()
        src_line = src_lines[line0] if line0 < len(src_lines) else ""
        if "token-lint: allow" in ctx or any(a in src_line for a in allow):
            continue
        if is_tokens and prop.startswith("--"):
            v = value.strip()
            if not (v.startswith("var(--app-") or "SITE-ONLY" in ctx or "DEVIATION:" in ctx):
                out.append({"file": name, "line": line0 + 1, "rule": "site-tokens-line",
                            "text": body.strip()[:100]})
            continue
        v = re.sub(r"url\([^)]*\)", "url()", value)  # url(#frag) is not a colour
        for rule, rx in RAW:
            for hit in rx.finditer(v):
                if rule == "raw-duration" and ZERO_TIME.match(hit.group(0)):
                    continue
                out.append({"file": name, "line": line0 + 1, "rule": rule,
                            "text": body.strip()[:100]})
                break
    return out


def main(argv: list[str]) -> int:
    args = argv[1:]
    as_json = "--json" in args
    allow: list[str] = []
    files: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--json":
            pass
        elif a == "--allow-file":
            i += 1
            try:
                allow = [ln.strip() for ln in Path(args[i]).read_text().splitlines()
                         if ln.strip() and not ln.startswith("#")]
            except (IndexError, OSError) as e:
                print(f"token_lint: {e}", file=sys.stderr)
                return 2
        else:
            files.append(a)
        i += 1
    if not files:
        print(__doc__, file=sys.stderr)
        return 2
    found: list[dict] = []
    for f in files:
        try:
            found += lint_text(Path(f).read_text(), f, allow)
        except OSError as e:
            print(f"token_lint: {e}", file=sys.stderr)
            return 2
    if as_json:
        print(json.dumps(found, indent=1))
    else:
        for v in found:
            print(f"{v['file']}:{v['line']}: {v['rule']}: {v['text']}")
        print(f"token_lint: {len(found)} violation(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
