import importlib.util
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image

from core.voice_clone import split_text
from core.shorts_builder import build_short


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "fictional_episode_pipeline.py"
SPEC = importlib.util.spec_from_file_location("fictional_episode_pipeline", MODULE_PATH)
assert SPEC and SPEC.loader
PIPELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE)


class FictionalEpisodePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = json.loads((REPO_ROOT / "config" / "channel_profile.json").read_text(encoding="utf-8"))
        self.run_at = datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc)

    def test_script_is_clearly_fictional_and_has_six_scenes(self) -> None:
        script, scenes = PIPELINE.build_script(self.profile, PIPELINE.select_seed(self.run_at), self.run_at)
        self.assertIn("عمل خيالي أصلي", script)
        self.assertEqual(len(scenes), 6)
        self.assertGreaterEqual(PIPELINE.word_count(script), self.profile["episode"]["target_word_count"])

    def test_voice_profile_requires_private_owner_reference(self) -> None:
        voice = self.profile["voice"]
        self.assertEqual(voice["engine"], "xtts_v2_noncommercial")
        self.assertEqual(voice["reference_audio_secret"], "VOICE_REFERENCE_B64")
        self.assertEqual(voice["usage_scope"], "private_noncommercial_review")

    def test_dry_run_writes_only_reviewable_text_artifacts(self) -> None:
        with TemporaryDirectory() as temporary:
            result = PIPELINE.build_episode(
                REPO_ROOT,
                REPO_ROOT / "config" / "channel_profile.json",
                Path(temporary),
                self.run_at,
                dry_run=True,
            )
            episode_dir = Path(temporary) / result["episode_id"]
            self.assertTrue((episode_dir / "script.txt").is_file())
            self.assertTrue((episode_dir / "metadata.json").is_file())
            self.assertFalse((episode_dir / "final.mp4").exists())
            self.assertTrue(result["youtube_publishing_enabled"])
            self.assertTrue((episode_dir / "publish-package.json").is_file())

    def test_scene_art_is_a_valid_16_by_9_png(self) -> None:
        _, scenes = PIPELINE.build_script(self.profile, PIPELINE.select_seed(self.run_at), self.run_at)
        with TemporaryDirectory() as temporary:
            artwork = Path(temporary) / "scene.png"
            PIPELINE.create_scene_art(scenes[0], self.profile, artwork)
            with Image.open(artwork) as image:
                self.assertEqual(image.size, (1280, 720))

    def test_xtts_narration_chunks_are_hard_capped_for_arabic(self) -> None:
        script, _ = PIPELINE.build_script(self.profile, PIPELINE.select_seed(self.run_at), self.run_at)
        chunks = split_text(script)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 150 for chunk in chunks))
        self.assertEqual(" ".join(chunks), " ".join(script.split()))

    def test_publish_package_has_public_metadata_and_linked_short_template(self) -> None:
        seed = PIPELINE.select_seed(self.run_at)
        hook = PIPELINE.build_short_hook(seed)
        package = PIPELINE.build_publish_package(self.profile, seed, "episode-test", hook)
        self.assertLessEqual(len(package["long_video"]["title"]), 100)
        self.assertEqual(package["long_video"]["privacy_status"], "public")
        self.assertIn("{long_video_url}", package["short"]["description_template"])
        self.assertIn("قصة خيالية", package["short"]["hook"])

    def test_short_builder_ends_when_hook_audio_ends(self) -> None:
        with patch("core.shorts_builder.subprocess.run") as mocked_run:
            build_short(Path("scene.mp4"), Path("hook.wav"), Path("short.mp4"))
        command = mocked_run.call_args.args[0]
        self.assertIn("-shortest", command)


if __name__ == "__main__":
    unittest.main()
