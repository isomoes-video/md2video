# md2video scene prompt

You are preparing source content for an animated HyperFrames video and narration.

Follow `prompts/README.md`: execute automatically through the requested stopping point; preview and approval are opt-in.

## Goals

- Accept any source file type or a direct text prompt.
- Create a dedicated workspace under `output/<presentation-slug>/`.
- Read `video/README.md` for the scene schema, animation behavior, and preview commands.
- Produce `slides.json` for the shared renderer and `script.json` for the existing TTS stage.
- Use the shared HyperFrames renderer exclusively; it renders animated HTML scenes directly to video.
- Keep visible content concise and narration conversational, with natural continuity between scenes.

## Language and attribution

- Write visible text and narration in Chinese. Preserve technical identifiers, commands, paths, code, API names, and proper nouns where appropriate.
- On slide 1, set `model` to the exact name of the model generating the content, without “Created by” or other wording. Do not guess a model name.
- Do not mention the model in narration unless it is part of the source material.

## Scene requirements

- Choose among `title`, `bullets`, `chart`, `code`, and `quote` layouts.
- Use consecutive `slide_number` values starting at 1 in both JSON files.
- Use 1–6 short bullets or bars per scene; keep code to roughly 12 short lines. Avoid text overflow.
- Charts must faithfully represent source data. Clearly label any illustrative data.
- Use a mix of layouts where it serves the explanation, not animation for its own sake.
- `revealSeconds` optionally times bullet/bar appearances relative to scene start. Omit it until narration duration is known, or verify every time is shorter than that audio clip.
- Do not use wall-clock CSS animations, timers, or random values. The shared renderer uses paused GSAP timelines that HyperFrames seeks frame by frame.
- For custom visual requirements, extend `video/Composition.tsx` and the schema deliberately; never silently emit unsupported fields.

## Output contract

- `output/<presentation-slug>/slides.json`: object containing optional `accent` and a non-empty `slides` array, following `video/README.md`.
- `output/<presentation-slug>/script.json`: array of objects with only `slide_number` and `narration`.
- Optional preview files stay inside the same workspace under `video-work/`.
- Scene/title previews are not final covers. Never save a preview frame as `thumbnail.png`; the final cover is generated with Qwen-Image via `prompts/thumbnail-prompt.md` after `intro.txt` is available.
- For a complete video request, proceed directly to TTS after validating the scenes and script; no approval is required unless the user requests it. Publish only when explicitly requested.

## Optional review

Skip preview by default. Only when the user requests a preview, run `bun run preview --workspace output/<presentation-slug>` and share the local HyperFrames Studio URL. Preview allows missing audio, using `durationSeconds` (default 6 seconds) for those scenes. Review layout and animation in Studio, rather than exporting static slides. Pause for approval only if the user explicitly requests that checkpoint.

If a file preview is preferred, render an explicitly silent draft:

```bash
bun run video --workspace output/<presentation-slug> --silent
```

Label it as a silent draft. The final narrated render must use real TTS audio and `--overwrite` if replacing the draft.
