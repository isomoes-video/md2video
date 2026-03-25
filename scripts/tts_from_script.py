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


DEFAULT_MODEL = "cosyvoice-v3-flash"
DEFAULT_VOICE = "longanyang"
DEFAULT_SCRIPT = Path("output/tools-keyboard-first-workflow/script.json")
DEFAULT_BASE_WEBSOCKET_API_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"


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
        if not isinstance(narration, str) or not narration:
            raise ValueError(
                f"Entry {index} in {script_path} is missing narration text"
            )

        entries.append({"slide_number": slide_number, "narration": narration})

    return sorted(entries, key=lambda entry: entry["slide_number"])


def resolve_output_dir(script_path: Path, output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir
    return script_path.parent / "audio"


def build_output_path(output_dir: Path, slide_number: int) -> Path:
    return output_dir / f"slide-{slide_number:02d}.mp3"


def make_dashscope_synthesizer(
    model: str,
    voice: str,
    api_key: str,
    base_websocket_api_url: str,
) -> Callable[[str], bytes]:
    import dashscope
    from dashscope.audio.tts_v2 import SpeechSynthesizer

    dashscope.api_key = api_key
    dashscope.base_websocket_api_url = base_websocket_api_url

    def synthesize(text: str) -> bytes:
        synthesizer = SpeechSynthesizer(model=model, voice=voice)
        audio = synthesizer.call(text)
        if not isinstance(audio, bytes) or not audio:
            raise RuntimeError(
                f"DashScope TTS returned no audio for model={model!r} voice={voice!r}"
            )
        return audio

    return synthesize


def synthesize_script_entries(
    entries: list[dict[str, Any]],
    output_dir: Path,
    synthesize: Callable[[str], bytes],
    overwrite: bool,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    written_files: list[Path] = []
    for entry in entries:
        output_path = build_output_path(output_dir, entry["slide_number"])
        if output_path.exists() and not overwrite:
            written_files.append(output_path)
            continue

        audio_bytes = synthesize(entry["narration"])
        output_path.write_bytes(audio_bytes)
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
        "--base-websocket-api-url",
        default=DEFAULT_BASE_WEBSOCKET_API_URL,
        help="DashScope WebSocket API base URL.",
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
        base_websocket_api_url=args.base_websocket_api_url,
    )
    written_files = synthesize_script_entries(
        entries=entries,
        output_dir=output_dir,
        synthesize=synthesize,
        overwrite=args.overwrite,
    )

    for output_path in written_files:
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
