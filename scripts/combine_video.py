#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "pillow>=11.1.0",
#   "pypdfium2>=4.30.0",
# ]
# ///

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from typing import NamedTuple, Sequence


DEFAULT_PDF = Path("plan/linux-best-os-ai-agent-coding/output.pdf")
AUDIO_FILE_PATTERN = re.compile(r"^slide-(\d+)\.mp3$")
DEFAULT_SLIDE_GAP_SECONDS = 0.25
DEFAULT_FPS = 30
DEFAULT_AUDIO_BITRATE = "96k"


class SlideAsset(NamedTuple):
    slide_number: int
    audio_path: Path
    image_path: Path
    segment_path: Path


def resolve_workspace_paths(
    pdf_path: Path,
    audio_dir: Path | None = None,
    work_dir: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Path]:
    pdf_path = pdf_path.resolve()
    base_dir = pdf_path.parent
    resolved_work_dir = (
        work_dir.resolve() if work_dir is not None else base_dir / "video-work"
    )
    return {
        "pdf_path": pdf_path,
        "audio_dir": audio_dir.resolve()
        if audio_dir is not None
        else base_dir / "audio",
        "work_dir": resolved_work_dir,
        "output_path": output_path.resolve()
        if output_path is not None
        else base_dir / "video.mp4",
    }


def collect_audio_files(audio_dir: Path) -> dict[int, Path]:
    audio_files: dict[int, Path] = {}
    for audio_path in sorted(audio_dir.glob("slide-*.mp3")):
        match = AUDIO_FILE_PATTERN.match(audio_path.name)
        if match is None:
            continue
        slide_number = int(match.group(1))
        audio_files[slide_number] = audio_path
    return audio_files


def build_slide_assets(
    pdf_page_count: int,
    audio_dir: Path,
    images_dir: Path,
    segments_dir: Path,
) -> list[SlideAsset]:
    audio_files = collect_audio_files(audio_dir)
    assets: list[SlideAsset] = []

    for slide_number in range(1, pdf_page_count + 1):
        audio_path = audio_files.get(slide_number)
        if audio_path is None:
            raise ValueError(f"Missing audio for slide {slide_number}")
        assets.append(
            SlideAsset(
                slide_number=slide_number,
                audio_path=audio_path,
                image_path=images_dir / f"slide-{slide_number:02d}.png",
                segment_path=segments_dir / f"slide-{slide_number:02d}.mp4",
            )
        )

    extra_audio = sorted(number for number in audio_files if number > pdf_page_count)
    if extra_audio:
        raise ValueError(f"Audio exists for non-existent slide {extra_audio[0]}")

    return assets


def write_concat_manifest(segment_paths: Sequence[Path], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for path in segment_paths:
        relative_path = (
            path.resolve().relative_to(manifest_path.parent.resolve())
            if path.resolve().is_relative_to(manifest_path.parent.resolve())
            else path.resolve()
        )
        escaped_name = relative_path.as_posix().replace("'", r"'\\''")
        lines.append(f"file '{escaped_name}'")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_pdf_page_count(pdf_path: Path) -> int:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(pdf_path))
    try:
        return len(document)
    finally:
        document.close()


def render_pdf_pages(
    pdf_path: Path, slide_assets: Sequence[SlideAsset], scale: float = 2.0
) -> None:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(pdf_path))
    try:
        for asset in slide_assets:
            asset.image_path.parent.mkdir(parents=True, exist_ok=True)
            page = document[asset.slide_number - 1]
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil()
            try:
                image.save(asset.image_path)
            finally:
                image.close()
    finally:
        document.close()


def run_command(command: Sequence[str]) -> None:
    subprocess.run(command, check=True)


def probe_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def render_slide_segment(
    asset: SlideAsset,
    duration: float,
    trailing_gap: float,
    overwrite: bool,
    fps: int,
    audio_bitrate: str,
) -> None:
    total_duration = duration + trailing_gap
    audio_filter = f"apad=whole_dur={total_duration:.6f}"
    command = [
        "ffmpeg",
        "-y" if overwrite else "-n",
        "-loop",
        "1",
        "-framerate",
        str(fps),
        "-t",
        f"{total_duration:.6f}",
        "-i",
        str(asset.image_path),
        "-i",
        str(asset.audio_path),
        "-vf",
        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-af",
        audio_filter,
        "-r",
        str(fps),
        "-t",
        f"{total_duration:.6f}",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-tune",
        "stillimage",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        str(asset.segment_path),
    ]
    run_command(command)


def combine_segments(manifest_path: Path, output_path: Path, overwrite: bool) -> None:
    command = [
        "ffmpeg",
        "-y" if overwrite else "-n",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(manifest_path),
        "-fflags",
        "+genpts",
        "-avoid_negative_ts",
        "make_zero",
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    run_command(command)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a narrated video from output.pdf and per-slide MP3 files.",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=DEFAULT_PDF,
        help="Path to the presentation PDF with one slide per page.",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        help="Directory containing slide-XX.mp3 files. Defaults next to the PDF.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Directory for intermediate render assets. Defaults to video-work/ next to the PDF.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Final MP4 output path. Defaults to video.mp4 next to the PDF.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite intermediate and final video files if they already exist.",
    )
    parser.add_argument(
        "--slide-gap",
        type=float,
        default=DEFAULT_SLIDE_GAP_SECONDS,
        help=(
            "Silent hold in seconds to append between slides. "
            f"Defaults to {DEFAULT_SLIDE_GAP_SECONDS:.2f}."
        ),
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=DEFAULT_FPS,
        help=f"Constant output frame rate for slide video segments. Defaults to {DEFAULT_FPS}.",
    )
    parser.add_argument(
        "--audio-bitrate",
        default=DEFAULT_AUDIO_BITRATE,
        help=(
            "AAC bitrate for rendered slide segments. "
            f"Defaults to {DEFAULT_AUDIO_BITRATE}."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths = resolve_workspace_paths(
        pdf_path=args.pdf,
        audio_dir=args.audio_dir,
        work_dir=args.work_dir,
        output_path=args.output,
    )
    pdf_path = paths["pdf_path"]
    audio_dir = paths["audio_dir"]
    work_dir = paths["work_dir"]
    output_path = paths["output_path"]

    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")
    if not audio_dir.exists():
        raise SystemExit(f"Audio directory not found: {audio_dir}")
    if args.slide_gap < 0:
        raise SystemExit("--slide-gap must be non-negative")
    if args.fps <= 0:
        raise SystemExit("--fps must be positive")

    images_dir = work_dir / "slides"
    segments_dir = work_dir / "segments"
    manifest_path = work_dir / "concat.txt"
    images_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)

    pdf_page_count = get_pdf_page_count(pdf_path)
    slide_assets = build_slide_assets(
        pdf_page_count, audio_dir, images_dir, segments_dir
    )

    render_pdf_pages(pdf_path, slide_assets)

    segment_paths: list[Path] = []
    for index, asset in enumerate(slide_assets):
        duration = probe_audio_duration(asset.audio_path)
        trailing_gap = args.slide_gap if index < len(slide_assets) - 1 else 0.0
        print(
            "slide "
            f"{asset.slide_number:02d}: {asset.image_path} + {asset.audio_path} "
            f"(audio={duration:.3f}s, gap={trailing_gap:.3f}s)"
        )
        render_slide_segment(
            asset,
            duration,
            trailing_gap,
            overwrite=args.overwrite,
            fps=args.fps,
            audio_bitrate=args.audio_bitrate,
        )
        segment_paths.append(asset.segment_path)

    write_concat_manifest(segment_paths, manifest_path)
    combine_segments(manifest_path, output_path, overwrite=args.overwrite)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
