# md2video script2intro prompt

You are generating a concise video introduction from subtitle timing and narration content.

## Task

Given subtitle files for a rendered presentation, generate a concise video introduction with three parts:

1. **Video Title** — Provide two versions of the title for the same video:
   - Chinese title
   - English title
2. **Summary** — One or more paragraphs describing the overall content of the video, not exceeding 2000 words in total.
3. **Chapter List** — A list of major sections, each on its own line as: `HH:MM  SectionTitle`

---

## Input contract

- Read `output/<presentation-slug>/audio/slide-*.srt`.
- Read `output/<presentation-slug>/script.json` when helpful for fuller context.
- If `script.json` or related presentation metadata shows the source content came from a URL, preserve that original URL in the generated introduction.
- Treat slide number order as the source of truth for chapter order.
- Treat each slide SRT's actual subtitle timing as the source of spoken timing within that slide.
- Derive the chapter timeline from the real rendered sequence, using the slide audio order and the workflow's configured inter-slide gap.

---

## Format

```text
中文标题：<Chinese title>
English Title: <English title>

<Summary paragraph describing the whole video>

HH:MM  SectionTitle
HH:MM  SectionTitle
HH:MM  SectionTitle
...
```

Rules:
- The summary can be multiple paragraphs but must not exceed 2000 words in total. It describes the full video content, not individual chapters.
- When the source content came from a URL, include the origin URL in the summary/introduction text, for example as a final line: `Source: <origin-url>`.
- Each chapter entry is exactly two parts on one line: timestamp and section title.
- Prefer short chapter titles in the subtitle language, ideally 1-2 words and no more than 3 words.
- The chapter list must contain no more than 10 entries. Use fewer when major sections should be merged.
- Timestamp format: `MM:SS` or `HH:MM:SS`, no milliseconds.
- Use the same language as the subtitle content for the summary and chapter titles.

---

## Output contract

- Write the result inside the same workspace directory: `output/<presentation-slug>/intro.txt`.
- Output only the two titles, summary paragraph(s), and chapter list in the final file.
- Do not add preamble, explanation, or extra commentary.

---

## Instructions

1. Read through all `output/<presentation-slug>/audio/slide-*.srt` files in slide order.
2. Use the subtitle content, timing, and `script.json` context to understand the full video. Check `script.json` and nearby metadata for source URL fields such as `source`, `url`, `source_url`, or `origin_url`.
3. Generate two video titles for the same content: one in Chinese and one in English.
4. Write a summary (one or more paragraphs, max 2000 words) describing the overall video content in depth. If the source was a URL, keep the exact origin URL in this introduction.
5. Identify the major topic shifts or chapter boundaries.
6. For each chapter, output one line: timestamp + very short title.
7. Do not force 10 chapters; choose only the major sections needed.
8. Save the output to `output/<presentation-slug>/intro.txt`.

---

## Example Output

Using a presentation about Claude Code benchmark workflows:

```text
中文标题：Claude Code 工作流实测
English Title: Claude Code Workflow Benchmark

这个视频比较多个大语言模型在真实 agent 编码工作流中的表现，关注它们在相同任务与环境下的执行质量、速度和完成情况。视频通过统一提示词和统一操作条件，展示不同模型在实际工作流中的差异，并据此讨论它们各自更适合的使用场景。

00:00  开场
01:03  对比
02:46  实测
04:59  Kimi
06:18  结果
07:21  总结
```
