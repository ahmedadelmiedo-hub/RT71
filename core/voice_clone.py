"""Generate Arabic narration with the owner's real voice using XTTS v2.

The voice reference must stay outside the public repository. In GitHub Actions it is
restored from the VOICE_REFERENCE_B64 repository secret.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


def clean_arabic_script(text: str) -> str:
    """Remove production labels and normalize spacing before speech synthesis."""
    kept: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            kept.append("")
            continue
        if re.fullmatch(r"(?:مشهد|المشهد)\s+[\w\u0600-\u06ff]+[:：]?", line, flags=re.IGNORECASE):
            continue
        if re.fullmatch(r"(?:ملخص|الخلاصة)[:：]?", line, flags=re.IGNORECASE):
            continue
        if re.fullmatch(r"\[[A-Z_]+(?::[^\]]+)?\]", line):
            continue
        kept.append(line)
    text = "\n".join(kept)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(text: str, max_chars: int = 650) -> list[str]:
    """Split narration at Arabic sentence boundaries for stable XTTS generation."""
    sentences = [part.strip() for part in re.split(r"(?<=[.!؟…])\s+|\n+", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def synthesize(script_file: Path, reference_audio: Path, output_file: Path, language: str = "ar") -> Path:
    if not script_file.is_file():
        raise FileNotFoundError(f"script not found: {script_file}")
    if not reference_audio.is_file():
        raise FileNotFoundError(f"voice reference not found: {reference_audio}")

    from TTS.api import TTS
    from pydub import AudioSegment

    script = clean_arabic_script(script_file.read_text(encoding="utf-8"))
    chunks = split_text(script)
    if not chunks:
        raise ValueError("script contains no speakable text")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    chunk_dir = output_file.parent / f".{output_file.stem}_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    engine = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    combined = AudioSegment.silent(duration=0)
    try:
        for index, chunk in enumerate(chunks, start=1):
            chunk_path = chunk_dir / f"chunk-{index:04d}.wav"
            engine.tts_to_file(
                text=chunk,
                speaker_wav=str(reference_audio),
                language=language,
                file_path=str(chunk_path),
                split_sentences=False,
            )
            combined += AudioSegment.from_wav(chunk_path)
            combined += AudioSegment.silent(duration=180)
        combined.export(output_file, format="wav")
    finally:
        for child in chunk_dir.glob("*"):
            child.unlink(missing_ok=True)
        chunk_dir.rmdir()

    if output_file.stat().st_size == 0:
        raise RuntimeError("XTTS produced an empty audio file")
    return output_file


def convert_to_mp3(wav_file: Path, mp3_file: Path) -> Path:
    mp3_file.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(wav_file),
            "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
            "-ar", "44100", "-b:a", "160k", str(mp3_file),
        ],
        check=True,
    )
    return mp3_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Arabic narration with a private XTTS voice reference.")
    parser.add_argument("--script-file", type=Path, required=True)
    parser.add_argument("--reference-audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", default="ar")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    requested_output = args.output
    wav_output = requested_output if requested_output.suffix.lower() == ".wav" else requested_output.with_suffix(".wav")
    synthesize(args.script_file, args.reference_audio, wav_output, args.language)
    if requested_output.suffix.lower() == ".mp3":
        convert_to_mp3(wav_output, requested_output)
        wav_output.unlink(missing_ok=True)
    print(requested_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
