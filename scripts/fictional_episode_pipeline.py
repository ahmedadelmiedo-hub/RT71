"""Build a self-contained, clearly fictional five-minute episode for الملف 71.

The job deliberately makes no network calls and performs no YouTube upload.  It
creates a screenplay, abstract original scene artwork, cloned narration from a
private repository secret, and a local MP4 artifact for manual review.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from textwrap import fill

from PIL import Image, ImageDraw, ImageFilter, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]

CASE_SEEDS = [
    {
        "case": "المصعد الذي توقف في الطابق صفر",
        "place": "مبنى أرشيف قديم على أطراف المدينة",
        "evidence": "مفتاح نحاسي عليه تاريخ ممسوح",
        "witness": "حارس ليلي لا يتذكر سوى صوت جرس بعيد",
        "twist": "المفتاح لا يفتح بابًا، بل يعيد ترتيب ملفات الدليل",
    },
    {
        "case": "الغرفة التي ظهرت في خريطة غير موجودة",
        "place": "مستشفى مهجور أُغلق منذ سنوات",
        "evidence": "خريطة حرارية تحمل علامة 71",
        "witness": "فني صيانة يحتفظ برسالة بلا مرسل",
        "twist": "الغرفة كانت سجلًا لرسائل اعتراف لم تصل أبدًا",
    },
    {
        "case": "الساعة التي عادت إلى الثالثة صباحًا",
        "place": "محطة قطار متروكة قرب مصنع قديم",
        "evidence": "ساعة جيب متوقفة عند نفس الدقيقة",
        "witness": "بائعة كتب عثرت على دفتر أسماء مشفّر",
        "twist": "التوقيت يطابق لحظة إخفاء الدليل لا وقوع الجريمة",
    },
    {
        "case": "الصورة التي التقطت صاحبها مرتين",
        "place": "عمارة سكنية خالية من السكان",
        "evidence": "صورة فورية يظهر فيها الممر من زاويتين",
        "witness": "مصوّر صحفي اعتزل العمل بعد تلك الليلة",
        "twist": "الصورة جزء من تجربة لتحديد من يبدّل شهادته",
    },
    {
        "case": "خطاب بلا توقيع داخل ملف 71",
        "place": "مكتب بريد صغير في حي صناعي",
        "evidence": "خطاب مشفّر بحبر لا يظهر إلا تحت الضوء الأزرق",
        "witness": "موظفة فرز تتذكر صندوقًا لم يُفتح",
        "twist": "كاتب الخطاب هو الشاهد الذي أخفى هويته لحماية شخص آخر",
    },
    {
        "case": "الباب الذي لا يفتح إلا عند انقطاع الكهرباء",
        "place": "قبو مسرح مهجور في وسط المدينة",
        "evidence": "مفتاح إنارة يحمل رقماً متسلسلاً ناقصًا",
        "witness": "عازف قديم سمع لحنًا داخل القبو",
        "twist": "الضوء يخفي رموزًا كانت تقود إلى الدليل الحقيقي",
    },
]


def load_profile(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def select_seed(run_at: datetime) -> dict:
    return CASE_SEEDS[(run_at.year * 53 + run_at.timetuple().tm_yday * 7 + run_at.hour) % len(CASE_SEEDS)]


def build_script(profile: dict, seed: dict, run_at: datetime) -> tuple[str, list[dict]]:
    policy = profile["content_policy"]
    channel = profile["channel_name"]
    title = f"{channel} | {seed['case']}"
    intro = policy["opening_disclaimer"]
    scene_specs = [
        ("الإنذار", f"في {seed['place']} بدأ كل شيء بتفصيلة عادية ظاهريًا، لكنها تحولت خلال دقائق إلى أول إنذار حقيقي. لم يكن هناك صراخ ولا مطاردة؛ فقط أثر صغير في غير موضعه جعل المحقق يفتح ملفًا كان قد أُغلق من دون إجابة."),
        ("الأثر", f"الأثر كان {seed['evidence']}. بدا بلا قيمة لمن مرّ بجانبه، لكن ترتيب العلامات حوله كشف أن شخصًا ما أراد أن يجدَه شخص محدد في وقت محدد. هنا أصبحت القصة سؤالًا: لماذا يُترك دليل ظاهر إذا كان صاحبه يريد إخفاء الحقيقة؟"),
        ("الشاهد", f"الخيط التالي قاد إلى {seed['witness']}. لم يقدم الشاهد جوابًا جاهزًا، بل وصف تفصيلًا ناقصًا: ضوء يتحرك، وخطوات تتوقف فجأة، وعبارة لا يعرف من قالها. كل كلمة بدت منفصلة، لكن جمعها أعاد رسم طريق الحكاية."),
        ("الأرشيف", f"عند مراجعة الأرشيف ظهر الرقم 71 من جديد. لم يكن اسمًا لشخص ولا رقم قضية حقيقية، بل علامة داخل العالم الخيالي للقصة تشير إلى ملف مراجعة. المقارنة بين السجل القديم والأثر الجديد أثبتت أن ما بدا صدفة كان خطة طويلة ومقصودة."),
        ("التبدل", f"مع اقتراب الحل تغير معنى الأدلة. {seed['twist']}. هذا التبدل أجبر المحقق على سؤال أصعب: هل كان الهدف كشف فاعل واحد، أم اختبار من يصدق الرواية الأسرع؟ لذلك عاد إلى المكان مرة أخيرة، من دون افتراضات ومن دون اتهام لأي شخص."),
        ("الملف المفتوح", f"النهاية لم تقدم حكمًا نهائيًا. بدلًا من ذلك، حُفظت الملاحظات في ملف جديد بعنوان {seed['case']}، مع تنبيه واضح بأن القصة خيالية بالكامل. ويبقى السؤال داخل عالم الحكاية: لو وصلت إليك آخر ورقة من الملف، هل ستفتحها أم ستترك الرقم 71 مغلقًا؟"),
    ]
    blocks = [intro, f"عنوان الحلقة: {title}."]
    scenes: list[dict] = []
    for index, (label, paragraph) in enumerate(scene_specs, start=1):
        expansion = (
            "الراوي لا يقرر الحقيقة بدل المستمع. يصف ما ظهر في السجل، ثم يترك مساحة للتفكير في علاقة الدليل بالزمن وبمن اختار أن يراه. "
            "بهذا يظل الإيقاع هادئًا، بينما تتقدم التفاصيل تدريجيًا من غير ادعاء أن ما نسمعه حدث واقعي."
        )
        narration = f"المشهد {index}: {label}. {paragraph} {expansion}"
        blocks.append(narration)
        scenes.append({"index": index, "label": label, "narration": narration})
    blocks.append("هذه القصة عمل خيالي أصلي لأغراض السرد والترفيه، ولا تمثل قضية حقيقية أو اتهامًا لأي شخص.")
    script = "\n\n".join(blocks)
    return script, scenes


def word_count(text: str) -> int:
    return len([word for word in text.replace("\n", " ").split(" ") if word.strip()])


def create_scene_art(scene: dict, profile: dict, output_path: Path) -> None:
    accent = tuple(profile["visual_identity"]["accent_rgb"])
    background = tuple(profile["visual_identity"]["background_rgb"])
    width, height = (1280, 720)
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image, "RGBA")
    label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
    random.seed(scene["index"])
    for _ in range(52):
        x = random.randrange(-150, width)
        y = random.randrange(-100, height)
        radius = random.randrange(18, 180)
        color = (*accent, random.randrange(12, 44))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    draw.rectangle((74, 76, width - 74, height - 76), outline=(*accent, 205), width=4)
    draw.line((122, height // 2, width - 122, height // 2), fill=(*accent, 120), width=2)
    draw.ellipse((width // 2 - 92, height // 2 - 92, width // 2 + 92, height // 2 + 92), outline=(*accent, 225), width=4)
    draw.text((106, 108), f"CASE 71  /  SCENE {scene['index']:02d}", fill=(230, 230, 230, 230), font=label_font)
    draw.text((106, height - 142), scene["label"].upper(), fill=(*accent, 250), font=title_font)
    image.filter(ImageFilter.GaussianBlur(radius=0.35)).save(output_path, "PNG")


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def create_visual_track(scene_images: list[Path], target_seconds: int, fps: int, output: Path) -> None:
    duration = target_seconds / len(scene_images)
    parts: list[Path] = []
    for index, image_path in enumerate(scene_images, start=1):
        part = output.parent / f"visual-{index:02d}.mp4"
        run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(image_path), "-t", f"{duration:.2f}",
            "-vf", f"scale=1280:720,zoompan=z='min(zoom+0.00012,1.08)':d={int(duration * fps)}:s=1280x720:fps={fps}",
            "-r", str(fps), "-pix_fmt", "yuv420p", "-an", str(part),
        ])
        parts.append(part)
    concat_file = output.parent / "visual-concat.txt"
    concat_file.write_text("\n".join(f"file '{part.resolve()}'" for part in parts), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output)])


def synthesize_narration(script_path: Path, reference_audio: Path, output: Path, voice: dict) -> None:
    """Generate narration from the owner-supplied reference with Habibi-TTS.

    The profile carries the matching reference transcript and Egyptian dialect
    ID.  No public default narrator or external API is used.
    """
    run([
        "habibi-tts_infer-cli",
        "--model", "Specialized",
        "--dialect", str(voice["dialect"]),
        "--ref_audio", str(reference_audio),
        "--ref_text", str(voice["reference_transcript"]),
        "--gen_file", str(script_path),
        "--output_dir", str(output.parent),
        "--output_file", output.name,
        "--device", "cpu",
        "--remove_silence",
    ])


def mux_video(visual_track: Path, narration: Path, target_seconds: int, output: Path) -> None:
    run([
        "ffmpeg", "-y", "-i", str(visual_track), "-i", str(narration),
        "-filter_complex", f"[1:a]apad=pad_dur={target_seconds}[audio]",
        "-map", "0:v:0", "-map", "[audio]", "-t", str(target_seconds),
        "-c:v", "libx264", "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output),
    ])


def build_episode(project_root: Path, profile_path: Path, output_dir: Path, run_at: datetime, dry_run: bool) -> dict:
    profile = load_profile(profile_path)
    seed = select_seed(run_at)
    script, scenes = build_script(profile, seed, run_at)
    episode_id = run_at.strftime("episode-%Y%m%d-%H%M")
    episode_dir = output_dir / episode_id
    episode_dir.mkdir(parents=True, exist_ok=True)
    script_path = episode_dir / "script.txt"
    script_path.write_text(script, encoding="utf-8")
    metadata = {
        "episode_id": episode_id,
        "title": f"{profile['channel_name']} | {seed['case']}",
        "channel_handle": profile["youtube"]["handle"],
        "fiction_only": True,
        "youtube_publishing_enabled": False,
        "target_duration_seconds": profile["episode"]["target_duration_seconds"],
        "script_word_count": word_count(script),
        "scenes": scenes,
    }
    (episode_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    if dry_run:
        return metadata
    scene_dir = episode_dir / "scenes"
    scene_dir.mkdir(exist_ok=True)
    scene_images: list[Path] = []
    for scene in scenes:
        image_path = scene_dir / f"scene-{scene['index']:02d}.png"
        create_scene_art(scene, profile, image_path)
        scene_images.append(image_path)
    visual_track = episode_dir / "visual-track.mp4"
    create_visual_track(scene_images, profile["episode"]["target_duration_seconds"], profile["episode"]["fps"], visual_track)
    reference = project_root / ".private" / "voice" / profile["voice"]["reference_audio_filename"]
    narration = episode_dir / "narration.wav"
    synthesize_narration(script_path, reference, narration, profile["voice"])
    mux_video(visual_track, narration, profile["episode"]["target_duration_seconds"], episode_dir / "final.mp4")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one fictional الملف 71 episode without publishing it.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--profile", type=Path, default=REPO_ROOT / "config" / "channel_profile.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--at", default=None, help="UTC ISO timestamp for reproducible tests")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_at = datetime.fromisoformat(args.at.replace("Z", "+00:00")) if args.at else datetime.now(timezone.utc)
    metadata = build_episode(args.project_root, args.profile, args.output_dir, run_at, args.dry_run)
    print(json.dumps(metadata, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
