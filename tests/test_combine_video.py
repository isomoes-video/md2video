import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "combine_video.py"
    spec = importlib.util.spec_from_file_location("combine_video", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResolveWorkspacePathsTests(unittest.TestCase):
    def test_defaults_paths_next_to_output_pdf(self) -> None:
        module = load_module()

        pdf_path = Path("/tmp/presentation/output.pdf")
        paths = module.resolve_workspace_paths(pdf_path)

        self.assertEqual(paths["pdf_path"], pdf_path)
        self.assertEqual(paths["audio_dir"], Path("/tmp/presentation/audio"))
        self.assertEqual(paths["work_dir"], Path("/tmp/presentation/video-work"))
        self.assertEqual(paths["output_path"], Path("/tmp/presentation/video.mp4"))


class BuildSlideAssetsTests(unittest.TestCase):
    def test_pairs_pdf_pages_with_matching_audio_files(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            audio_dir = base / "audio"
            images_dir = base / "images"
            segments_dir = base / "segments"
            audio_dir.mkdir()
            (audio_dir / "slide-01.mp3").write_bytes(b"a")
            (audio_dir / "slide-02.mp3").write_bytes(b"b")

            assets = module.build_slide_assets(
                pdf_page_count=2,
                audio_dir=audio_dir,
                images_dir=images_dir,
                segments_dir=segments_dir,
            )

        self.assertEqual([asset.slide_number for asset in assets], [1, 2])
        self.assertEqual(assets[0].audio_path, audio_dir / "slide-01.mp3")
        self.assertEqual(assets[0].image_path, images_dir / "slide-01.png")
        self.assertEqual(assets[0].segment_path, segments_dir / "slide-01.mp4")
        self.assertEqual(assets[1].audio_path, audio_dir / "slide-02.mp3")

    def test_fails_when_audio_missing_for_pdf_page(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            audio_dir = base / "audio"
            audio_dir.mkdir()
            (audio_dir / "slide-01.mp3").write_bytes(b"a")

            with self.assertRaisesRegex(ValueError, "Missing audio for slide 2"):
                module.build_slide_assets(
                    pdf_page_count=2,
                    audio_dir=audio_dir,
                    images_dir=base / "images",
                    segments_dir=base / "segments",
                )

    def test_fails_when_audio_exists_without_pdf_page(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            audio_dir = base / "audio"
            audio_dir.mkdir()
            (audio_dir / "slide-01.mp3").write_bytes(b"a")
            (audio_dir / "slide-02.mp3").write_bytes(b"b")

            with self.assertRaisesRegex(
                ValueError, "Audio exists for non-existent slide 2"
            ):
                module.build_slide_assets(
                    pdf_page_count=1,
                    audio_dir=audio_dir,
                    images_dir=base / "images",
                    segments_dir=base / "segments",
                )


class ConcatManifestTests(unittest.TestCase):
    def test_writes_ffmpeg_concat_manifest(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            manifest_path = base / "concat.txt"
            segment_paths = [base / "slide-01.mp4", base / "slide-02.mp4"]

            module.write_concat_manifest(segment_paths, manifest_path)

            self.assertEqual(
                manifest_path.read_text(encoding="utf-8"),
                "file 'slide-01.mp4'\nfile 'slide-02.mp4'\n",
            )

    def test_writes_paths_relative_to_manifest_location(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            manifest_path = base / "video-work" / "concat.txt"
            segment_paths = [
                base / "video-work" / "segments" / "slide-01.mp4",
                base / "video-work" / "segments" / "slide-02.mp4",
            ]

            module.write_concat_manifest(segment_paths, manifest_path)

            self.assertEqual(
                manifest_path.read_text(encoding="utf-8"),
                "file 'segments/slide-01.mp4'\nfile 'segments/slide-02.mp4'\n",
            )


if __name__ == "__main__":
    unittest.main()
