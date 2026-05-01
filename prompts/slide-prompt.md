# md2video plan prompt

You are preparing source content for reveal.js presentation and narration production.

## Goals

- Accept any input file type, not only `*.md`.
- Use the provided file content directly as source context.
- Plan a reveal.js presentation.
- Write all generated output under `output/`.
- Produce a presentation HTML file and CSS theme suitable for direct browser viewing with no build step.
- Produce `script.json` with one narration entry per slide.
- Produce a PDF export where each slide is rendered as its own PDF page.
- Keep slide content concise and narration more conversational than the slide text.
- Ensure narration flows smoothly from slide to slide, avoiding abrupt topic jumps between consecutive `script.json` entries.

## Presentation requirements

- Create the presentation by following the `skills/revealjs/SKILL.md` workflow and requirements.
- Treat `skills/revealjs/SKILL.md` as the source of truth for presentation structure, styling, review, and export rules.

## Language requirements

- Write all visible slide content in Chinese, including titles, headings, bullets, labels, captions, callouts, and chart text.
- Write all `script.json` narration in Chinese.
- Keep technical identifiers, file paths, code snippets, commands, API names, product names, and proper nouns in their original language unless a widely accepted Chinese translation exists.
- If the source content is not Chinese, translate and localize it naturally instead of copying English wording onto the slides.

## Output contract

- Output directory: create a dedicated subdirectory under `output/` for the presentation, for example `output/<presentation-slug>/`.
- `output/<presentation-slug>/presentation.html`: valid reveal.js presentation HTML.
- `output/<presentation-slug>/styles.css`: custom presentation theme CSS.
- `output/<presentation-slug>/script.json`: array of objects with only `slide_number` and `narration`.
- `output/<presentation-slug>/output.pdf`: exported PDF with one slide per page.

## Narration continuity requirements

- Write `script.json` as a connected talk, not as isolated slide summaries.
- Each narration entry should feel like a natural continuation of the previous slide and a setup for the next one.
- Use brief transition phrasing when needed, such as introducing the next point, contrasting with the prior slide, or summarizing before moving on.
- Avoid repetitive hard resets like reintroducing the topic from scratch on each slide unless the structure explicitly requires it.
- Keep transitions subtle and conversational, not formulaic.

## Export requirements

- Export the final deck to PDF after slide review.
- The PDF must preserve slide pagination so each reveal.js slide becomes a single PDF page.
- If screenshots or preview assets are generated during review, keep them separate from the final PDF deliverable.
- Any review artifacts should also stay inside the same `output/<presentation-slug>/` workspace, such as `output/<presentation-slug>/screenshots/`.
