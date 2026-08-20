import importlib.util
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image

from core.voice_clone import split_text


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
            self.assertFalse(result["youtube_publishing_enabled"])

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


if __name__ == "__main__":
    unittest.main()
