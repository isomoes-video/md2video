# md2video plan prompt

You are preparing a markdown blog for narration video production.

## Goals

- Read `source.md`.
- Produce `slides.md` for slidev follow template `reference/technology-template.md
` style.
- Produce `script.json` with one narration entry per slide.
- Keep slide content concise and narration more conversational than the slide text.

## Output contract

- `slides.md`: valid slidev markdown.
- `script.json`: array of objects with `slide_number`, `title`, `slide_markdown`, and `narration`.
