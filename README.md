# md2video

`md2video` is a small agent-friendly workflow for turning source content into a narrated slide video.

## What is in this repo

- `prompts/slide-prompt.md`: create a reveal.js deck, CSS theme, `script.json`, and exported PDF under `output/<presentation-slug>/`.
- `prompts/tts-prompt.md`: generate one narration MP3 per slide from `script.json`.
- `prompts/combine-prompt.md`: combine `output.pdf` and slide MP3s into `video.mp4`.
- `prompts/script2intro-prompt.md`: generate `intro.txt` from `script.json`.
- `prompts/thumbnail-prompt.md`: generate `thumbnail.png` from a crafted Qwen-Image prompt.
- `prompts/upload-prompt.md`: publish `video.mp4` to Bilibili via `scripts/upload_bilibili.py`.
- `scripts/tts_from_script.py`: standalone `uv run` TTS helper.
- `scripts/combine_video.py`: standalone `uv run` video assembly helper.
- `scripts/thumbnail_from_prompt.py`: standalone `uv run` thumbnail image helper.
- `scripts/upload_bilibili.py`: standalone `uv run` Bilibili uploader; reads login cookies straight from the local browser.

## Intended workflow

1. Start with either a source file such as `source.md` or a direct text prompt.
2. Use `prompts/slide-prompt.md` to create a presentation workspace under `output/<presentation-slug>/`.
3. Review the generated presentation workspace and decide whether to continue to the next stage.
4. Use `prompts/tts-prompt.md` to create `output/<presentation-slug>/audio/slide-XX.mp3` files.
5. Use `prompts/combine-prompt.md` to create `output/<presentation-slug>/video.mp4`.
6. Optionally use `prompts/script2intro-prompt.md` to create `output/<presentation-slug>/intro.txt`.
7. Optionally use `prompts/thumbnail-prompt.md` to create `output/<presentation-slug>/thumbnail.png`.
8. Optionally use `prompts/upload-prompt.md` to publish `video.mp4` to Bilibili (title/description come from `intro.txt`, cover from `thumbnail.png`). The upload publishes directly; `--dry-run` is available for troubleshooting.

## Notes

The prompt files are stage-specific on purpose. Pick the prompt that matches the artifact you want to generate, and keep all outputs for a presentation in the same `output/<presentation-slug>/` directory.

## Output submodule

Generated presentations live in the [ai-video](https://github.com/isomoes-video/ai-video) repo, mounted here as the `output/` git submodule. Clone with submodules:

```bash
git clone --recurse-submodules https://github.com/isomoes-video/md2video.git
# or, in an existing clone:
git submodule update --init
```

After generating new artifacts, commit and push inside `output/` first, then commit the updated submodule pointer in this repo.
