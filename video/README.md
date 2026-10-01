# Animated video renderer

Remotion renders the reusable React scenes in `Composition.tsx` directly to MP4. PDF is not an input. Scene durations come from actual MP3 lengths, rounded up to frames; the default 0.25-second hold is added only between scenes. Narration never overlaps. Visuals fade out and the next scene enters against a shared background.

## Install and run

Requires Bun (for dependency installation), Node.js, and FFmpeg/FFprobe on PATH. Remotion downloads Chrome Headless Shell on first render; Linux also needs Chromium's system libraries and a Chinese font such as Noto Sans CJK. Internet access is needed for that initial download. To use installed Chromium, pass `--browser-executable /path/to/chrome`.

```bash
bun install

# No API credentials needed: render the included silent animation demo
bun run video --workspace examples/remotion-demo --silent

# Review a workspace in Remotion Studio (audio may be missing)
bun run preview --workspace output/my-video

# Generate narration with the existing TTS helper, then render
uv run scripts/tts_from_script.py --script output/my-video/script.json
bun run video --workspace output/my-video
```

Use `--overwrite` to replace an existing MP4. `--silent` explicitly skips audio and subtitles, using scene `durationSeconds` (default 6); it is for drafts and demos only. Normal rendering fails if audio is missing. `--prepare-only` writes props without launching a browser. Preview props are a snapshot: restart the preview command after changing JSON or regenerating audio; React source changes hot-reload in Studio.

## Workspace contract

```text
output/my-video/
  slides.json
  script.json
  audio/slide-01.mp3
  audio/slide-01.srt       # optional, scene-relative times
  video-work/             # generated props, staged media and browser bundle
  video.mp4
```

`script.json` retains the existing TTS format:

```json
[
  {"slide_number": 1, "narration": "先介绍主题，再逐步解释关键内容。"},
  {"slide_number": 2, "narration": "接下来，我们看看这套流程的三个重点。"}
]
```

`slides.json`:

```json
{
  "accent": "#38bdf8",
  "slides": [
    {
      "slide_number": 1,
      "layout": "title",
      "title": "动态视频制作流程",
      "subtitle": "让画面跟着讲解走",
      "model": "EXACT_MODEL_NAME"
    },
    {
      "slide_number": 2,
      "layout": "bullets",
      "title": "三个重点",
      "bullets": ["动态场景", "同步配音", "直接输出视频"]
    }
  ]
}
```

Replace `EXACT_MODEL_NAME` with the actual generating model. Both files must use consecutive slide numbers from 1 with matching counts and non-empty narration.

### Layouts

Every scene needs `slide_number`, `layout`, and `title`. Optional common fields: `subtitle`, `durationSeconds` (silent/preview only), `revealSeconds` (seconds from scene start for each bullet/bar, or the main code/quote block). Model attribution is shown only on the first scene.

| Layout | Additional fields | Animation |
| --- | --- | --- |
| `title` | optional `subtitle`, `model` | Title/subtitle fade and rise |
| `bullets` | `bullets`: 1–6 strings | Progressive reveals |
| `chart` | `bars`: 1–6 `{label, value}` objects; optional `unit` | Horizontal bars grow; values must be non-negative |
| `code` | `code`: string | Code block fade and rise |
| `quote` | `quote`: string; optional `attribution` | Quote fade and rise |

Automatic reveals are compact and occur within narration time. For closer speech alignment, set `revealSeconds` after TTS or use the SRT cue times to choose them manually. They must be ordered, non-negative, and strictly shorter than the audio duration. Subtitles are synchronized to their SRT timestamps; bullet reveals do not automatically follow word timestamps.

Keep titles short, bullets to roughly one line each, and code to roughly 12 short lines. The renderer does not automatically paginate overflowing text. Bar charts show relative magnitude, not a full scientific chart axis. Unsupported visuals (images, line charts, syntax highlighting, complex diagrams) require extending the shared React renderer and data validation/types; they are not built in yet.

## Options and checks

```bash
node scripts/render_video.mjs --help
bun run typecheck
bun run test:video
```

`--subtitles burn|none` controls SRT captions; soft subtitle tracks are not currently supported. Final output is H.264/AAC at 1920×1080 with configurable `--fps` (default 30). Only referenced audio is copied into the browser bundle. Video timing and frame coverage are verified after encoding.

Remotion has its own license terms, including paid licenses for some company/team use. Review [the current license](https://www.remotion.dev/license) before commercial deployment.
