import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def load_module():
    module_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "thumbnail_from_prompt.py"
    )
    spec = importlib.util.spec_from_file_location("thumbnail_from_prompt", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PromptResolutionTests(unittest.TestCase):
    def test_loads_prompt_from_file(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            prompt_file = Path(tmp_dir) / "thumbnail-prompt.txt"
            prompt_file.write_text("  一张科技感封面图  \n", encoding="utf-8")

            self.assertEqual(
                module.resolve_prompt_text(None, prompt_file),
                "一张科技感封面图",
            )

    def test_rejects_empty_prompt_file(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            prompt_file = Path(tmp_dir) / "thumbnail-prompt.txt"
            prompt_file.write_text("   \n", encoding="utf-8")

            with self.assertRaises(ValueError):
                module.resolve_prompt_text(None, prompt_file)

    def test_requires_prompt_or_prompt_file(self) -> None:
        module = load_module()

        with self.assertRaises(SystemExit):
            module.resolve_prompt_text(None, None)

    def test_rejects_prompt_and_prompt_file_together(self) -> None:
        module = load_module()

        with self.assertRaises(SystemExit):
            module.resolve_prompt_text("inline", Path("/tmp/prompt.txt"))


class OutputPathTests(unittest.TestCase):
    def test_defaults_thumbnail_next_to_prompt_file(self) -> None:
        module = load_module()

        prompt_file = Path("/tmp/presentation/thumbnail-prompt.txt")

        self.assertEqual(
            module.resolve_output_paths(prompt_file, None, 1),
            [Path("/tmp/presentation/thumbnail.png")],
        )

    def test_explicit_output_wins_over_prompt_file(self) -> None:
        module = load_module()

        self.assertEqual(
            module.resolve_output_paths(
                Path("/tmp/presentation/thumbnail-prompt.txt"),
                Path("/tmp/elsewhere/cover.png"),
                1,
            ),
            [Path("/tmp/elsewhere/cover.png")],
        )

    def test_numbers_files_for_multiple_images(self) -> None:
        module = load_module()

        self.assertEqual(
            module.resolve_output_paths(
                Path("/tmp/presentation/thumbnail-prompt.txt"), None, 3
            ),
            [
                Path("/tmp/presentation/thumbnail-1.png"),
                Path("/tmp/presentation/thumbnail-2.png"),
                Path("/tmp/presentation/thumbnail-3.png"),
            ],
        )

    def test_keeps_custom_extension_when_numbering(self) -> None:
        module = load_module()

        self.assertEqual(
            module.resolve_output_paths(None, Path("/tmp/cover.jpg"), 2),
            [Path("/tmp/cover-1.jpg"), Path("/tmp/cover-2.jpg")],
        )

    def test_appends_png_when_output_has_no_extension(self) -> None:
        module = load_module()

        self.assertEqual(
            module.resolve_output_paths(None, Path("/tmp/cover"), 2),
            [Path("/tmp/cover-1.png"), Path("/tmp/cover-2.png")],
        )

    def test_falls_back_to_cwd_thumbnail_without_prompt_file(self) -> None:
        module = load_module()

        self.assertEqual(
            module.resolve_output_paths(None, None, 1),
            [Path("thumbnail.png")],
        )


class ShouldGenerateTests(unittest.TestCase):
    def test_generates_when_no_files_exist(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = [Path(tmp_dir) / "thumbnail.png"]

            self.assertTrue(module.should_generate(paths, overwrite=False))

    def test_skips_when_all_files_exist(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = [
                Path(tmp_dir) / "thumbnail-1.png",
                Path(tmp_dir) / "thumbnail-2.png",
            ]
            for path in paths:
                path.write_bytes(b"png")

            self.assertFalse(module.should_generate(paths, overwrite=False))

    def test_overwrite_always_generates(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = [
                Path(tmp_dir) / "thumbnail-1.png",
                Path(tmp_dir) / "thumbnail-2.png",
            ]
            paths[0].write_bytes(b"png")

            self.assertTrue(module.should_generate(paths, overwrite=True))

    def test_refuses_partial_set_without_overwrite(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = [
                Path(tmp_dir) / "thumbnail-1.png",
                Path(tmp_dir) / "thumbnail-2.png",
            ]
            paths[0].write_bytes(b"kept candidate")

            with self.assertRaises(SystemExit):
                module.should_generate(paths, overwrite=False)
            self.assertEqual(paths[0].read_bytes(), b"kept candidate")


class ParseArgsTests(unittest.TestCase):
    def test_uses_expected_defaults(self) -> None:
        module = load_module()

        args = module.parse_args(["--prompt", "封面"])

        self.assertEqual(module.DEFAULT_MODEL, "qwen-image-2.0-pro")
        self.assertEqual(module.DEFAULT_SIZE, "2368*1728")
        self.assertEqual(
            module.DEFAULT_BASE_HTTP_API_URL,
            "https://dashscope.aliyuncs.com/api/v1",
        )
        self.assertEqual(args.model, "qwen-image-2.0-pro")
        self.assertEqual(args.size, "2368*1728")
        self.assertEqual(args.n, 1)
        self.assertIsNone(args.seed)
        self.assertFalse(args.no_prompt_extend)
        self.assertFalse(args.watermark)
        self.assertFalse(args.overwrite)


class ApiKeyResolutionTests(unittest.TestCase):
    def test_reads_dashscope_api_key(self) -> None:
        module = load_module()

        with mock.patch.dict(
            os.environ, {"DASHSCOPE_API_KEY": "dash-key"}, clear=False
        ):
            self.assertEqual(module.resolve_api_key(), "dash-key")

    def test_fails_without_dashscope_api_key(self) -> None:
        module = load_module()

        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                module.resolve_api_key()


class ExtractImageUrlsTests(unittest.TestCase):
    def test_extracts_urls_from_response_dict(self) -> None:
        module = load_module()

        response = {
            "output": {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": [
                                {"image": "https://example.com/a.png"},
                                {"image": "https://example.com/b.png"},
                            ],
                        },
                    }
                ]
            }
        }

        self.assertEqual(
            module.extract_image_urls(response),
            ["https://example.com/a.png", "https://example.com/b.png"],
        )

    def test_returns_empty_list_for_missing_output(self) -> None:
        module = load_module()

        self.assertEqual(module.extract_image_urls({}), [])
        self.assertEqual(module.extract_image_urls(None), [])


class SaveImagesTests(unittest.TestCase):
    def test_downloads_each_url_to_its_path(self) -> None:
        module = load_module()

        def fake_download(url: str) -> bytes:
            return f"png:{url}".encode("utf-8")

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_paths = [
                Path(tmp_dir) / "thumbnail-1.png",
                Path(tmp_dir) / "thumbnail-2.png",
            ]

            written = module.save_images(
                ["https://example.com/a.png", "https://example.com/b.png"],
                output_paths,
                download=fake_download,
            )

            self.assertEqual(written, output_paths)
            self.assertEqual(
                output_paths[0].read_bytes(), b"png:https://example.com/a.png"
            )
            self.assertEqual(
                output_paths[1].read_bytes(), b"png:https://example.com/b.png"
            )

    def test_creates_missing_parent_directories(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "nested" / "thumbnail.png"

            written = module.save_images(
                ["https://example.com/a.png"],
                [output_path],
                download=lambda url: b"png",
            )

            self.assertEqual(written, [output_path])
            self.assertEqual(output_path.read_bytes(), b"png")

    def test_fails_when_no_urls_returned(self) -> None:
        module = load_module()

        with self.assertRaises(RuntimeError):
            module.save_images([], [Path("/tmp/thumbnail.png")], download=lambda u: b"")

    def test_saves_available_images_when_fewer_urls_than_paths(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_paths = [
                Path(tmp_dir) / "thumbnail-1.png",
                Path(tmp_dir) / "thumbnail-2.png",
                Path(tmp_dir) / "thumbnail-3.png",
            ]

            written = module.save_images(
                ["https://example.com/a.png"],
                output_paths,
                download=lambda url: b"png",
            )

            self.assertEqual(written, [output_paths[0]])
            self.assertTrue(output_paths[0].exists())
            self.assertFalse(output_paths[1].exists())
            self.assertFalse(output_paths[2].exists())

    def test_ignores_extra_urls_beyond_requested_paths(self) -> None:
        module = load_module()

        downloaded: list[str] = []

        def fake_download(url: str) -> bytes:
            downloaded.append(url)
            return b"png"

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "thumbnail.png"

            written = module.save_images(
                ["https://example.com/a.png", "https://example.com/b.png"],
                [output_path],
                download=fake_download,
            )

            self.assertEqual(written, [output_path])
            self.assertEqual(downloaded, ["https://example.com/a.png"])


if __name__ == "__main__":
    unittest.main()
