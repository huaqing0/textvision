#!/usr/bin/env python3
"""Fallback helper for image-unsupported models.

This helper is intentionally small and platform-neutral. It receives JSON on stdin
and decides whether to pass the original message through or replace image paths
with textvision output.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List

IMAGE_EXT_RE = r"(?:png|jpe?g|webp|bmp|gif|tiff?|svg)"
QUOTED_IMAGE_PATH_RE = re.compile(
    r"(?P<quote>[\"'])(?P<path>[^\"'\r\n]+\." + IMAGE_EXT_RE + r")(?P=quote)",
    re.IGNORECASE,
)
PREFIXED_IMAGE_PATH_RE = re.compile(
    r"(?P<path>(?:~|\.{1,2}/|/|[A-Za-z]:\\)[^\"'`\r\n<>]*?\." + IMAGE_EXT_RE + r")\b",
    re.IGNORECASE,
)
BARE_IMAGE_PATH_RE = re.compile(
    r"(?<![\w./\\-])(?P<path>[^\"'`\s<>/\\]+\." + IMAGE_EXT_RE + r")\b",
    re.IGNORECASE,
)
TEXTVISION_TIMEOUT_SECONDS = 120


def normalize_image_support(value):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1", "supported", "supports_images"}:
            return True
        if normalized in {"false", "no", "0", "unsupported", "text_only", "text-only", "no_images", "no-images"}:
            return False
    return None


def find_image_paths(text: str) -> List[str]:
    candidates = []
    covered_spans = []
    paths: List[str] = []
    for pattern in (QUOTED_IMAGE_PATH_RE, PREFIXED_IMAGE_PATH_RE):
        for match in pattern.finditer(text or ""):
            start, end = match.span("path")
            candidates.append((start, match.group("path")))
            covered_spans.append((start, end))
    for match in BARE_IMAGE_PATH_RE.finditer(text or ""):
        start, _ = match.span("path")
        if any(span_start <= start < span_end for span_start, span_end in covered_spans):
            continue
        candidates.append((start, match.group("path")))
    for _, raw_path in sorted(candidates, key=lambda item: item[0]):
        raw = raw_path.strip().strip('"\'')
        if raw.startswith("//"):
            continue
        p = Path(raw).expanduser()
        if p.exists() and p.is_file():
            paths.append(str(p.resolve()))
    # preserve order, dedupe
    return list(dict.fromkeys(paths))


def textvision(path: str, question: str | None = None) -> str:
    cmd = ["textvision", path]
    if question:
        cmd += ["--question", question]
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=False,
            timeout=TEXTVISION_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return "textvision command not found. Install TextVision or add its bin directory to PATH."
    except subprocess.TimeoutExpired:
        return f"textvision timed out after {TEXTVISION_TIMEOUT_SECONDS} seconds for {path}."
    except Exception as exc:
        return f"textvision failed to start for {path}: {exc}"
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
        return f"textvision failed for {path}: {detail}"
    return proc.stdout.strip()


def emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        emit({"action": "error", "error": f"Invalid JSON payload: {exc}"})
        return 0

    message = payload.get("message", "")
    model_supports_images = normalize_image_support(payload.get("model_supports_images", None))
    last_error = (payload.get("last_error") or "").lower()

    paths = find_image_paths(message)
    if not paths:
        emit({"action": "pass_through"})
        return 0

    image_error_markers = [
        "image input not supported",
        "image inputs are not supported",
        "unsupported media type",
        "unsupported image",
        "does not support image",
        "does not accept images",
        "cannot process image",
        "image unsupported",
        "images are not supported",
        "vision is not supported",
        "multimodal input is not supported",
        "only text input",
        "不支持图片",
        "不支持图像",
        "无法处理图片",
        "无法处理图像",
        "不能处理图片",
        "不能处理图像",
        "图片输入不支持",
        "图像输入不支持",
    ]
    failed_due_to_image = any(m in last_error for m in image_error_markers)

    if model_supports_images is True and not failed_due_to_image:
        emit({"action": "pass_through"})
        return 0

    if model_supports_images is False or failed_due_to_image:
        contexts = [textvision(p, question=message) for p in paths]
        emit({"action": "replace_with_context", "contexts": contexts})
        return 0

    # Unknown capability: caller should try direct image first, then call us again
    # with last_error if that fails.
    emit({"action": "try_direct_first", "image_paths": paths})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
