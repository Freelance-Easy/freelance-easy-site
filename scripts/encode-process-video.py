#!/usr/bin/env python3
"""Trim and encode the raw creation-flow recording for the site.

Input:  a directory written by `capture-process.py --video <dir>`: one .webm from
        Playwright plus marks.json ({"list": s, "editor": s, "preview": s, "end": s}).
Output: assets/video/make-an-invoice.mp4 (H.264, yuv420p, 1280×800, faststart)
        assets/video/make-an-invoice-poster.jpg (a frame from the line items being typed)

ffmpeg comes from the system if present, else from the imageio-ffmpeg wheel
(`pip install imageio-ffmpeg`), which bundles a static binary.

Usage:
  python3 scripts/encode-process-video.py <raw-dir> [--out assets/video]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys


def ffmpeg_exe() -> str:
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print("need ffmpeg on PATH or `pip install imageio-ffmpeg`", file=sys.stderr)
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_dir")
    ap.add_argument("--out", default="assets/video")
    ap.add_argument("--width", type=int, default=1280)
    args = ap.parse_args()

    raw_dir = pathlib.Path(args.raw_dir)
    raws = sorted(raw_dir.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not raws:
        print("no .webm in", raw_dir, file=sys.stderr)
        return 1
    raw = raws[-1]
    marks = json.loads((raw_dir / "marks.json").read_text())
    start = max(0.0, marks["list"] - 0.4)
    end = marks["end"] + 0.2
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg_exe()
    height = round(args.width * 900 / 1440 / 2) * 2

    mp4 = out / "make-an-invoice.mp4"
    subprocess.run(
        [
            ff, "-y", "-loglevel", "error",
            "-ss", f"{start:.2f}", "-to", f"{end:.2f}", "-i", str(raw),
            "-vf", f"scale={args.width}:{height}:flags=lanczos,format=yuv420p",
            "-c:v", "libx264", "-preset", "slow", "-crf", "24", "-profile:v", "high", "-level", "4.0",
            "-movflags", "+faststart", "-an",
            str(mp4),
        ],
        check=True,
    )
    poster = out / "make-an-invoice-poster.jpg"
    subprocess.run(
        [
            ff, "-y", "-loglevel", "error",
            # the line items being typed — distinct from the "new invoice" frame that sits above the video on the page
            "-ss", f"{marks['editor'] + 13.5:.2f}", "-i", str(raw), "-frames:v", "1",
            "-vf", f"scale={args.width}:{height}:flags=lanczos", "-q:v", "3",
            str(poster),
        ],
        check=True,
    )
    dur = end - start
    print(f"wrote {mp4} ({mp4.stat().st_size // 1024} KB, {dur:.1f} s) and {poster} ({poster.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
