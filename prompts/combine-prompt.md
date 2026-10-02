# md2video render prompt

You are rendering the final animated, narrated video with HyperFrames.

## Input contract

- `output/<presentation-slug>/slides.json`: scenes following `video/README.md`.
- `output/<presentation-slug>/script.json`: one narration entry per scene.
- `output/<presentation-slug>/audio/slide-XX.mp3`: one narration clip per scene.
- Optional matching `slide-XX.srt`: scene-relative subtitle cues.
- Scene and script numbers must be ordered consecutively from 1, with equal counts.
- Extra, duplicate, or missing audio is an error. Never use `--silent` for the final narrated video.

## Render

Use the existing renderer, rather than PDF conversion or screen recording:

```bash
bun run video --workspace output/<presentation-slug>

# Replace a previously reviewed draft or final render
bun run video --workspace output/<presentation-slug> --overwrite

# Without burned-in subtitles
bun run video --workspace output/<presentation-slug> --subtitles none --overwrite
```

## Behavior

- Actual audio lengths are measured with FFprobe and rounded up to full video frames.
- Scene duration covers narration plus a short hold between scenes (`--slide-gap`, default 0.25 seconds).
- Frame-driven animations render reproducibly, with no overlapping narration.
- Available SRT cues are burned into the picture by default. Missing SRT does not block rendering; the current OpenAI TTS backend does not generate SRT.
- The output is a 1920×1080 H.264/AAC MP4 at 30 fps by default (`--fps` is configurable).
- `--concurrency` controls rendering workers (default 2); `--browser-executable` optionally selects an existing Chromium executable.
- `--prepare-only` validates inputs and writes HTML, timeline JSON, and local assets without encoding.

## Output and review

- Final artifact: `output/<presentation-slug>/video.mp4`.
- Intermediate assets and resolved timeline: `output/<presentation-slug>/video-work/`.
- Review the final MP4 for visual overflow, correct narration ordering, animation timing, and subtitles.
- Report the final path. Do not upload or publish unless asked.
- Rendering finishes the video stage, not the entire deliverable. For a complete video workflow, generate `intro.txt` with `prompts/script2intro-prompt.md`, then the required AI cover with `prompts/thumbnail-prompt.md`. An explicitly render-only request can stop at the MP4.
- Do not extract a video frame or use a renderer still as `thumbnail.png`. Preview screenshots belong under `video-work/`; the final cover must come from the AI thumbnail stage.
