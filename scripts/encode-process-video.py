#!/usr/bin/env python3
"""Cut and encode the raw creation-flow recording for the site.

Input:  a directory written by `capture-process.py --video <dir>`: one .webm from
        Playwright (1440×900, 25 fps) plus marks.json
        ({"list": s, "editor": s, "preview": s, "end": s}).
Output, in --out (default assets/video), one set per app theme (--theme, the
theme the recording was made in; the page swaps sets with its own theme):
  make-an-invoice-loop-<theme>.mp4         the page's silent auto-playing loop,
                                           ~10 s: sped up per segment (SPEEDS),
                                           the finished invoice held for HOLD
                                           seconds before it repeats
  make-an-invoice-loop-<theme>-poster.jpg  the loop's first frame (shown until
                                           the video plays, and instead of it
                                           when it can't)
  make-an-invoice-<theme>.mp4              the same recording in real time,
                                           linked from the caption for anyone
                                           who wants the honest pace
All H.264 yuv420p 1280×800 faststart, no audio.

ffmpeg comes from the system if present, else from the imageio-ffmpeg wheel
(`pip install imageio-ffmpeg`), which bundles a static binary.

Usage:
  python3 scripts/encode-process-video.py <raw-dir> --theme dark [--out assets/video]
  python3 scripts/encode-process-video.py <raw-light-dir> --theme light
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys

# Speed per segment of the loop. Navigation and the finished invoice stay
# readable; the typing is what gets compressed.
SPEEDS = {"navigate": 2.0, "fill": 3.0, "result": 1.5}
HOLD = 1.2  # seconds the last frame is held before the loop repeats
LEAD = 0.3  # seconds of the invoice list shown before the New invoice click
FPS = 30


def ffmpeg_exe() -> str:
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print("need ffmpeg on PATH or `pip install imageio-ffmpeg`", file=sys.stderr)
        raise


def run(ff: str, args: list[str]) -> None:
    subprocess.run([ff, "-y", "-loglevel", "error", *args], check=True)


def duration(ff: str, path: pathlib.Path) -> float:
    """Seconds, read back from the written file (ffmpeg prints it to stderr and exits 1 without an output)."""
    info = subprocess.run([ff, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", info)
    if not m:
        return float("nan")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


X264 = ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-level", "4.0", "-movflags", "+faststart", "-an"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_dir")
    ap.add_argument("--out", default="assets/video")
    ap.add_argument("--theme", choices=("dark", "light"), required=True, help="the app theme the recording was made in")
    ap.add_argument("--width", type=int, default=1280)
    args = ap.parse_args()

    raw_dir = pathlib.Path(args.raw_dir)
    raws = sorted(raw_dir.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not raws:
        print("no .webm in", raw_dir, file=sys.stderr)
        return 1
    raw = raws[-1]
    marks = json.loads((raw_dir / "marks.json").read_text())
    start = max(0.0, marks["list"] - LEAD)
    end = marks["end"] + 0.2
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg_exe()
    height = round(args.width * 900 / 1440 / 2) * 2
    finish = f"scale={args.width}:{height}:flags=lanczos,format=yuv420p"

    # --- the loop: three segments at their own speeds, concatenated, last frame held ---
    segs = [
        (start, marks["editor"], SPEEDS["navigate"]),
        (marks["editor"], marks["preview"], SPEEDS["fill"]),
        (marks["preview"], end, SPEEDS["result"]),
    ]
    chains = [f"[0:v]trim=start={s:.2f}:end={e:.2f},setpts=(PTS-STARTPTS)/{speed}[s{i}]" for i, (s, e, speed) in enumerate(segs)]
    # The hold goes after fps=: tpad sizes stop_duration from the frame rate, which
    # setpts leaves unknown (it padded nothing when placed before the concat).
    graph = (
        ";".join(chains) + ";" + "".join(f"[s{i}]" for i in range(len(segs)))
        + f"concat=n={len(segs)}:v=1:a=0,fps={FPS},tpad=stop_mode=clone:stop_duration={HOLD},{finish}[v]"
    )
    loop = out / f"make-an-invoice-loop-{args.theme}.mp4"
    run(ff, ["-i", str(raw), "-filter_complex", graph, "-map", "[v]", *X264, "-crf", "23", str(loop)])

    poster = out / f"make-an-invoice-loop-{args.theme}-poster.jpg"
    run(ff, ["-ss", f"{start:.2f}", "-i", str(raw), "-frames:v", "1", "-vf", f"scale={args.width}:{height}:flags=lanczos", "-q:v", "3", str(poster)])

    # --- the real-time cut ---
    real = out / f"make-an-invoice-{args.theme}.mp4"
    run(ff, ["-ss", f"{start:.2f}", "-to", f"{end:.2f}", "-i", str(raw), "-vf", finish, *X264, "-crf", "24", str(real)])

    for p in (loop, real):
        print(f"wrote {p} ({p.stat().st_size // 1024} KB, {duration(ff, p):.1f} s)")
    print(f"wrote {poster} ({poster.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
