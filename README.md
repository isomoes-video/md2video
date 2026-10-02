# md2video

`md2video` is a small agent-friendly workflow for turning source content into an animated, narrated video with HyperFrames. Videos render directly from HTML/CSS scenes and seekable GSAP animations, not static PDF pages.

The renderer uses HyperFrames while preserving the existing scene JSON, narration, and audio workspace format. See [CHANGELOG.md](CHANGELOG.md) for the history.

## What is in this repo

- `prompts/slide-prompt.md`: create animated scene data (`slides.json`) and narration (`script.json`) under `output/<presentation-slug>/`.
- `prompts/tts-prompt.md`: generate one narration MP3 per slide from `script.json`.
- `prompts/combine-prompt.md`: render scenes, narration MP3s, and available SRT captions into `video.mp4` with HyperFrames.
- `prompts/script2intro-prompt.md`: generate `intro.txt` from `script.json`.
- `prompts/thumbnail-prompt.md`: generate `thumbnail.png` from a crafted Qwen-Image prompt.
- `prompts/upload-prompt.md`: publish `video.mp4` to Bilibili via `scripts/upload_bilibili.py`.
- `scripts/tts_from_script.py`: standalone `uv run` TTS helper.
- `scripts/render_video.mjs`: HyperFrames preview, HTML/timeline preparation, and narrated video renderer.
- `video/`: reusable animated layouts; see [the scene schema and renderer guide](video/README.md).
- `examples/hyperframes-demo/`: a five-scene animation demo that renders without API credentials.
- `scripts/thumbnail_from_prompt.py`: standalone `uv run` thumbnail image helper.
- `scripts/upload_bilibili.py`: standalone `uv run` Bilibili uploader; reads login cookies straight from the local browser.

## Intended workflow

Install dependencies with `bun install`; Node.js 22+ and FFmpeg/FFprobe must be available. HyperFrames provisions a headless browser when needed. For a quick animation demo:

```bash
bun run video --workspace examples/hyperframes-demo --silent
```

1. Start with either a source file such as `source.md` or a direct text prompt.
2. Use `prompts/slide-prompt.md` to create a presentation workspace under `output/<presentation-slug>/`.
3. Review animations with `bun run preview --workspace output/<presentation-slug>` and decide whether to continue.
4. Use `prompts/tts-prompt.md` to create `output/<presentation-slug>/audio/slide-XX.mp3` files.
5. Use `prompts/combine-prompt.md`, or run `bun run video --workspace output/<presentation-slug>`, to create `video.mp4` directly with HyperFrames.
6. Optionally use `prompts/script2intro-prompt.md` to create `output/<presentation-slug>/intro.txt`.
7. Optionally use `prompts/thumbnail-prompt.md` to create `output/<presentation-slug>/thumbnail.png`.
8. Optionally use `prompts/upload-prompt.md` to publish `video.mp4` to Bilibili (title/description come from `intro.txt`, cover from `thumbnail.png`). The upload publishes directly; `--dry-run` is available for troubleshooting.

## Notes

The prompt files are stage-specific on purpose. Pick the prompt that matches the artifact you want to generate, and keep all outputs for a presentation in the same `output/<presentation-slug>/` directory.

HyperFrames is the only supported renderer. Workspaces need scene data, narration, and audio. Existing generated artifacts are not migrated or deleted automatically. See [video/README.md](video/README.md) for requirements and limitations.

## Output submodule

Generated presentations live in the [ai-video](https://github.com/isomoes-video/ai-video) repo, mounted here as the `output/` git submodule. Clone with submodules:

```bash
git clone --recurse-submodules https://github.com/isomoes-video/md2video.git
# or, in an existing clone:
git submodule update --init
```

After generating new artifacts, commit and push inside `output/` first, then commit the updated submodule pointer in this repo.
