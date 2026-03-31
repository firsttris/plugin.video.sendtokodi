#!/usr/bin/env python3
"""Manual probe for yt-dlp SoundCloud extraction formats."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

try:
    from yt_dlp import YoutubeDL
except Exception:
    ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
    VENDORED_LIB = os.path.join(ROOT_DIR, "lib")
    if VENDORED_LIB not in sys.path:
        sys.path.insert(0, VENDORED_LIB)
    from yt_dlp import YoutubeDL


def _short_url(value: Any, max_len: int = 140) -> str:
    text = str(value or "")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _format_row(fmt: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": fmt.get("format_id"),
        "protocol": fmt.get("protocol"),
        "ext": fmt.get("ext"),
        "acodec": fmt.get("acodec"),
        "vcodec": fmt.get("vcodec"),
        "abr": fmt.get("abr"),
        "audio_ext": fmt.get("audio_ext"),
        "video_ext": fmt.get("video_ext"),
        "manifest_url": bool(fmt.get("manifest_url")),
        "url": _short_url(fmt.get("url")),
    }


def run_probe(url: str) -> int:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = info.get("formats") or []

    print("title:", info.get("title"))
    print("webpage_url:", info.get("webpage_url"))
    print("extractor:", info.get("extractor"))
    print("num_formats:", len(formats))

    print("\nformats:")
    for fmt in formats:
        print(json.dumps(_format_row(fmt), ensure_ascii=True))

    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe SoundCloud extraction output")
    parser.add_argument(
        "url",
        nargs="?",
        default="https://soundcloud.com/chiefkeef/video-shoot-feat-ian",
        help="SoundCloud track URL",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    return run_probe(args.url)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
