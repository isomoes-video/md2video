# md2video thumbnail prompt

## Task

Given a finished presentation's intro (`output/<presentation-slug>/intro.txt`), generate **one** thumbnail image that works as the video cover on YouTube and Bilibili.

The thumbnail should visually represent the video's core topic — striking and instantly readable at feed size, rendered in whatever art direction best fits *this* video (not a fixed house style), with the Chinese video title rendered inside the image (Qwen-Image excels at complex Chinese text rendering).

Use the existing `scripts/thumbnail_from_prompt.py` script — do not rewrite it.

---

## Input

`output/<presentation-slug>/intro.txt` is the **only** content source. Do not read `script.json`, `styles.css`, or `presentation.html`.

The intro file looks like:

```
中文标题：<Chinese title>
English Title: <English title>

Source: <url>

<one-paragraph Chinese summary of the video>

00:00  <chapter>
00:22  <chapter>
...
```

`DASHSCOPE_API_KEY` must be set; the thumbnail stage is DashScope-only.

---

## Instructions

1. Read `intro.txt`: the Chinese title, the English title, and the summary paragraph.
2. Identify the single most important visual concept of the video — one scene, not a collage.
3. Compose one Chinese text-to-image prompt that:
   - **Opens by naming a deliberate art direction** chosen to fit this specific topic and to look different from recent covers — not a reflexive sci-fi/neon scene. See "Visual style — make every thumbnail look different".
   - Describes one concrete scene: composition, foreground/background, lighting, mood.
   - Is visually bold within the chosen style — a clean focal point that survives thumbnail size.
   - **Renders the Chinese title inside the image** as large, high-contrast typography. Quote every piece of rendered text with `“”` or `「」` and state where it appears, for example: 画面上方以醒目的白色大字标题写着「……」.
   - **Composes for the full 16:9 frame** — use the whole width boldly; keep the lower-right corner clear for the duration badge.
4. Save the exact prompt to `output/<presentation-slug>/thumbnail-prompt.txt` so the thumbnail is reproducible.
5. Run the script **once** to generate `output/<presentation-slug>/thumbnail.png` with `qwen-image-2.0-pro` at `2688*1536` (16:9). Generate exactly one image — never pass `--n` to produce multiple candidates.

---

## Running the script

```bash
uv run scripts/thumbnail_from_prompt.py \
  --prompt-file output/<presentation-slug>/thumbnail-prompt.txt \
  --size '2688*1536'
```

The script calls the DashScope synchronous multimodal-generation API, downloads the returned image immediately (the URL expires after 24 hours), and writes `thumbnail.png` next to the prompt file.

**Key CLI flags:**

- `--prompt-file` — path to the crafted prompt text file (preferred over `--prompt`).
- `--size` — always pass `2688*1536` (16:9, YouTube/Bilibili cover ratio) explicitly; do not rely on the script's built-in default.
- `--output` — override the output PNG path (default: `thumbnail.png` next to the prompt file).
- `--seed` — fix the random seed for more stable regeneration.
- `--no-prompt-extend` — disable server-side prompt rewriting when exact control over rendered text matters.
- `--overwrite` — regenerate even when `thumbnail.png` already exists (reruns are otherwise idempotent and skip the API call).

---

## Visual style — make every thumbnail look different

The biggest failure mode of this stage is **sameness**: every cover drifting into the same `深蓝色数字空间 + 霓虹蓝紫 + 发光水晶/能量球 + 科幻电影感` look. That is not a house style — it is just the path of least resistance, and a channel where every cover looks identical is one viewers scroll past.

Before composing, deliberately pick an art direction that fits *this* video and differs from recent covers. Treat sci-fi/neon as **one option among many, not the default** — reach for it only when the topic is genuinely about that, and even then find a fresher take. State the chosen style as the **first words** of the prompt (Qwen weights the opening hardest), e.g. `等距 3D 黏土渲染：……` or `复古丝网印刷海报：……`.

Pick or mix from a wide palette — let the topic drive the choice:

| 题材线索 | 可选风格方向 |
| --- | --- |
| 硬件 / 产品 / 评测 | 微距实拍、产品棚光摄影、爆炸图 exploded view |
| 工具 / 工作流 / 效率 | 扁平矢量插画、等距 isometric 微缩场景、信息图 |
| 历史 / 人文 / 文化 | 水墨、工笔、剪纸、浮世绘、国潮、油画 |
| 财经 / 数据 / 商业 | 瑞士国际主义版式、Bauhaus 几何、立体数据图表 |
| 新闻 / 观点 / 人物 | 黑白高反差摄影、杂志封面、电影剧照 |
| 趣味 / 科普 / 故事 | 黏土定格动画、手绘白板、拼贴 collage、像素风 |

This table is a starting palette, not a closed list — combine, subvert, or invent a direction when the topic suggests one. To add real variation across runs, vary `--seed` and start each prompt fresh from the topic + chosen style; never copy a previous prompt's wording.

---

## Prompt template (adapt, don't copy)

A reliable thumbnail prompt follows the proven order *topic → emotion → visual hook → focal point → text → composition → constraints*, adapted for Chinese covers. Adapt this skeleton — do **not** paste it verbatim:

```
<风格方向>：<一句话主体场景：主角 + 动作或状态 + 前景/背景>，<光线与氛围>，<高对比度配色>。构图铺满 16:9 宽幅画面，右下角留空。画面上方中央以醒目的大字标题写着「<≤12字标题>」，下方一行小字标签写着「<可选关键词>」。
```

1. **风格方向** — the art direction, first (see the table above).
2. **主体场景** — one concrete subject doing or being something; this is the "visual hook", and it should carry an emotion, not just depict the topic.
3. **光线与氛围** — 棚光 / golden hour / 逆光 / 戏剧侧光 — this single detail sets the mood.
4. **配色** — name a high-contrast scheme (深底亮主体 or 亮底深主体); avoid muddy mid-tones.
5. **构图约束** — compose boldly for the full 16:9 frame; keep the lower-right corner clear.
6. **文字** — quote every rendered string with `「」`, put each text block on its own line, and state its position; ask for a font *style* (`简洁无衬线`, `书法体`, `衬线`), never a brand font name.

**Qwen text-rendering notes:** quoting strings raises rendering accuracy sharply (≈65% → 96%); one big title plus at most one short subhead is the safe ceiling — more text means more garbled glyphs; naming a font *style* works, naming a font *brand* does not.

---

## Prompt guidelines

- One powerful visual + a short bold title — that is the whole thumbnail.
- Keep rendered text short and few: one main title (ideally ≤ 12 个汉字 — abbreviate the `intro.txt` title if needed), plus at most 1-2 short keyword labels. More text means more rendering errors.
- Design for the platform feed: most viewers see the thumbnail tiny and on mobile — large high-contrast title, simple composition, no dense detail that disappears at small sizes.
- Keep the lower-right corner free of text: YouTube and Bilibili overlay the video duration badge there.
- Keep technical identifiers and product names (for example Claude Code, MCP, API) in their original language.
- Stay well under the 1300-token prompt limit of the qwen-image-2.0 series; anything longer is truncated automatically.
- Do not put watermark, logo, or border instructions in the prompt; the script already disables the watermark.
- Good (科幻，仅当题材真正契合): `深蓝色数字隧道中，三枚发光的能量球并排疾驰，速度线与霓虹光效，电影感，高对比度。画面中央以醒目的白色大字标题写着「Agent 实测对比」`
- Good (扁平插画): `扁平矢量插画，明黄底色，中央一枚被放大镜照亮的红色邮票图标，简洁几何阴影。画面上方以黑色无衬线大字标题写着「邮件协议简史」，左右两侧留白`
- Good (等距 3D): `等距 3D 微缩渲染：木质书桌上一台打开的笔记本电脑，桌面漂浮着齿轮与文档图标，柔和棚光，奶油色背景。画面顶部以深蓝大字标题写着「自动化工作流」`
- Good (水墨国风): `水墨国风，远山云雾间一条蜿蜒河流，大量留白，淡赭与墨色。画面右上以书法体黑字标题写着「长江文明」，左右延伸纯宣纸留白`
- Avoid: vague prompts like 「一张与 AI 相关的图片」
- Avoid: rendering the full long title or whole sentences — abbreviate to a punchy phrase.
- Avoid: defaulting to the `深蓝数字空间 / 霓虹 / 发光水晶` sci-fi look out of habit — use it only when the topic truly calls for it.

---

## Output

- `output/<presentation-slug>/thumbnail-prompt.txt`: the exact prompt text sent to the model, nothing else.
- `output/<presentation-slug>/thumbnail.png`: one generated PNG, `2688*1536` (16:9).

---

## Example

Given `output/claude-fable-5-mythos-5-zh/intro.txt`:

```
中文标题：Claude Fable 5 与 Mythos 5：把能力放到最强，把风险关到最小
English Title: Claude Fable 5 and Claude Mythos 5

这个视频解读 Anthropic 发布的官方公告，介绍迄今最强的 Mythos 级模型……
```

The same intro can be rendered many ways — pick the one that fits and looks fresh, then save **only that one** to `thumbnail-prompt.txt`. Three valid directions for this topic:

A — 科幻 (the obvious default; fine here because the topic is AI models, but not the only choice):

```
电影感科幻场景：深蓝色数字空间中，两枚发光的水晶核心并排悬浮，左侧一枚被三层透明防护环包裹，右侧一枚完全裸露、光芒更锐利。高对比度，霓虹蓝紫光效，右下角留空。画面上方中央以醒目的白色大字标题写着「Claude Fable 5 与 Mythos 5」，标题下方一行小字标签写着「同一模型 · 两种发布」
```

B — 博物馆陈列 (a fresher take on "same specimen, two displays"):

```
博物馆陈列摄影：温暖的射灯下，两个并排的玻璃罩各罩着一枚一模一样的发光晶体标本，左罩密封并贴着「保障」封条，右罩敞开、晶体更明亮锐利。深色背景，高级感，浅景深，右下角留空。画面上方中央以白色衬线大字标题写着「Claude Fable 5 与 Mythos 5」，下方一行小字写着「同一模型 · 两种发布」
```

C — 编辑海报 (typographic, no sci-fi at all):

```
极简编辑海报，画面由一条垂直线分成左右两半：左半冷蓝、有一把合上的锁的图标，右半暖橙、同一图标但锁已打开。大面积留白，瑞士国际主义版式，高对比度，右下角留空。画面上方中央以黑色无衬线大字标题写着「Fable 5 与 Mythos 5」，下方一行小字写着「同一模型 · 两种发布」
```

Run the chosen prompt with `--size '2688*1536'`; result saved as `output/claude-fable-5-mythos-5-zh/thumbnail.png`.
