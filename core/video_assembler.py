"""Assembles a full episode: intro card -> scenes (with narration) -> outro,
then applies the periodic corner-hopping watermark over the whole thing.

This orchestrates core.intro_builder and core.watermark; scene footage /
narration mixing is expected to already exist as a single "raw_episode.mp4"
produced upstream by the existing MoneyPrinterTurbo-based pipeline. This
module focuses specifically on the branding layer requested: intro, outro,
and the moving watermark.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from core.intro_builder import build_intro_clip
from core.watermark import apply_watermark


def concat_clips(clip_paths: list[Path], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = output_path.parent / f".{output_path.stem}_concat.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in clip_paths), encoding="utf-8"
    )
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    list_file.unlink(missing_ok=True)
    return output_path


def assemble_episode(
    raw_episode: Path,
    config_path: Path,
    output_path: Path,
    watermark_seed: int | None = None,
) -> Path:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    logo_path = Path(cfg["branding"]["logo_path"])
    jingle_path = Path(cfg["branding"]["jingle_path"])

    work_dir = output_path.parent / f".{output_path.stem}_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    intro_clip = work_dir / "intro.mp4"
    build_intro_clip(
        logo_path=logo_path,
        jingle_path=jingle_path,
        output_path=intro_clip,
        duration=cfg["branding"]["jingle_intro_duration_sec"],
        jingle_start=cfg["branding"]["jingle_intro_start_sec"],
    )

    concatenated = work_dir / "concatenated.mp4"
    concat_clips([intro_clip, raw_episode], concatenated)

    apply_watermark(
        video_path=concatenated,
        logo_path=logo_path,
        output_path=output_path,
        width_percent=cfg["watermark"]["width_percent_of_frame"],
        margin_percent=cfg["watermark"]["margin_percent"],
        visible_seconds=cfg["watermark"]["visible_seconds"],
        hidden_seconds=cfg["watermark"]["hidden_seconds"],
        corners=cfg["watermark"]["corners"],
        opacity=cfg["watermark"]["opacity"],
        seed=watermark_seed,
    )

    for temp_file in work_dir.glob("*"):
        temp_file.unlink(missing_ok=True)
    work_dir.rmdir()

    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assemble intro + raw episode + watermark.")
    parser.add_argument("--raw-episode", type=Path, required=True, help="Output of the existing MoneyPrinterTurbo pipeline")
    parser.add_argument("--config", type=Path, default=Path("config/channel_profile.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    assemble_episode(args.raw_episode, args.config, args.output, watermark_seed=args.seed)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
