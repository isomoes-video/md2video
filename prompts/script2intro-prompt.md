# md2video script2intro prompt

You are generating a concise video introduction from subtitle timing and narration content.

## Task

Given subtitle files for a rendered presentation, generate a concise video introduction with six parts:

1. **Video Title** — Provide two versions of the title for the same video:
   - Chinese title
   - English title
2. **Tags** — 3 to 10 short topic tags for the video, on their own line as `标签：tag1，tag2，tag3`. These become the Bilibili video tags consumed by the upload stage. Use the subtitle language, drop any leading `#`, and separate tags with full-width commas (`，`).
3. **Summary** — One or more paragraphs describing the overall content of the video, not exceeding 2000 words in total.
4. **Source URL** — If the source content came from a URL (e.g., a blog post, article, or webpage), the exact origin URL **must** be stored in `intro.txt` on its own line as `Source: <origin-url>`. Omit this line only when there is genuinely no source URL.
5. **Output URL** — The `output/` directory is published publicly at https://github.com/isomoes-video/ai-video/, so every presentation's generated assets are browsable online. Always include the public URL for this presentation on its own line as `Output: https://github.com/isomoes-video/ai-video/tree/main/<presentation-slug>`.
6. **Chapter List** — A list of major sections, each on its own line as: `HH:MM  SectionTitle`. The chapter list has a hard maximum of **10 entries**.

---

## Input contract

- Read `output/<presentation-slug>/audio/slide-*.srt`.
- Read `output/<presentation-slug>/script.json` when helpful for fuller context.
- **Source URL discovery is mandatory.** Before writing `intro.txt`, actively search for the origin URL of the source content. Check, in order:
  1. `script.json` fields such as `source`, `url`, `source_url`, or `origin_url`.
  2. The narration text in `script.json` and the burned subtitle text for any explicit URL mentions (`https://...`).
  3. The original user request, recent conversation context, or any input file referenced when the presentation was created.
  4. `output/<presentation-slug>/presentation.html` and any sibling input files for a `Source:` or `Origin:` annotation.
- If the source content came from a URL (a blog post, article, documentation page, etc.), that URL **must** be preserved verbatim in `intro.txt`.
- The output URL is deterministic — no discovery needed. Build it from the presentation slug: `https://github.com/isomoes-video/ai-video/tree/main/<presentation-slug>`.
- Treat slide number order as the source of truth for chapter order.
- Chapters summarize the video at the topic level, not the slide level. Merge adjacent slides that belong to the same topic, including section dividers, transitions, examples, and supporting evidence.
- Treat each slide SRT's actual subtitle timing as the source of spoken timing within that slide.
- Derive the chapter timeline from the real rendered sequence, using the slide audio order and the workflow's configured inter-slide gap.

---

## Format

```text
中文标题：<Chinese title>
English Title: <English title>
标签：<tag1>，<tag2>，<tag3>

Source: <origin-url>
Output: https://github.com/isomoes-video/ai-video/tree/main/<presentation-slug>

<Summary paragraph describing the whole video>

HH:MM  SectionTitle
HH:MM  SectionTitle
HH:MM  SectionTitle
...
```

Rules:
- Always include the `标签：` line directly after the two title lines. Provide 3-10 tags, in the subtitle language, separated by full-width commas (`，`), with no leading `#`. Tags should cover the core topics, named entities, and category (e.g. product names, technique, field) so the video is discoverable.
- The summary can be multiple paragraphs but must not exceed 2000 words in total. It describes the full video content, not individual chapters.
- When the source content came from a URL, you **must** include the origin URL on its own line as `Source: <origin-url>`, placed **before** the summary (right after the two title lines). Use the exact URL — do not shorten, paraphrase, or wrap it in markdown.
- Only omit the `Source:` line when the source genuinely has no URL (e.g., a local file with no upstream origin). When in doubt, include it.
- Always include the `Output:` line with the public output URL `https://github.com/isomoes-video/ai-video/tree/main/<presentation-slug>`, placed directly after the `Source:` line (or where the `Source:` line would be, when there is no source URL). The output is always public, so this line is never omitted.
- Each chapter entry is exactly two parts on one line: timestamp and section title.
- Prefer short chapter titles in the subtitle language, ideally 1-2 words and no more than 3 words.
- The chapter list must contain no more than 10 entries. This is a hard output constraint, not a preference. If there are more than 10 possible boundaries, merge the least important adjacent sections before writing the file.
- Timestamp format: `MM:SS` or `HH:MM:SS`, no milliseconds.
- Use the same language as the subtitle content for the summary and chapter titles.

---

## Output contract

- Write the result inside the same workspace directory: `output/<presentation-slug>/intro.txt`.
- Output only the two titles, the `标签：` line, optional `Source: <origin-url>` line, `Output: <output-url>` line, summary paragraph(s), and chapter list in the final file.
- Do not add preamble, explanation, or extra commentary.

---

## Instructions

1. Read through all `output/<presentation-slug>/audio/slide-*.srt` files in slide order.
2. Use the subtitle content, timing, and `script.json` context to understand the full video.
3. **Locate the source URL.** Search `script.json` metadata fields (`source`, `url`, `source_url`, `origin_url`), narration and subtitle text for `https://...` mentions, the original user request, and sibling input files. If the source content came from a blog, article, or webpage, this URL must end up in `intro.txt`.
4. Generate two video titles for the same content: one in Chinese and one in English.
5. Add a `标签：` line directly after the two title lines with 3-10 topic tags (subtitle language, full-width-comma separated, no `#`).
6. Write a summary (one or more paragraphs, max 2000 words) describing the overall video content in depth.
7. If a source URL was found, add a line `Source: <origin-url>` **before** the summary. Use the URL exactly as found.
8. Add a line `Output: https://github.com/isomoes-video/ai-video/tree/main/<presentation-slug>` directly after the `Source:` line (or in its place when there is no source URL).
9. Identify the major topic shifts or chapter boundaries.
10. For each chapter, output one line: timestamp + very short title.
11. Do not force 10 chapters; choose only the major sections needed.
12. Before saving, count the chapter lines matching `^[0-9]{2}:[0-9]{2}  `. If the count is greater than 10, merge adjacent chapters and recount. Never write an `intro.txt` containing 11 or more chapter lines.
13. Save the output to `output/<presentation-slug>/intro.txt`.

---

## Example Output

Using a presentation about Claude Code benchmark workflows:

```text
中文标题：Claude Code 工作流实测
English Title: Claude Code Workflow Benchmark
标签：Claude Code，大语言模型，AI编程，模型对比，Agent

Source: https://example.com/blog/claude-code-workflow-benchmark
Output: https://github.com/isomoes-video/ai-video/tree/main/claude-code-workflow-benchmark

这个视频比较多个大语言模型在真实 agent 编码工作流中的表现，关注它们在相同任务与环境下的执行质量、速度和完成情况。视频通过统一提示词和统一操作条件，展示不同模型在实际工作流中的差异，并据此讨论它们各自更适合的使用场景。

00:00  开场
01:03  对比
02:46  实测
04:59  Kimi
06:18  结果
07:21  总结
```
