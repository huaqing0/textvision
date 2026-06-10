#!/usr/bin/env python3
"""Convert images into text evidence packets for text-only AI models.

Backend policy:
- macOS: Apple Vision OCR by default.
- Windows: Windows native OCR by default.
- Linux / no native OCR: PaddleOCR by default when installed.
- SVG: direct XML/text parsing.
- Optional: PaddleOCR high-accuracy backend on any OS.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import traceback
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore

VERSION = "0.4.0"
RASTER_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif"}
SVG_EXTS = {".svg"}
SUPPORTED_EXTS = RASTER_EXTS | SVG_EXTS
OCR_SUBPROCESS_TIMEOUT_SECONDS = 90


@dataclass
class TextItem:
    text: str
    confidence: Optional[float] = None
    source: str = "ocr"
    box: Optional[Any] = None


def human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{n} B"


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def read_file_info(path: Path) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "path": str(path),
        "filename": path.name,
        "extension": path.suffix.lower(),
        "file_size_bytes": path.stat().st_size,
        "file_size": human_bytes(path.stat().st_size),
        "modified_time": iso_mtime(path),
    }

    ext = path.suffix.lower()
    if ext in RASTER_EXTS:
        if Image is None:
            info["image_parse_warning"] = "Pillow is not available; dimensions were not read."
            return info
        try:
            with Image.open(path) as img:
                info.update({
                    "format": img.format,
                    "width": img.width,
                    "height": img.height,
                    "mode": img.mode,
                })
                try:
                    exif = img.getexif()
                    if exif:
                        non_empty = {k: v for k, v in exif.items() if v not in (None, "", b"")}
                        info["exif_tag_count"] = len(exif)
                        info["exif_non_empty_tag_count"] = len(non_empty)
                except Exception:
                    pass
        except Exception as exc:
            info["image_parse_warning"] = f"Image metadata could not be parsed: {exc}"
    elif ext in SVG_EXTS:
        info["format"] = "SVG"
        try:
            root = ET.parse(path).getroot()
            for attr in ("width", "height", "viewBox"):
                if root.get(attr):
                    info[attr] = root.get(attr)
        except Exception:
            info["svg_parse_warning"] = "SVG metadata could not be parsed."
    return info


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def dedupe_items(items: Iterable[TextItem]) -> List[TextItem]:
    seen: Set[str] = set()
    out: List[TextItem] = []
    for item in items:
        text = item.text.strip()
        if not text:
            continue
        key = f"{item.source}:{text}"
        if key not in seen:
            seen.add(key)
            out.append(TextItem(text=text, confidence=item.confidence, source=item.source, box=item.box))
    return out


def parse_svg_text(path: Path) -> List[TextItem]:
    items: List[TextItem] = []
    tree = ET.parse(path)
    root = tree.getroot()
    for elem in root.iter():
        tag = strip_ns(elem.tag).lower()
        if tag in {"title", "desc", "text", "tspan"}:
            text = " ".join("".join(elem.itertext()).split())
            if text:
                items.append(TextItem(text=text, source=f"svg:{tag}"))
        for attr in ("aria-label", "alt", "title", "data-label"):
            value = elem.get(attr)
            if value and value.strip():
                items.append(TextItem(text=value.strip(), source=f"svg-attr:{attr}"))
    return dedupe_items(items)


def coerce_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def run_macos_vision(path: Path, languages: Optional[str] = None) -> List[TextItem]:
    if platform.system() != "Darwin":
        raise RuntimeError("Apple Vision OCR is only available on macOS.")
    if shutil.which("swift") is None:
        raise RuntimeError("swift command not found. Install Xcode Command Line Tools.")
    script = Path(__file__).with_name("macos_vision_ocr.swift")
    if not script.exists():
        raise RuntimeError(f"Apple Vision helper not found: {script}")
    cmd = ["swift", str(script)]
    if languages:
        cmd += ["--languages", languages]
    cmd.append(str(path))
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=OCR_SUBPROCESS_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Apple Vision OCR timed out after {OCR_SUBPROCESS_TIMEOUT_SECONDS} seconds.") from exc
    raw = proc.stdout.strip() or proc.stderr.strip()
    try:
        data = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"Apple Vision returned non-JSON output: {raw[:500]}") from exc
    if not data.get("ok"):
        raise RuntimeError(data.get("error") or "Apple Vision OCR failed.")
    items: List[TextItem] = []
    for item in data.get("items", []) or []:
        text = item.get("text", "")
        if text and text.strip():
            items.append(TextItem(text=text.strip(), confidence=coerce_float(item.get("confidence")), source="apple_vision", box=item.get("box")))
    return dedupe_items(items)


def run_windows_ocr(path: Path, language: Optional[str] = None) -> List[TextItem]:
    if platform.system() != "Windows":
        raise RuntimeError("Windows OCR is only available on Windows.")
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if ps is None:
        raise RuntimeError("PowerShell not found; cannot call Windows OCR.")
    script = Path(__file__).with_name("windows_ocr.ps1")
    if not script.exists():
        raise RuntimeError(f"Windows OCR helper not found: {script}")
    cmd = [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Path", str(path)]
    if language:
        cmd += ["-Language", language]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=OCR_SUBPROCESS_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Windows OCR timed out after {OCR_SUBPROCESS_TIMEOUT_SECONDS} seconds.") from exc
    raw = proc.stdout.strip() or proc.stderr.strip()
    try:
        data = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"Windows OCR returned non-JSON output: {raw[:500]}") from exc
    if not data.get("ok"):
        raise RuntimeError(data.get("error") or "Windows OCR failed.")
    items: List[TextItem] = []
    for item in data.get("items", []) or []:
        text = item.get("text", "")
        if text and text.strip():
            items.append(TextItem(text=text.strip(), confidence=coerce_float(item.get("confidence")), source="windows_ocr", box=item.get("box")))
    return dedupe_items(items)


def run_tesseract(path: Path, lang: Optional[str] = None) -> List[TextItem]:
    if shutil.which("tesseract") is None:
        raise RuntimeError("tesseract command not found.")
    cmd = ["tesseract", str(path), "stdout", "tsv"]
    if lang:
        cmd = ["tesseract", str(path), "stdout", "-l", lang, "tsv"]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=OCR_SUBPROCESS_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"tesseract timed out after {OCR_SUBPROCESS_TIMEOUT_SECONDS} seconds.") from exc
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "tesseract failed.")
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0].split("\t")
    index = {name: i for i, name in enumerate(header)}
    items: List[TextItem] = []
    for ln in lines[1:]:
        cols = ln.split("\t")
        def get(name: str) -> Optional[str]:
            i = index.get(name)
            if i is None or i >= len(cols):
                return None
            return cols[i]
        text = (get("text") or "").strip()
        if not text:
            continue
        conf = coerce_float(get("conf"))
        conf = conf / 100.0 if conf is not None and conf >= 0 else None
        box = {"left": coerce_float(get("left")), "top": coerce_float(get("top")), "width": coerce_float(get("width")), "height": coerce_float(get("height"))}
        items.append(TextItem(text=text, confidence=conf, source="tesseract", box=box))
    return dedupe_items(items)


def extract_from_paddle_result(obj: Any) -> List[TextItem]:
    items: List[TextItem] = []
    def add(text: Any, score: Any = None, box: Any = None) -> None:
        if isinstance(text, str) and text.strip():
            items.append(TextItem(text=text.strip(), confidence=coerce_float(score), source="paddleocr", box=box))
    def walk(x: Any) -> None:
        if hasattr(x, "json") and callable(getattr(x, "json")):
            try:
                walk(x.json())
                return
            except Exception:
                pass
        if hasattr(x, "to_json") and callable(getattr(x, "to_json")):
            try:
                walk(x.to_json())
                return
            except Exception:
                pass
        if hasattr(x, "res"):
            try:
                walk(getattr(x, "res"))
                return
            except Exception:
                pass
        if isinstance(x, dict):
            raw = x.get("res", x)
            if isinstance(raw, dict) and "rec_texts" in raw:
                texts = raw.get("rec_texts") or []
                scores = raw.get("rec_scores") or []
                boxes = raw.get("rec_boxes") or raw.get("rec_polys") or raw.get("dt_polys") or []
                for i, text in enumerate(texts):
                    add(text, scores[i] if i < len(scores) else None, boxes[i] if i < len(boxes) else None)
                return
            if "text" in x:
                add(x.get("text"), x.get("confidence") or x.get("score"), x.get("box"))
            for value in x.values():
                walk(value)
            return
        if isinstance(x, (list, tuple)):
            if len(x) >= 2 and isinstance(x[1], (list, tuple)) and x[1] and isinstance(x[1][0], str):
                add(x[1][0], x[1][1] if len(x[1]) > 1 else None, x[0])
                return
            if len(x) >= 1 and isinstance(x[0], str):
                add(x[0], x[1] if len(x) > 1 else None, None)
                return
            for value in x:
                walk(value)
    walk(obj)
    return dedupe_items(items)


def make_paddleocr_instance():
    try:
        import paddleocr  # type: ignore
        from paddleocr import PaddleOCR  # type: ignore
    except Exception as exc:
        raise RuntimeError("PaddleOCR is not installed. Reinstall with: install script --with-paddleocr, or use native OCR on macOS/Windows.") from exc
    attempts = [
        lambda: PaddleOCR(use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False),
        lambda: PaddleOCR(use_angle_cls=False, lang="ch"),
        lambda: PaddleOCR(lang="ch"),
        lambda: PaddleOCR(),
    ]
    last_error: Optional[Exception] = None
    for attempt in attempts:
        try:
            return attempt()
        except Exception as exc:
            last_error = exc
    version = getattr(sys.modules.get("paddleocr"), "__version__", "unknown")
    raise RuntimeError(f"Could not initialize PaddleOCR: {last_error}\nPaddleOCR version: {version}. Try reinstalling with --with-paddleocr.")


def run_paddleocr(path: Path) -> List[TextItem]:
    ocr = make_paddleocr_instance()
    if hasattr(ocr, "predict"):
        try:
            result = ocr.predict(str(path))
        except TypeError:
            result = ocr.predict(input=str(path))
    elif hasattr(ocr, "ocr"):
        try:
            result = ocr.ocr(str(path), cls=False)
        except TypeError:
            result = ocr.ocr(str(path))
    else:
        raise RuntimeError("PaddleOCR instance has neither predict nor ocr method.")
    return extract_from_paddle_result(result)


def is_paddle_installed() -> bool:
    try:
        import paddleocr  # noqa: F401
        return True
    except Exception:
        return False


def available_backends() -> List[str]:
    names = ["svg", "metadata"]
    if platform.system() == "Darwin" and shutil.which("swift"):
        names.append("apple_vision")
    if platform.system() == "Windows" and (shutil.which("powershell") or shutil.which("pwsh")):
        names.append("windows_ocr")
    if is_paddle_installed():
        names.append("paddleocr")
    if shutil.which("tesseract"):
        names.append("tesseract")
    return names


def run_ocr_auto(path: Path, requested: str, tesseract_lang: Optional[str], windows_lang: Optional[str], vision_langs: Optional[str] = None) -> Tuple[List[TextItem], List[str], List[str]]:
    errors: List[str] = []
    if requested == "none":
        return [], [], ["OCR backend disabled by --ocr-backend none."]

    if requested == "auto":
        system = platform.system()
        if system == "Darwin":
            backend_order = ["apple_vision", "paddleocr", "tesseract"]
        elif system == "Windows":
            backend_order = ["windows_ocr", "paddleocr", "tesseract"]
        else:
            # Systems without native OCR default to PaddleOCR. Tesseract is a fallback if installed.
            backend_order = ["paddleocr", "tesseract"]
    elif requested == "native":
        system = platform.system()
        if system == "Darwin":
            backend_order = ["apple_vision"]
        elif system == "Windows":
            backend_order = ["windows_ocr"]
        else:
            backend_order = ["paddleocr"]
    else:
        backend_order = [requested]

    for backend in backend_order:
        try:
            if backend == "apple_vision":
                items = run_macos_vision(path, languages=vision_langs)
            elif backend == "windows_ocr":
                items = run_windows_ocr(path, language=windows_lang)
            elif backend == "tesseract":
                items = run_tesseract(path, lang=tesseract_lang)
            elif backend == "paddleocr":
                items = run_paddleocr(path)
            else:
                errors.append(f"Unknown OCR backend: {backend}")
                continue
            return items, [backend], errors
        except Exception as exc:
            errors.append(f"{backend}: {exc}")
            continue
    return [], [], errors


def build_context_text(packet: Dict[str, Any]) -> str:
    file_info = packet["file_info"]
    texts = packet["extracted_text"]
    lines: List[str] = []
    lines.append("This image has been converted into a text evidence packet for a text-only model.")
    lines.append("")
    lines.append("File information:")
    lines.append(f"- filename: {file_info.get('filename')}")
    lines.append(f"- format: {file_info.get('format') or file_info.get('extension')}")
    if file_info.get("width") and file_info.get("height"):
        lines.append(f"- size: {file_info.get('width')} x {file_info.get('height')}")
    lines.append(f"- file size: {file_info.get('file_size')}")
    if packet.get("extraction_methods"):
        human_names = {
            "apple_vision": "Apple Vision OCR (macOS native)",
            "windows_ocr": "Windows OCR (native)",
            "paddleocr": "PaddleOCR",
            "tesseract": "Tesseract OCR",
            "svg_xml_text_parse": "SVG text/XML parsing",
        }
        readable = [human_names.get(m, m) for m in packet["extraction_methods"]]
        lines.append(f"- extraction: {', '.join(readable)}")
    if texts:
        lines.append("")
        lines.append("Extracted text:")
        for item in texts:
            conf = item.get("confidence")
            if conf is None:
                lines.append(f"- {item.get('text')}")
            else:
                lines.append(f"- {item.get('text')} (confidence: {conf:.3f})")
    else:
        lines.append("")
        lines.append("Extracted text: none")
    if packet["confirmed_facts"]:
        lines.append("")
        lines.append("Confirmed facts:")
        for fact in packet["confirmed_facts"]:
            lines.append(f"- {fact}")
    if packet["uncertainties"]:
        lines.append("")
        lines.append("Limitations:")
        for u in packet["uncertainties"]:
            lines.append(f"- {u}")
    lines.append("")
    lines.append("Answering instruction: reason only from the extracted text and file information. Do not invent non-text visual details.")
    return "\n".join(lines)


def build_packet(path: Path, question: Optional[str], include_trace: bool, ocr_backend: str, tesseract_lang: Optional[str], windows_lang: Optional[str], vision_langs: Optional[str] = None) -> Dict[str, Any]:
    ext = path.suffix.lower()
    packet: Dict[str, Any] = {
        "tool": "textvision",
        "version": VERSION,
        "question": question,
        "file_info": read_file_info(path),
        "available_backends": available_backends(),
        "requested_ocr_backend": ocr_backend,
        "extraction_methods": [],
        "extracted_text": [],
        "confirmed_facts": [],
        "uncertainties": [],
        "context_for_text_model": "",
    }
    if ext not in SUPPORTED_EXTS:
        packet["uncertainties"].append(f"Unsupported image extension: {ext}")
        packet["context_for_text_model"] = build_context_text(packet)
        return packet
    try:
        if ext in SVG_EXTS:
            packet["extraction_methods"].append("svg_xml_text_parse")
            items = parse_svg_text(path)
            packet["extracted_text"] = [asdict(i) for i in items]
            if items:
                packet["confirmed_facts"].append("SVG text or accessibility attributes were extracted from the file.")
            else:
                packet["confirmed_facts"].append("SVG file was parsed, but no text elements were found.")
                packet["uncertainties"].append("SVG paths/shapes may contain visual meaning that is not represented as text.")
        else:
            items, methods, errors = run_ocr_auto(path, ocr_backend, tesseract_lang, windows_lang, vision_langs)
            packet["extraction_methods"].extend(methods)
            if errors:
                packet["backend_errors"] = errors
            packet["extracted_text"] = [asdict(i) for i in items]
            if items:
                packet["confirmed_facts"].append("OCR extracted visible text from the image.")
            else:
                packet["confirmed_facts"].append("Image file was processed, but OCR did not extract useful text.")
                packet["uncertainties"].append("Without OCR text or a vision model, internal visual content cannot be reliably determined.")
        packet["uncertainties"].append("This tool uses OCR/SVG text extraction, not full visual understanding. Non-text objects, scenes, emotions, and visual style may be missed.")
    except Exception as exc:
        packet["uncertainties"].append(f"Extraction failed: {exc}")
        if include_trace:
            packet["traceback"] = traceback.format_exc()
    packet["context_for_text_model"] = build_context_text(packet)
    return packet


def print_markdown(packet: Dict[str, Any]) -> None:
    print("# TextVision Evidence Packet")
    if packet.get("question"):
        print(f"\nUser question: {packet['question']}")
    print("\n## Context for text-only model\n")
    print(packet["context_for_text_model"])
    print("\n## Raw JSON\n")
    print("```json")
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    print("```")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert an image into OCR/text context for text-only models.")
    parser.add_argument("image_path", help="Path to an image file")
    parser.add_argument("--question", "-q", help="Optional user question/context")
    parser.add_argument("--json", action="store_true", help="Output raw JSON only")
    parser.add_argument("--trace", action="store_true", help="Include traceback on extraction failure")
    parser.add_argument("--ocr-backend", choices=["auto", "native", "apple_vision", "windows_ocr", "tesseract", "paddleocr", "none"], default="auto")
    parser.add_argument("--tesseract-lang", default=None, help="Optional Tesseract language, e.g. eng+chi_sim")
    parser.add_argument("--windows-lang", default=None, help="Optional Windows OCR language, e.g. en-US or zh-Hans")
    parser.add_argument("--vision-languages", default=None, help="Comma-separated Vision OCR languages, e.g. en-US,zh-Hans,ja-JP")
    args = parser.parse_args()
    path = Path(args.image_path).expanduser().resolve()
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    if not path.is_file():
        print(f"Not a file: {path}", file=sys.stderr)
        return 1
    packet = build_packet(path, args.question, args.trace, args.ocr_backend, args.tesseract_lang, args.windows_lang, args.vision_languages)
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        print_markdown(packet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
