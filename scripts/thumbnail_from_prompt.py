#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "dashscope>=1.24.6",
# ]
# ///

from __future__ import annotations

import argparse
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable


DEFAULT_MODEL = "qwen-image-2.0-pro"
DEFAULT_SIZE = "2368*1728"  # 4:3, recommended for qwen-image-2.0 series
DEFAULT_BASE_HTTP_API_URL = "https://dashscope.aliyuncs.com/api/v1"
DEFAULT_NEGATIVE_PROMPT = (
    "低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，人脸无细节，"
    "过度光滑，画面具有AI感。构图混乱。文字模糊，扭曲。"
)
DEFAULT_OUTPUT_NAME = "thumbnail.png"
DOWNLOAD_TIMEOUT_SECONDS = 60


def load_prompt_text(prompt_file: Path) -> str:
    text = prompt_file.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Prompt file {prompt_file} is empty")
    return text


def resolve_prompt_text(prompt: str | None, prompt_file: Path | None) -> str:
    if prompt and prompt_file:
        raise SystemExit("Pass either --prompt or --prompt-file, not both.")
    if prompt:
        stripped = prompt.strip()
        if not stripped:
            raise SystemExit("--prompt must not be empty")
        return stripped
    if prompt_file:
        return load_prompt_text(prompt_file)
    raise SystemExit("One of --prompt or --prompt-file is required.")


def resolve_output_paths(
    prompt_file: Path | None, output: Path | None, n: int
) -> list[Path]:
    """Resolve the target PNG paths.

    Defaults to a thumbnail.png next to the prompt file (mirroring how the TTS
    stage writes audio/ next to script.json). With n > 1 the images are
    numbered thumbnail-1.png, thumbnail-2.png, and so on.
    """
    if output is not None:
        base = output
    elif prompt_file is not None:
        base = prompt_file.parent / DEFAULT_OUTPUT_NAME
    else:
        base = Path(DEFAULT_OUTPUT_NAME)

    if n == 1:
        return [base]
    return [
        base.with_name(f"{base.stem}-{index}{base.suffix or '.png'}")
        for index in range(1, n + 1)
    ]


def _get(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def extract_image_urls(response: Any) -> list[str]:
    """Collect image URLs from a multimodal-generation response.

    Works with both plain dicts and the attribute-style response objects
    returned by the DashScope SDK.
    """
    urls: list[str] = []
    choices = _get(_get(response, "output"), "choices") or []
    for choice in choices:
        content = _get(_get(choice, "message"), "content") or []
        for item in content:
            image_url = _get(item, "image")
            if isinstance(image_url, str) and image_url:
                urls.append(image_url)
    return urls


def should_generate(output_paths: list[Path], overwrite: bool) -> bool:
    """Decide whether to call the API, enforcing no-clobber semantics.

    Returns False when every target already exists so reruns stay idempotent.
    A partial set without --overwrite is an error: the API produces all n
    images in one batch, so regenerating would clobber the surviving files.
    """
    if overwrite:
        return True
    existing = [path for path in output_paths if path.exists()]
    if not existing:
        return True
    if len(existing) == len(output_paths):
        return False
    raise SystemExit(
        "Some thumbnail files already exist: "
        + ", ".join(str(path) for path in existing)
        + ". Pass --overwrite to regenerate all of them, or remove them first."
    )


def download_image(url: str) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Image download failed with status {exc.code}: {url}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Image download failed: {exc.reason}") from exc

    if not data:
        raise RuntimeError(f"Image download returned no data: {url}")
    return data


def save_images(
    urls: list[str],
    output_paths: list[Path],
    download: Callable[[str], bytes],
) -> list[Path]:
    if not urls:
        raise RuntimeError("Model returned no image URLs")
    if len(urls) != len(output_paths):
        print(
            f"warning: requested {len(output_paths)} image(s) but received "
            f"{len(urls)}; saving {min(len(urls), len(output_paths))}"
        )

    written_files: list[Path] = []
    for url, output_path in zip(urls, output_paths):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(download(url))
        written_files.append(output_path)
    return written_files


def make_dashscope_generator(
    model: str,
    api_key: str,
    base_http_api_url: str,
    size: str,
    n: int,
    negative_prompt: str,
    prompt_extend: bool,
    watermark: bool,
    seed: int | None,
) -> Callable[[str], list[str]]:
    """Return a generate(prompt) callable that produces image URLs.

    Uses the synchronous multimodal-generation interface, which is the only
    interface supported by the qwen-image-2.0 series. The returned URLs are
    valid for 24 hours, so callers must download them immediately.
    """
    import dashscope
    from dashscope import MultiModalConversation

    dashscope.base_http_api_url = base_http_api_url

    def generate(prompt: str) -> list[str]:
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        extra_params: dict[str, Any] = {}
        if seed is not None:
            extra_params["seed"] = seed

        response = MultiModalConversation.call(
            api_key=api_key,
            model=model,
            messages=messages,
            result_format="message",
            stream=False,
            watermark=watermark,
            prompt_extend=prompt_extend,
            negative_prompt=negative_prompt,
            size=size,
            n=n,
            **extra_params,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope image generation failed with status "
                f"{response.status_code}, code: {response.code}, "
                f"message: {response.message}"
            )

        urls = extract_image_urls(response)
        if not urls:
            raise RuntimeError(
                f"DashScope returned no image for model={model!r} size={size!r}"
            )
        return urls

    return generate


def resolve_api_key() -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY is required for thumbnail generation.")
    return api_key


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a video thumbnail PNG from a text-to-image prompt "
            "using DashScope Qwen-Image."
        ),
    )
    parser.add_argument(
        "--prompt",
        help="Text-to-image prompt passed directly on the command line.",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="Path to a text file containing the text-to-image prompt.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=("Output PNG path. Defaults to thumbnail.png next to the prompt file."),
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Qwen-Image model name. Defaults to {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--size",
        default=DEFAULT_SIZE,
        help=f"Output resolution as width*height. Defaults to {DEFAULT_SIZE} (4:3).",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1,
        choices=range(1, 7),
        help="Number of candidate images to generate (1-6). Defaults to 1.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed in [0, 2147483647] for more stable results.",
    )
    parser.add_argument(
        "--negative-prompt",
        default=DEFAULT_NEGATIVE_PROMPT,
        help="Negative prompt describing content to avoid.",
    )
    parser.add_argument(
        "--no-prompt-extend",
        action="store_true",
        help="Disable server-side prompt rewriting for more precise control.",
    )
    parser.add_argument(
        "--watermark",
        action="store_true",
        help='Add the "Qwen-Image" watermark to the bottom-right corner.',
    )
    parser.add_argument(
        "--base-http-api-url",
        default=DEFAULT_BASE_HTTP_API_URL,
        help="DashScope HTTP API base URL. Defaults to the Beijing endpoint.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate and overwrite existing thumbnail files.",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    api_key = resolve_api_key()
    prompt_file = args.prompt_file.resolve() if args.prompt_file else None
    prompt = resolve_prompt_text(args.prompt, prompt_file)
    output_paths = resolve_output_paths(prompt_file, args.output, args.n)

    if not should_generate(output_paths, args.overwrite):
        for path in output_paths:
            print(path)
        return 0

    generate = make_dashscope_generator(
        model=args.model,
        api_key=api_key,
        base_http_api_url=args.base_http_api_url,
        size=args.size,
        n=args.n,
        negative_prompt=args.negative_prompt,
        prompt_extend=not args.no_prompt_extend,
        watermark=args.watermark,
        seed=args.seed,
    )

    urls = generate(prompt)
    written_files = save_images(urls, output_paths, download=download_image)

    for output_path in written_files:
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
