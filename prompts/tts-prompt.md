# md2video tts prompt

You are generating narration audio from approved script content.

## Goals

- Read `output/<presentation-slug>/script.json`.
- Use DashScope TTS with `DASHSCOPE_API_KEY`.
- Create a uv-runnable Python script that converts each narration entry into audio.
- Generate one mp3 per slide into `output/<presentation-slug>/audio/`.
- Keep file names aligned with slide numbers.

## Input contract

- `script.json` is an array of objects with only `slide_number` and `narration`.
- Treat `slide_number` as the source of truth for file ordering and naming.

## Output contract

- Output directory: `output/<presentation-slug>/audio/`.
- One audio file per slide, for example `slide-01.mp3`, `slide-02.mp3`.
- Preserve the original narration text exactly unless a TTS API requires escaping.

## Implementation requirements

- Prefer a standalone Python script that runs with `uv run`.
- Default the script to reading the target `script.json` and writing next to it under `audio/`.
- Use `cosyvoice-v3-flash` as the default model.
- Use `longanyang` as the default voice.
- Allow overriding at least the script path, voice, and model from the CLI.
- Use the Beijing DashScope WebSocket endpoint by default unless a different region is explicitly needed.
- Use `dashscope.audio.tts_v2.SpeechSynthesizer` and write returned audio bytes directly to mp3 files.
- Create a fresh synthesizer per narration request if the SDK connection lifecycle requires it.
- Fail clearly when `DASHSCOPE_API_KEY` is missing or the TTS API returns no audio.
