#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "dashscope>=1.24.6",
# ]
# ///

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen


DEFAULT_MODEL = "qwen3-tts-vd-2026-01-26"
DEFAULT_VOICE = "qwen-tts-vd-bailian-voice-20260323160336093-f9d8"
DEFAULT_SCRIPT = Path("plan/linux-best-os-ai-agent-coding/script.json")
DEFAULT_BASE_HTTP_API_URL = "https://dashscope.aliyuncs.com/api/v1"


def load_script_entries(script_path: Path) -> list[dict[str, Any]]:
    data = json.loads(script_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a list in {script_path}")

    entries: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Entry {index} in {script_path} must be an object")

        slide_number = item.get("slide_number")
        narration = item.get("narration")
        if not isinstance(slide_number, int):
            raise ValueError(
                f"Entry {index} in {script_path} is missing integer slide_number"
            )
        if not isinstance(narration, str) or not narration.strip():
            raise ValueError(
                f"Entry {index} in {script_path} is missing narration text"
            )

        entries.append({"slide_number": slide_number, "narration": narration.strip()})

    return entries


def resolve_output_dir(script_path: Path, output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir
    return script_path.parent / "audio"


def build_output_path(output_dir: Path, slide_number: int) -> Path:
    return output_dir / f"slide-{slide_number:02d}.mp3"


def _get_value(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def extract_audio_url(response: Any) -> str:
    output = _get_value(response, "output")
    audio = _get_value(output, "audio")
    url = _get_value(audio, "url")
    if isinstance(url, str) and url:
        return url
    raise ValueError("DashScope response did not include output.audio.url")


def download_audio_file(url: str, destination: Path) -> None:
    with urlopen(url) as response:
        destination.write_bytes(response.read())


def make_dashscope_synthesizer(
    model: str,
    voice: str,
    api_key: str,
    base_http_api_url: str,
    language_type: str | None,
) -> Callable[[str], str]:
    import dashscope

    dashscope.base_http_api_url = base_http_api_url

    def synthesize(text: str) -> str:
        request_kwargs: dict[str, Any] = {
            "model": model,
            "api_key": api_key,
            "text": text,
            "voice": voice,
            "stream": False,
        }
        if language_type:
            request_kwargs["language_type"] = language_type

        response = dashscope.MultiModalConversation.call(**request_kwargs)
        return extract_audio_url(response)

    return synthesize


def synthesize_script_entries(
    entries: list[dict[str, Any]],
    output_dir: Path,
    synthesize: Callable[[str], str],
    download_audio: Callable[[str, Path], None],
    overwrite: bool,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    written_files: list[Path] = []
    for entry in entries:
        output_path = build_output_path(output_dir, entry["slide_number"])
        if output_path.exists() and not overwrite:
            written_files.append(output_path)
            continue

        audio_url = synthesize(entry["narration"])
        download_audio(audio_url, output_path)
        written_files.append(output_path)

    return written_files


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate one narration MP3 per slide from a plan script.json file.",
    )
    parser.add_argument(
        "--script",
        type=Path,
        default=DEFAULT_SCRIPT,
        help="Path to the plan script.json file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for generated MP3 files. Defaults to an audio/ folder next to script.json.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="DashScope TTS model.",
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help="DashScope voice name or custom voice id.",
    )
    parser.add_argument(
        "--language-type",
        help="Optional DashScope language_type value such as Chinese or English.",
    )
    parser.add_argument(
        "--base-http-api-url",
        default=DEFAULT_BASE_HTTP_API_URL,
        help="DashScope HTTP API base URL.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite any existing slide MP3 files.",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY is required")

    script_path = args.script.resolve()
    entries = load_script_entries(script_path)
    output_dir = resolve_output_dir(script_path, args.output_dir)
    synthesize = make_dashscope_synthesizer(
        model=args.model,
        voice=args.voice,
        api_key=api_key,
        base_http_api_url=args.base_http_api_url,
        language_type=args.language_type,
    )
    written_files = synthesize_script_entries(
        entries=entries,
        output_dir=output_dir,
        synthesize=synthesize,
        download_audio=download_audio_file,
        overwrite=args.overwrite,
    )

    for output_path in written_files:
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
