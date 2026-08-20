"""Builds the after-episode Short: hook + unresolved question, ending with a
CTA back to the full episode. Also writes the required growth_metrics.json
sidecar file described in the SEO strategy doc.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def build_short(
    scene_clip: Path,
    narration_audio: Path,
    output_path: Path,
    resolution: str = "1080x1920",
    max_duration: float = 59.0,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = resolution.split("x")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(scene_clip),
        "-i", str(narration_audio),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
        "-map", "0:v", "-map", "1:a",
        "-t", str(max_duration),
        "-shortest",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    return output_path


def write_growth_metrics(
    episode_id: str,
    title_variant: str,
    thumbnail_variant: str,
    tts_backend: str,
    publish_time_utc: str,
    related_long_video_id: str,
    output_path: Path,
) -> Path:
    """Schema per the channel's SEO strategy doc (section 10):
    episode_id, title_variant, thumbnail_variant, tts_backend, publish time,
    plus the Short's link back to the long-form video."""
    payload = {
        "episode_id": episode_id,
        "title_variant": title_variant,
        "thumbnail_variant": thumbnail_variant,
        "tts_backend": tts_backend,
        "publish_time_utc": publish_time_utc,
        "related_long_video_id": related_long_video_id,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the after-episode Short + growth_metrics.json")
    parser.add_argument("--scene-clip", type=Path, required=True)
    parser.add_argument("--narration-audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--title-variant", required=True)
    parser.add_argument("--thumbnail-variant", required=True)
    parser.add_argument("--tts-backend", default="xtts_v2")
    parser.add_argument("--publish-time-utc", required=True)
    parser.add_argument("--related-long-video-id", required=True)
    parser.add_argument("--metrics-output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    build_short(args.scene_clip, args.narration_audio, args.output)
    write_growth_metrics(
        episode_id=args.episode_id,
        title_variant=args.title_variant,
        thumbnail_variant=args.thumbnail_variant,
        tts_backend=args.tts_backend,
        publish_time_utc=args.publish_time_utc,
        related_long_video_id=args.related_long_video_id,
        output_path=args.metrics_output,
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
