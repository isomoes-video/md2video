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
import threading
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


def build_srt_path(output_dir: Path, slide_number: int) -> Path:
    return output_dir / f"slide-{slide_number:02d}.srt"


# ---------------------------------------------------------------------------
# SRT helpers
# ---------------------------------------------------------------------------


def _ms_to_srt_timestamp(ms: int) -> str:
    """Convert milliseconds to SRT timestamp string HH:MM:SS,mmm."""
    hours, remainder = divmod(ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _words_to_srt(sentences: list[dict[str, Any]]) -> str:
    """Build SRT content from a list of sentence dicts collected during synthesis.

    Each sentence dict has the shape::

        {
            "original_text": "床前明月光，",
            "words": [
                {"text": "床", "begin_time": 280, "end_time": 640},
                ...
            ]
        }

    The function groups the words of each sentence into a single subtitle cue.
    If word timestamps are unavailable (empty words list), the sentence text is
    used as a single cue spanning the whole sentence, and begin/end times are
    derived from the first/last available word across adjacent sentences or
    set to 0 as a fallback.
    """
    lines: list[str] = []
    cue_index = 1

    for sentence in sentences:
        text = sentence.get("original_text", "").strip()
        words = sentence.get("words", [])

        if not text:
            continue

        if words:
            begin_ms = words[0]["begin_time"]
            end_ms = words[-1]["end_time"]
        else:
            # No word timestamps — skip; caller should warn
            continue

        lines.append(str(cue_index))
        lines.append(
            f"{_ms_to_srt_timestamp(begin_ms)} --> {_ms_to_srt_timestamp(end_ms)}"
        )
        lines.append(text)
        lines.append("")
        cue_index += 1

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Timestamp-aware ResultCallback
# ---------------------------------------------------------------------------


class _TimestampCollector:
    """Thread-safe collector of sentence/word timestamp data from on_event calls."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Map sentence index → {"original_text": str, "words": [...]}
        self._sentences: dict[int, dict[str, Any]] = {}

    def on_event(self, message: str) -> None:
        try:
            data = json.loads(message)
        except (json.JSONDecodeError, TypeError):
            return

        output = data.get("payload", {}).get("output", {})
        event_type = output.get("type", "")
        sentence = output.get("sentence", {})
        index = sentence.get("index")
        words = sentence.get("words")

        if index is None:
            return

        with self._lock:
            if index not in self._sentences:
                self._sentences[index] = {"original_text": "", "words": []}

            if event_type == "sentence-begin":
                original_text = output.get("original_text", "")
                self._sentences[index]["original_text"] = original_text
                if words:
                    self._sentences[index]["words"] = words

            elif event_type == "sentence-end":
                original_text = output.get("original_text", "")
                if original_text:
                    self._sentences[index]["original_text"] = original_text
                if words:
                    self._sentences[index]["words"] = words

    def get_sentences(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._sentences[i] for i in sorted(self._sentences)]


def make_dashscope_synthesizer(
    model: str,
    voice: str,
    api_key: str,
    base_websocket_api_url: str,
    enable_timestamps: bool = True,
) -> Callable[[str], tuple[bytes, list[dict[str, Any]]]]:
    """Return a synthesize(text) callable that produces (audio_bytes, sentences).

    When *enable_timestamps* is True, ``word_timestamp_enabled`` is passed to
    the API and the returned *sentences* list contains per-sentence word timing
    data suitable for SRT generation.  When False, *sentences* is always ``[]``.
    """
    import dashscope
    from dashscope.audio.tts_v2 import ResultCallback, SpeechSynthesizer

    dashscope.api_key = api_key
    dashscope.base_websocket_api_url = base_websocket_api_url

    def synthesize(text: str) -> tuple[bytes, list[dict[str, Any]]]:
        collector = _TimestampCollector()

        class _Callback(ResultCallback):
            def on_event(self, message: str) -> None:  # type: ignore[override]
                collector.on_event(message)

            def on_data(self, data: bytes) -> None:
                pass  # audio data handled internally by SpeechSynthesizer

            def on_error(self, message: str) -> None:
                pass

            def on_open(self) -> None:
                pass

            def on_complete(self) -> None:
                pass

            def on_close(self) -> None:
                pass

        additional_params: dict[str, Any] = {"enable_ssml": True}
        if enable_timestamps:
            additional_params["word_timestamp_enabled"] = True

        audio_parts: list[bytes] = []
        audio_lock = threading.Lock()

        class _StreamCallback(_Callback):
            def on_data(self, data: bytes) -> None:
                with audio_lock:
                    audio_parts.append(data)

        callback = _StreamCallback()
        synthesizer = SpeechSynthesizer(
            model=model,
            voice=voice,
            callback=callback,
            additional_params=additional_params,
        )
        # Use streaming_call / streaming_complete so we can intercept on_data
        synthesizer.streaming_call(text)
        synthesizer.streaming_complete()

        audio = b"".join(audio_parts)
        if not audio:
            raise RuntimeError(
                f"DashScope TTS returned no audio for model={model!r} voice={voice!r}"
            )
        sentences = collector.get_sentences() if enable_timestamps else []
        return audio, sentences

    return synthesize


def synthesize_script_entries(
    entries: list[dict[str, Any]],
    output_dir: Path,
    synthesize: Callable[[str], tuple[bytes, list[dict[str, Any]]]],
    overwrite: bool,
    write_srt: bool,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    written_files: list[Path] = []
    for entry in entries:
        output_path = build_output_path(output_dir, entry["slide_number"])
        srt_path = build_srt_path(output_dir, entry["slide_number"])

        mp3_exists = output_path.exists()
        srt_exists = srt_path.exists()

        if mp3_exists and (not write_srt or srt_exists) and not overwrite:
            written_files.append(output_path)
            continue

        audio_bytes, sentences = synthesize(entry["narration"])
        output_path.write_bytes(audio_bytes)

        if write_srt:
            srt_content = _words_to_srt(sentences)
            if srt_content.strip():
                srt_path.write_text(srt_content, encoding="utf-8")
                print(f"  srt: {srt_path}")
            else:
                print(
                    f"  warning: no word timestamps received for slide "
                    f"{entry['slide_number']}; skipping SRT"
                )

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
    parser.add_argument(
        "--no-srt",
        action="store_true",
        help="Skip SRT subtitle file generation (enabled by default).",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY is required")

    write_srt = not args.no_srt

    script_path = args.script.resolve()
    entries = load_script_entries(script_path)
    output_dir = resolve_output_dir(script_path, args.output_dir)
    synthesize = make_dashscope_synthesizer(
        model=args.model,
        voice=args.voice,
        api_key=api_key,
        base_websocket_api_url=args.base_websocket_api_url,
        enable_timestamps=write_srt,
    )
    written_files = synthesize_script_entries(
        entries=entries,
        output_dir=output_dir,
        synthesize=synthesize,
        overwrite=args.overwrite,
        write_srt=write_srt,
    )

    for output_path in written_files:
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
