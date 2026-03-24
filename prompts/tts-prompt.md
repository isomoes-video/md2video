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
- Use `qwen-tts-vd-bailian-voice-20260323160336093-f9d8` as the default voice id.
- Allow overriding at least the script path, voice, and model from the CLI.
- Use the Beijing DashScope HTTP endpoint by default unless a different region is explicitly needed.
- Fail clearly when `DASHSCOPE_API_KEY` is missing or the API response does not contain downloadable audio.
