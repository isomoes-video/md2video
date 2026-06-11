#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "bilibili-api-python==17.4.1",
#   "curl_cffi>=0.7.0",
#   "pycryptodome>=3.20.0",
#   "secretstorage>=3.3.3; sys_platform == 'linux'",
# ]
# ///
"""Upload a finished presentation video to Bilibili.

Login is read automatically from the local browser: you just need to be
logged into bilibili.com in a supported browser. The upload drives
``bilibili_api.video_uploader.VideoUploader``.

Examples
--------
    # auto-discover video/cover/title/tags from a workspace
    ./scripts/upload_bilibili.py --workspace output/claude-fable-5-mythos-5-zh

    # validate the resolved plan without uploading
    ./scripts/upload_bilibili.py --workspace output/<slug> --dry-run

    # restrict the browser scan to one browser
    ./scripts/upload_bilibili.py --workspace output/<slug> --browser firefox
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

# Bilibili stores Chromium expiry as microseconds since the Windows epoch.
WINDOWS_EPOCH_OFFSET_SECONDS = 11_644_473_600
DEFAULT_TID = 231  # 科技 › 计算机技术
DEFAULT_TAGS = ["人工智能", "科技", "AI"]
BILI_DESC_LIMIT = 2000
BILI_TITLE_LIMIT = 80
CHAPTER_RE = re.compile(r"^\s*(\d{1,2}:\d{2}(?::\d{2})?)\b")


# --------------------------------------------------------------------------- #
# Browser cookie extraction (port of blivedm_rs browser_cookies.rs)
# --------------------------------------------------------------------------- #


@dataclass
class Cookie:
    name: str
    value: str
    domain: str
    expires: int | None  # unix seconds, None == session cookie


@dataclass
class Browser:
    """A supported browser and where it keeps its cookie database."""

    name: str
    family: str  # "chromium" | "firefox"
    paths: list[Path]
    keyring_label: str = ""  # Chromium "<X> Safe Storage" keyring entry

    def existing_db(self) -> Path | None:
        for path in self.paths:
            if path.is_file():
                return path
            # Firefox stores cookies under a profile dir we still need to find.
            if self.family == "firefox" and path.is_dir():
                found = _find_firefox_cookie_db(path)
                if found is not None:
                    return found
        return None


def _home() -> Path:
    return Path.home()


def _find_firefox_cookie_db(profiles_dir: Path) -> Path | None:
    if not profiles_dir.is_dir():
        return None
    candidates = sorted(profiles_dir.glob("*/cookies.sqlite"))
    # Prefer the default-release profile, then any default profile.
    for marker in (".default-release", ".default"):
        for candidate in candidates:
            if marker in candidate.parent.name:
                return candidate
    return candidates[0] if candidates else None


def supported_browsers() -> list[Browser]:
    home = _home()
    if sys.platform.startswith("linux"):
        config = home / ".config"
        return [
            Browser("chrome", "chromium", [config / "google-chrome/Default/Cookies"], "Chrome"),
            Browser("chromium", "chromium", [config / "chromium/Default/Cookies"], "Chromium"),
            Browser("edge", "chromium", [config / "microsoft-edge/Default/Cookies"], "Microsoft Edge"),
            Browser("brave", "chromium", [config / "BraveSoftware/Brave-Browser/Default/Cookies"], "Brave"),
            Browser("vivaldi", "chromium", [config / "vivaldi/Default/Cookies"], "Vivaldi"),
            Browser("opera", "chromium", [config / "opera/Default/Cookies"], "Opera"),
            Browser(
                "firefox",
                "firefox",
                [
                    home / ".mozilla/firefox",
                    home / "snap/firefox/common/.mozilla/firefox",
                    home / ".var/app/org.mozilla.firefox/.mozilla/firefox",
                ],
            ),
        ]
    if sys.platform == "darwin":
        app = home / "Library/Application Support"
        return [
            Browser("chrome", "chromium", [app / "Google/Chrome/Default/Cookies"], "Chrome"),
            Browser("chromium", "chromium", [app / "Chromium/Default/Cookies"], "Chromium"),
            Browser("edge", "chromium", [app / "Microsoft Edge/Default/Cookies"], "Microsoft Edge"),
            Browser("brave", "chromium", [app / "BraveSoftware/Brave-Browser/Default/Cookies"], "Brave"),
            Browser("opera", "chromium", [app / "com.operasoftware.Opera/Default/Cookies"], "Opera"),
            Browser("firefox", "firefox", [app / "Firefox/Profiles"]),
        ]
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local"))
        roaming = Path(os.environ.get("APPDATA", home / "AppData/Roaming"))
        return [
            Browser("chrome", "chromium", [local / "Google/Chrome/User Data/Default/Network/Cookies"]),
            Browser("chromium", "chromium", [local / "Chromium/User Data/Default/Network/Cookies"]),
            Browser("edge", "chromium", [local / "Microsoft/Edge/User Data/Default/Network/Cookies"]),
            Browser("brave", "chromium", [local / "BraveSoftware/Brave-Browser/User Data/Default/Network/Cookies"]),
            Browser("firefox", "firefox", [roaming / "Mozilla/Firefox/Profiles"]),
        ]
    return []


def _read_sqlite_rows(db_path: Path, query: str) -> list[tuple]:
    """Copy the (possibly locked) cookie DB to a temp file and query it."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        shutil.copy2(db_path, tmp_path)
        conn = sqlite3.connect(f"file:{tmp_path}?immutable=1", uri=True)
        try:
            return list(conn.execute(query))
        finally:
            conn.close()
    finally:
        tmp_path.unlink(missing_ok=True)


def _read_chromium(browser: Browser, db_path: Path, domain: str) -> list[Cookie]:
    rows = _read_sqlite_rows(
        db_path,
        "SELECT name, value, encrypted_value, host_key, expires_utc "
        "FROM cookies WHERE host_key LIKE '%bilibili.com'",
    )
    key = _chromium_key(browser)
    cookies: list[Cookie] = []
    for name, value, encrypted_value, host_key, expires_utc in rows:
        if domain not in host_key:
            continue
        plain = value or _decrypt_chromium_value(encrypted_value, key)
        if not plain:
            continue
        expires = None
        if expires_utc:
            expires = int(expires_utc) // 1_000_000 - WINDOWS_EPOCH_OFFSET_SECONDS
        cookies.append(Cookie(name, plain, host_key, expires))
    return cookies


def _read_firefox(db_path: Path, domain: str) -> list[Cookie]:
    rows = _read_sqlite_rows(
        db_path,
        "SELECT name, value, host, expiry FROM moz_cookies WHERE host LIKE '%bilibili.com'",
    )
    cookies: list[Cookie] = []
    for name, value, host, expiry in rows:
        if domain not in host or not value:
            continue
        cookies.append(Cookie(name, value, host, int(expiry) if expiry else None))
    return cookies


# --- Chromium value decryption -------------------------------------------- #


def _chromium_key(browser: Browser) -> bytes | None:
    """Derive the AES key Chromium used to encrypt cookie values."""
    try:
        if sys.platform.startswith("linux"):
            return _linux_chromium_key(browser.keyring_label)
        if sys.platform == "darwin":
            return _macos_chromium_key(browser.keyring_label)
    except Exception as exc:  # noqa: BLE001 - degrade to manual cookies
        _debug(f"could not derive {browser.name} key: {exc}")
    return None


def _pbkdf2_aes_key(password: bytes, iterations: int) -> bytes:
    from Crypto.Hash import SHA1
    from Crypto.Protocol.KDF import PBKDF2

    return PBKDF2(password, b"saltysalt", dkLen=16, count=iterations, hmac_hash_module=SHA1)


def _linux_chromium_key(keyring_label: str) -> bytes:
    password = b"peanuts"  # fallback used by Chromium when no keyring is present
    if keyring_label:
        try:
            import secretstorage

            bus = secretstorage.dbus_init()
            collection = secretstorage.get_default_collection(bus)
            if collection.is_locked():
                collection.unlock()
            wanted = f"{keyring_label} Safe Storage"
            for item in collection.get_all_items():
                if item.get_label() == wanted:
                    password = item.get_secret()
                    break
        except Exception as exc:  # noqa: BLE001
            _debug(f"keyring lookup failed ({keyring_label}): {exc}; using fallback")
    return _pbkdf2_aes_key(password, iterations=1)


def _macos_chromium_key(keyring_label: str) -> bytes:
    out = subprocess.run(
        ["security", "find-generic-password", "-w", "-s", f"{keyring_label} Safe Storage"],
        capture_output=True,
        text=True,
        check=True,
    )
    return _pbkdf2_aes_key(out.stdout.strip().encode(), iterations=1003)


def _decrypt_chromium_value(encrypted_value: bytes | None, key: bytes | None) -> str:
    if not encrypted_value:
        return ""
    prefix = encrypted_value[:3]
    if prefix not in (b"v10", b"v11"):
        # Unencrypted store: the plaintext lives in the `value` column already.
        try:
            return encrypted_value.decode("utf-8")
        except UnicodeDecodeError:
            return ""
    if key is None:
        return ""
    body = encrypted_value[3:]
    try:
        if os.name == "nt":
            # Windows uses AES-256-GCM: [12B nonce][ciphertext][16B tag].
            from Crypto.Cipher import AES

            nonce, tag = body[:12], body[-16:]
            cipher = AES.new(_windows_chromium_key(), AES.MODE_GCM, nonce=nonce)
            plain = cipher.decrypt_and_verify(body[12:-16], tag)
        else:
            from Crypto.Cipher import AES

            cipher = AES.new(key, AES.MODE_CBC, b" " * 16)
            padded = cipher.decrypt(body)
            plain = padded[: -padded[-1]]  # strip PKCS#7 padding
    except Exception as exc:  # noqa: BLE001
        _debug(f"cookie decrypt failed: {exc}")
        return ""
    # Chrome >=130 prepends a 32-byte SHA-256 domain hash to the plaintext.
    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError:
        return plain[32:].decode("utf-8", "ignore")


def _windows_chromium_key() -> bytes:
    raise RuntimeError("Windows cookie decryption is not implemented; pass cookies manually")


def collect_browser_cookies(only: str | None = None) -> dict[str, str]:
    """Return the freshest valid bilibili cookies found across browsers."""
    best: dict[str, Cookie] = {}
    now = int(time.time())
    for browser in supported_browsers():
        if only and browser.name != only:
            continue
        db_path = browser.existing_db()
        if db_path is None:
            continue
        _debug(f"scanning {browser.name}: {db_path}")
        try:
            if browser.family == "chromium":
                found = _read_chromium(browser, db_path, "bilibili.com")
            else:
                found = _read_firefox(db_path, "bilibili.com")
        except Exception as exc:  # noqa: BLE001
            _debug(f"  {browser.name} read failed: {exc}")
            continue
        for cookie in found:
            if cookie.expires is not None and cookie.expires < now:
                continue
            current = best.get(cookie.name)
            if current is None or (cookie.expires or 0) > (current.expires or 0):
                best[cookie.name] = cookie
        _debug(f"  found {len(found)} cookie(s)")
    return {name: c.value for name, c in best.items()}


# --------------------------------------------------------------------------- #
# Credential resolution
# --------------------------------------------------------------------------- #


@dataclass
class ResolvedCredentials:
    sessdata: str
    bili_jct: str
    buvid3: str = ""
    dedeuserid: str = ""


def resolve_credentials(args: argparse.Namespace) -> ResolvedCredentials:
    scraped = collect_browser_cookies(only=args.browser)
    sessdata = scraped.get("SESSDATA", "")
    bili_jct = scraped.get("bili_jct", "")
    buvid3 = scraped.get("buvid3", "")
    dedeuserid = scraped.get("DedeUserID", "")

    if not sessdata:
        raise SystemExit(
            "Not logged in: no bilibili login found in any browser. "
            "Log into bilibili.com in a supported browser and retry."
        )
    if not bili_jct:
        raise SystemExit(
            "Incomplete login: re-log into bilibili.com in your browser and retry."
        )
    return ResolvedCredentials(sessdata, bili_jct, buvid3, dedeuserid)


# --------------------------------------------------------------------------- #
# Workspace discovery (video / cover / title / description)
# --------------------------------------------------------------------------- #


@dataclass
class UploadPlan:
    video: Path
    cover: Path
    title: str
    description: str
    tags: list[str]
    tid: int
    line: str | None
    cover_is_temp: bool = False
    extras: dict[str, object] = field(default_factory=dict)


def _split_tags(raw: str) -> list[str]:
    """Split a tag line on ASCII / full-width commas and the Chinese enum comma."""
    return [t.strip().lstrip("#") for t in re.split(r"[，,、]+", raw) if t.strip()]


def _parse_intro(intro_path: Path) -> dict[str, str]:
    """Pull title / tags / source / summary / chapters out of intro.txt."""
    if not intro_path.is_file():
        return {}
    lines = intro_path.read_text(encoding="utf-8").splitlines()
    title = source = tags = ""
    summary_parts: list[str] = []
    chapters: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(r"^中文标题[:：]\s*(.+)$", stripped)
        if m:
            title = title or m.group(1).strip()
            continue
        if re.match(r"^English Title[:：]", stripped):
            continue
        m = re.match(r"^(?:标签|Tags?)[:：]\s*(.+)$", stripped)
        if m:
            tags = tags or m.group(1).strip()
            continue
        m = re.match(r"^Source[:：]\s*(.+)$", stripped)
        if m:
            source = m.group(1).strip()
            continue
        if re.match(r"^Output[:：]", stripped):
            continue  # internal archive URL; not part of the description
        if CHAPTER_RE.match(stripped):
            chapters.append(stripped)
            continue
        summary_parts.append(stripped)
    return {
        "title": title,
        "tags": tags,
        "source": source,
        "summary": "\n".join(summary_parts).strip(),
        "chapters": "\n".join(chapters).strip(),
    }


def _build_description(intro: dict[str, str]) -> str:
    # Chapters are parsed only to keep their HH:MM lines out of the summary;
    # they are intentionally not appended to the published description.
    blocks: list[str] = []
    if intro.get("summary"):
        blocks.append(intro["summary"])
    if intro.get("source"):
        blocks.append(f"原文：{intro['source']}")
    return "\n\n".join(blocks).strip()


def _extract_cover_frame(video: Path, dest: Path) -> Path:
    """Grab a frame from the video as a fallback cover when none is provided."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", str(video),
         "-frames:v", "1", "-q:v", "2", str(dest)],
        check=True,
    )
    return dest


def build_plan(args: argparse.Namespace) -> UploadPlan:
    workspace = args.workspace.resolve() if args.workspace else None

    video = args.video.resolve() if args.video else (workspace / "video.mp4" if workspace else None)
    if not video or not video.is_file():
        raise SystemExit("No video found. Pass --video or a --workspace containing video.mp4.")

    intro = _parse_intro(workspace / "intro.txt") if workspace else {}

    title = args.title or intro.get("title") or (workspace.name if workspace else video.stem)
    title = title[:BILI_TITLE_LIMIT]

    description = args.desc if args.desc is not None else _build_description(intro)
    description = description[:BILI_DESC_LIMIT]

    if args.tags:
        tags = _split_tags(args.tags)
    elif intro.get("tags"):
        tags = _split_tags(intro["tags"])
    else:
        tags = list(DEFAULT_TAGS)
    tags = [t for t in dict.fromkeys(tags) if t][:10] or list(DEFAULT_TAGS)

    cover_is_temp = False
    if args.cover:
        cover = args.cover.resolve()
        if not cover.is_file():
            raise SystemExit(f"--cover not found: {cover}")
    elif workspace and (workspace / "thumbnail.png").is_file():
        cover = workspace / "thumbnail.png"
    else:
        work_dir = (workspace or video.parent) / "video-work"
        cover = _extract_cover_frame(video, work_dir / "cover.png")
        cover_is_temp = True

    return UploadPlan(
        video=video,
        cover=cover,
        title=title,
        description=description,
        tags=tags,
        tid=args.tid,
        line=args.line,
        cover_is_temp=cover_is_temp,
    )


# --------------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------------- #


async def run_upload(plan: UploadPlan, creds: ResolvedCredentials, dry_run: bool) -> int:
    from bilibili_api import Credential, video_uploader

    credential = Credential(
        sessdata=creds.sessdata,
        bili_jct=creds.bili_jct,
        buvid3=creds.buvid3 or None,
        dedeuserid=creds.dedeuserid or None,
    )

    try:
        valid = await credential.check_valid()
    except Exception:  # noqa: BLE001 - older API versions, or offline
        valid = None
    if valid is False:
        raise SystemExit("Credential rejected by bilibili (expired SESSDATA?). Re-log in.")

    meta = video_uploader.VideoMeta(
        tid=plan.tid,
        title=plan.title,
        desc=plan.description,
        tags=plan.tags,
        cover=str(plan.cover),
        no_reprint=True,
    )

    line = None
    if plan.line:
        line = video_uploader.Lines[plan.line.upper()]

    if dry_run:
        print("Dry run — nothing uploaded. Resolved plan:")
        _print_plan(plan, valid)
        return 0

    page = video_uploader.VideoUploaderPage(
        path=str(plan.video), title=plan.title, description=plan.description
    )
    uploader = video_uploader.VideoUploader([page], meta, credential, line=line)

    result: dict[str, object] = {}

    @uploader.on("__ALL__")
    async def _on_event(data: dict) -> None:
        name = data.get("name", "?")
        payload = data.get("data")
        if name in ("PRE_CHUNK", "AFTER_CHUNK"):
            return  # too chatty
        print(f"[{name}] {payload if payload is not None else ''}".rstrip())
        if name == "COMPLETE" and isinstance(payload, dict):
            result.update(payload)

    print(f"Uploading {plan.video.name} → {plan.title!r} (tid={plan.tid})")
    data = await uploader.start()
    if isinstance(data, dict):
        result.update(data)

    bvid = result.get("bvid")
    if bvid:
        print(f"\nDone: https://www.bilibili.com/video/{bvid}")
    else:
        print(f"\nDone: {result}")
    return 0


def _print_plan(plan: UploadPlan, valid: bool | None) -> None:
    print(f"  video       : {plan.video}")
    print(f"  cover       : {plan.cover}{' (extracted)' if plan.cover_is_temp else ''}")
    print(f"  title       : {plan.title}")
    print(f"  tags        : {', '.join(plan.tags)}")
    print(f"  tid         : {plan.tid}")
    print(f"  line        : {plan.line or 'auto'}")
    print(f"  login valid : {valid if valid is not None else 'unchecked'}")
    desc = plan.description or "(empty)"
    preview = desc if len(desc) <= 280 else desc[:280] + "…"
    print("  description :")
    for line in preview.splitlines() or ["(empty)"]:
        print(f"    {line}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

_DEBUG = False


def _debug(message: str) -> None:
    if _DEBUG:
        print(f"debug: {message}", file=sys.stderr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload a presentation video to Bilibili using your local browser login.",
    )
    parser.add_argument(
        "--workspace", type=Path,
        help="output/<slug> dir; auto-discovers video.mp4, thumbnail.png, intro.txt.",
    )
    parser.add_argument("--video", type=Path, help="Video file (overrides workspace/video.mp4).")
    parser.add_argument("--cover", type=Path, help="Cover image (overrides thumbnail.png).")
    parser.add_argument("--title", help="Video title (overrides intro.txt 中文标题).")
    parser.add_argument("--desc", help="Description (overrides the one built from intro.txt).")
    parser.add_argument(
        "--tags",
        help="Comma-separated tags (1-10). Overrides the intro.txt 标签 line. "
        "Falls back to that line, then to: " + ",".join(DEFAULT_TAGS),
    )
    parser.add_argument("--tid", type=int, default=DEFAULT_TID, help=f"Zone id. Default {DEFAULT_TID}.")
    parser.add_argument(
        "--line", choices=["bda2", "qn", "ws", "bldsa"],
        help="Upload line. Default: auto speed-test.",
    )
    parser.add_argument(
        "--browser",
        help="Limit the login lookup to one browser (chrome/firefox/edge/brave/...).",
    )

    parser.add_argument("--dry-run", action="store_true", help="Resolve and validate without uploading.")
    parser.add_argument("--debug", action="store_true", help="Verbose login-scan logging to stderr.")
    return parser.parse_args(argv)


def main() -> int:
    global _DEBUG
    args = parse_args()
    _DEBUG = args.debug

    plan = build_plan(args)
    creds = resolve_credentials(args)

    from bilibili_api import sync

    try:
        return sync(run_upload(plan, creds, args.dry_run))
    finally:
        if plan.cover_is_temp:
            Path(plan.cover).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
