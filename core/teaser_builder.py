"""Builds the pre-episode teaser: a 10-15s whisper-toned hook clip that
does NOT resolve the mystery, meant to be published exactly N minutes
before the main episode drops, at the channel's best viewing time.

Does not decide *when* to publish — see scripts/best_time.py for that.
This module only renders the teaser video file itself.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def build_teaser(
    logo_path: Path,
    hook_audio: Path,
    background_clip: Path,
    output_path: Path,
    max_duration: float = 15.0,
    resolution: str = "1080x1920",
    watermark_opacity: float = 0.9,
) -> Path:
    """background_clip: a short atmospheric scene clip (no dialogue) that sets
    the mood; hook_audio: the whisper narration line, e.g. assets/audio/whisper_hook_sample.mp3
    or a freshly-generated XTTS line for this episode."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = resolution.split("x")

    # Small static logo bug in the corner for the teaser (kept simple —
    # full periodic watermark logic lives in core.watermark for long-form).
    filter_complex = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}[bg];"
        f"[1:v]scale=iw*0.15:-1,format=rgba,colorchannelmixer=aa={watermark_opacity}[logo];"
        f"[bg][logo]overlay=x=main_w-overlay_w-40:y=40[vout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-t", str(max_duration), "-i", str(background_clip),
        "-i", str(logo_path),
        "-i", str(hook_audio),
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "2:a",
        "-t", str(max_duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the pre-episode teaser clip.")
    parser.add_argument("--logo", type=Path, required=True)
    parser.add_argument("--hook-audio", type=Path, required=True)
    parser.add_argument("--background-clip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config/channel_profile.json"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))["teaser"]
    max_dur = cfg["duration_seconds"][1]
    build_teaser(
        logo_path=args.logo,
        hook_audio=args.hook_audio,
        background_clip=args.background_clip,
        output_path=args.output,
        max_duration=max_dur,
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
