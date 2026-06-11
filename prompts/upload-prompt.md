# md2video upload prompt

You are publishing a finished presentation video to Bilibili.

## Goals

- Upload `output/<presentation-slug>/video.mp4` to Bilibili.
- Use the existing `scripts/upload_bilibili.py` script — do not rewrite it.
- Let the script auto-discover metadata from the workspace: title, tags, and description from `intro.txt`, cover from `thumbnail.png`.
- The script logs in automatically using the local browser — the user just needs to be logged into bilibili.com in a supported browser.
- **Always run `--dry-run` first** and confirm the resolved plan with the user before the real upload. Publishing is public and cannot be undone from this workflow.
- Report the final video URL (`https://www.bilibili.com/video/<bvid>`) when the upload completes.

## Input contract

- `output/<presentation-slug>/video.mp4` — the final rendered video (required; produced by the combine stage).
- `output/<presentation-slug>/intro.txt` — strongly recommended (produced by the script2intro stage). The script parses it for:
  - `中文标题：<title>` → the video title, truncated to 80 characters.
  - `标签：tag1，tag2，...` → the video tags (split on `，`/`,`/`、`, deduped, capped at 10). When absent, falls back to the default tags.
  - the summary paragraph(s) → the top of the description.
  - `Source: <url>` → appended to the description as `原文：<url>`.
  - `Output: <url>` → ignored (internal archive link, kept out of the description).
  - `HH:MM  Chapter` lines → parsed only so they stay out of the summary; not added to the description.
  - Description = summary + source joined by blank lines, truncated to 2000 characters.
- `output/<presentation-slug>/thumbnail.png` — recommended cover (produced by the thumbnail stage). When absent, the script extracts a frame at 1s from the video into `video-work/cover.png` and deletes it after the upload.
- Login: the user must be logged into bilibili.com in a supported browser (Chrome / Chromium / Edge / Brave / Vivaldi / Opera / Firefox). The script reads the login automatically; the freshest valid login across browsers wins.
- Fail clearly when `video.mp4` is missing or no browser login can be found; do not improvise credentials.

## Output contract

- A published Bilibili video; the script prints `Done: https://www.bilibili.com/video/<bvid>` on success.
- No new files left in the workspace: the only temporary artifact is the extracted `video-work/cover.png` fallback cover, and the script removes it on exit.
- Report the resulting video URL back to the user verbatim.

## Running the script

Run the existing script with `uv run` (it carries its own inline dependencies):

```bash
# 1. validate the resolved metadata (and browser login) without uploading
uv run scripts/upload_bilibili.py --workspace output/<presentation-slug> --dry-run

# 2. real upload, after the dry-run plan is confirmed
uv run scripts/upload_bilibili.py --workspace output/<presentation-slug>

# restrict the login lookup to one browser
uv run scripts/upload_bilibili.py --workspace output/<presentation-slug> --browser firefox
```

**Key CLI flags:**

- `--workspace` — `output/<presentation-slug>` dir; auto-discovers `video.mp4`, `thumbnail.png`, `intro.txt`.
- `--video` / `--cover` / `--title` / `--desc` — override any auto-discovered piece individually.
- `--tags` — comma-separated, 1-10 tags. Overrides the `标签：` line in `intro.txt`; when neither is given, defaults to `人工智能,科技,AI`.
- `--tid` — Bilibili zone id. Default: `231` (科技 › 计算机技术).
- `--line {bda2,qn,ws,bldsa}` — pin an upload line; default is an automatic speed test.
- `--browser` — limit the login lookup to one browser (`chrome`, `firefox`, …).
- `--dry-run` — resolve and validate everything (including the login check), print the plan, upload nothing.
- `--debug` — verbose login-scan logging to stderr.

## Instructions

1. Verify the workspace: `video.mp4` must exist. If `intro.txt` or `thumbnail.png` is missing, recommend running the script2intro / thumbnail stage first instead of uploading with fallback metadata — only proceed without them when the user explicitly says so.
2. Run the `--dry-run` and review the resolved plan it prints: video, cover, title, tags, tid, login validity, and the description preview.
3. Check the plan makes sense: the title is the intro's 中文标题 (not a slug fallback), the tags are the intro's 标签 (not the generic default), the description carries summary + 原文 link, and `login valid` is `True`. Adjust `--tags`/`--tid` when the intro tags or the default 科技 zone do not fit the topic.
4. Show the plan to the user and get explicit confirmation before uploading.
5. Run the real upload. The script streams progress events (`PREUPLOAD`, `COMPLETE`, …) and finishes with the `https://www.bilibili.com/video/<bvid>` URL — report that URL to the user.

## Troubleshooting

- `Not logged in` / `Incomplete login` — log into bilibili.com in a supported browser, then retry. If the login has expired, re-log in.
- Use `--debug` to see which browsers were scanned, and `--browser <name>` to pin one.

## Implementation notes (for reference only)

- The upload drives `bilibili_api.video_uploader.VideoUploader` with `no_reprint=True` (自制 declaration) and a single-page video.
- Title and description limits (80 / 2000 characters) are enforced by truncation before submission.
- Tags resolve in priority order `--tags` flag → `intro.txt` 标签 line → default list; they are de-duplicated and capped at 10, and an empty result falls back to the defaults.
