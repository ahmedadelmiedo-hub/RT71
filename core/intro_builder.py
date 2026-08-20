"""Builds the short branded intro clip: logo fade-in over the jingle sting.

This is separate from core.watermark — this is the full-screen opening card
(2-3s) shown once at the start of every video, not the periodic small logo
that appears/disappears throughout.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def build_intro_clip(
    logo_path: Path,
    jingle_path: Path,
    output_path: Path,
    duration: float = 3.0,
    jingle_start: float = 0.0,
    resolution: str = "1080x1920",
    fade_seconds: float = 0.4,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = resolution.split("x")

    filter_complex = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black@0,"
        f"format=yuva420p,"
        f"fade=t=in:st=0:d={fade_seconds}:alpha=1,"
        f"fade=t=out:st={duration - fade_seconds:.2f}:d={fade_seconds}:alpha=1[vout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration), "-i", str(logo_path),
        "-ss", str(jingle_start), "-t", str(duration), "-i", str(jingle_path),
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the branded opening intro clip.")
    parser.add_argument("--logo", type=Path, required=True)
    parser.add_argument("--jingle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument("--jingle-start", type=float, default=0.0)
    parser.add_argument("--resolution", default="1080x1920")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    build_intro_clip(
        logo_path=args.logo,
        jingle_path=args.jingle,
        output_path=args.output,
        duration=args.duration,
        jingle_start=args.jingle_start,
        resolution=args.resolution,
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
