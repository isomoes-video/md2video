import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "tts_from_script.py"
    spec = importlib.util.spec_from_file_location("tts_from_script", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LoadScriptEntriesTests(unittest.TestCase):
    def test_loads_entries_from_script_json(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            script_path = Path(tmp_dir) / "script.json"
            script_path.write_text(
                json.dumps(
                    [
                        {"slide_number": 1, "narration": "hello"},
                        {"slide_number": 2, "narration": "world"},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            entries = module.load_script_entries(script_path)

        self.assertEqual(
            entries,
            [
                {"slide_number": 1, "narration": "hello"},
                {"slide_number": 2, "narration": "world"},
            ],
        )


class OutputPathTests(unittest.TestCase):
    def test_defaults_audio_directory_next_to_script(self) -> None:
        module = load_module()

        script_path = Path("/tmp/presentation/script.json")

        self.assertEqual(
            module.resolve_output_dir(script_path, None),
            Path("/tmp/presentation/audio"),
        )

    def test_builds_zero_padded_mp3_name(self) -> None:
        module = load_module()

        output_path = module.build_output_path(Path("/tmp/audio"), 7)

        self.assertEqual(output_path, Path("/tmp/audio/slide-07.mp3"))


class ParseArgsTests(unittest.TestCase):
    def test_uses_expected_default_voice(self) -> None:
        module = load_module()

        args = module.parse_args(["--voice", "override-voice"])

        self.assertEqual(
            module.DEFAULT_VOICE,
            "qwen-tts-vd-bailian-voice-20260323160336093-f9d8",
        )
        self.assertEqual(args.voice, "override-voice")


class SynthesizeEntriesTests(unittest.TestCase):
    def test_writes_one_audio_file_per_slide(self) -> None:
        module = load_module()
        seen_text = []

        def fake_synthesizer(text: str) -> str:
            seen_text.append(text)
            return f"https://example.com/{len(seen_text)}.mp3"

        downloads = []

        def fake_downloader(url: str, destination: Path) -> None:
            downloads.append((url, destination))
            destination.write_bytes(f"downloaded:{url}".encode("utf-8"))

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "audio"
            manifest = module.synthesize_script_entries(
                entries=[
                    {"slide_number": 1, "narration": "first"},
                    {"slide_number": 11, "narration": "second"},
                ],
                output_dir=output_dir,
                synthesize=fake_synthesizer,
                download_audio=fake_downloader,
                overwrite=False,
            )

            self.assertEqual(seen_text, ["first", "second"])
            self.assertEqual(
                downloads,
                [
                    ("https://example.com/1.mp3", output_dir / "slide-01.mp3"),
                    ("https://example.com/2.mp3", output_dir / "slide-11.mp3"),
                ],
            )
            self.assertEqual(
                manifest,
                [
                    output_dir / "slide-01.mp3",
                    output_dir / "slide-11.mp3",
                ],
            )

    def test_skips_existing_files_without_overwrite(self) -> None:
        module = load_module()

        def fail_synthesizer(text: str) -> str:
            raise AssertionError(f"should not synthesize: {text}")

        def fail_downloader(url: str, destination: Path) -> None:
            raise AssertionError(f"should not download: {url} -> {destination}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "audio"
            output_dir.mkdir(parents=True)
            existing = output_dir / "slide-03.mp3"
            existing.write_bytes(b"existing")

            manifest = module.synthesize_script_entries(
                entries=[{"slide_number": 3, "narration": "keep me"}],
                output_dir=output_dir,
                synthesize=fail_synthesizer,
                download_audio=fail_downloader,
                overwrite=False,
            )

            self.assertEqual(manifest, [existing])
            self.assertEqual(existing.read_bytes(), b"existing")


if __name__ == "__main__":
    unittest.main()
