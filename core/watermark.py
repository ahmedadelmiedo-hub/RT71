"""Periodic, corner-hopping watermark overlay.

Builds an ffmpeg filter graph that shows the channel logo for a few seconds,
hides it, then re-shows it in a different (randomly chosen) corner — instead
of a static always-on watermark. This mirrors the "appears/disappears, moves
around" behavior requested for the روايات الواقع intro/branding pack.

Usage:
    python -m core.watermark --input episode.mp4 --logo assets/branding/rawaat_original_transparent.png \
        --output episode_watermarked.mp4 --config config/channel_profile.json
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
from pathlib import Path


def _probe_duration(video_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(video_path),
        ],
        check=True, capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def _probe_dimensions(video_path: Path) -> tuple[int, int]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0", str(video_path),
        ],
        check=True, capture_output=True, text=True,
    )
    width_str, height_str = result.stdout.strip().split("x")
    return int(width_str), int(height_str)


def _corner_position(corner: str, margin: int, logo_w: int, logo_h: int, frame_w: int, frame_h: int) -> tuple[int, int]:
    positions = {
        "top_left": (margin, margin),
        "top_right": (frame_w - logo_w - margin, margin),
        "bottom_left": (margin, frame_h - logo_h - margin),
        "bottom_right": (frame_w - logo_w - margin, frame_h - logo_h - margin),
    }
    if corner not in positions:
        raise ValueError(f"unknown corner: {corner}")
    return positions[corner]


def build_cycles(duration: float, visible_seconds: float, hidden_seconds: float, corners: list[str], rng: random.Random) -> list[dict]:
    """Compute (start, end, corner) windows covering the whole video, avoiding
    the same corner twice in a row so the movement reads as intentional."""
    cycles: list[dict] = []
    t = 0.0
    last_corner = None
    period = visible_seconds + hidden_seconds
    while t < duration:
        start = t
        end = min(t + visible_seconds, duration)
        choices = [c for c in corners if c != last_corner] or corners
        corner = rng.choice(choices)
        cycles.append({"start": start, "end": end, "corner": corner})
        last_corner = corner
        t += period
    return cycles


def apply_watermark(
    video_path: Path,
    logo_path: Path,
    output_path: Path,
    width_percent: float = 0.20,
    margin_percent: float = 0.04,
    visible_seconds: float = 3.0,
    hidden_seconds: float = 11.0,
    corners: list[str] | None = None,
    opacity: float = 0.85,
    seed: int | None = None,
) -> Path:
    corners = corners or ["top_left", "top_right", "bottom_left", "bottom_right"]
    rng = random.Random(seed)

    duration = _probe_duration(video_path)
    frame_w, frame_h = _probe_dimensions(video_path)

    logo_w = int(frame_w * width_percent)
    margin = int(frame_w * margin_percent)

    cycles = build_cycles(duration, visible_seconds, hidden_seconds, corners, rng)
    if not cycles:
        raise ValueError("video too short to place any watermark cycle")

    # We need the logo's scaled height to compute bottom-aligned corners; scale
    # is applied once up front, so height is derived from the source aspect ratio.
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "csv=s=x:p=0", str(logo_path)],
        check=True, capture_output=True, text=True,
    )
    src_w, src_h = (int(v) for v in probe.stdout.strip().split("x"))
    logo_h = int(logo_w * (src_h / src_w))

    # Each overlay stage needs its own copy of the watermark stream — ffmpeg
    # filter labels are single-consumer, so split the scaled logo into one
    # copy per cycle before chaining the overlays.
    split_labels = [f"wm{i}" for i in range(len(cycles))]
    filter_parts = [
        f"[1:v]scale={logo_w}:-1,format=rgba,colorchannelmixer=aa={opacity}"
        f"[wmbase]",
        f"[wmbase]split={len(cycles)}[" + "][".join(split_labels) + "]",
    ]
    last_label = "0:v"
    for index, cycle in enumerate(cycles):
        x, y = _corner_position(cycle["corner"], margin, logo_w, logo_h, frame_w, frame_h)
        out_label = f"v{index}" if index < len(cycles) - 1 else "vout"
        enable_expr = f"between(t,{cycle['start']:.3f},{cycle['end']:.3f})"
        filter_parts.append(
            f"[{last_label}][{split_labels[index]}]overlay=x={x}:y={y}:enable='{enable_expr}'[{out_label}]"
        )
        last_label = out_label

    filter_complex = ";".join(filter_parts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(logo_path),
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "0:a?",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Overlay a periodic, corner-hopping watermark.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--logo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config/channel_profile.json"))
    parser.add_argument("--seed", type=int, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))["watermark"]
    apply_watermark(
        video_path=args.input,
        logo_path=args.logo,
        output_path=args.output,
        width_percent=cfg["width_percent_of_frame"],
        margin_percent=cfg["margin_percent"],
        visible_seconds=cfg["visible_seconds"],
        hidden_seconds=cfg["hidden_seconds"],
        corners=cfg["corners"],
        opacity=cfg["opacity"],
        seed=args.seed,
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
