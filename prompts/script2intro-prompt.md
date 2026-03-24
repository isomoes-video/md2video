# md2video script2intro prompt

You are generating a concise video introduction from presentation narration.

## Task

Given `output/<presentation-slug>/script.json`, generate a concise video introduction with two parts:

1. **Video Title** — Provide two versions of the title for the same video:
   - Chinese title
   - English title
2. **Summary** — One or more paragraphs describing the overall content of the video, not exceeding 2000 words in total.

---

## Input contract

- Read `output/<presentation-slug>/script.json`.
- `script.json` is an array of objects with only `slide_number` and `narration`.
- Treat the narration text across all slides as the source material for understanding the full video.

---

## Format

```text
中文标题：<Chinese title>
English Title: <English title>

<Summary paragraph describing the whole video>
...
```

Rules:
- The summary can be multiple paragraphs but must not exceed 2000 words in total. It describes the full video content, not individual chapters.
- Use the same language as the narration content for the summary.

---

## Output contract

- Write the result inside the same workspace directory: `output/<presentation-slug>/intro.txt`.
- Output only the two titles and summary paragraph(s) in the final file.
- Do not add preamble, explanation, or extra commentary.

---

## Instructions

1. Read through the entire `output/<presentation-slug>/script.json` file.
2. Generate two video titles for the same content: one in Chinese and one in English.
3. Write a summary (one or more paragraphs, max 2000 words) describing the overall video content in depth.
4. Save the output to `output/<presentation-slug>/intro.txt`.

---

## Example Output

Using a presentation about Claude Code benchmark workflows:

```text
中文标题：Claude Code 工作流实测
English Title: Claude Code Workflow Benchmark

This video examines how multiple large language models perform inside real agent-based coding workflows. It compares execution quality, speed, and task completion behavior under the same working conditions, then explains how each model behaves across practical benchmark tasks.
```
