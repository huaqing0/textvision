import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "textvision.py"
HOOK = ROOT / "hooks" / "textvision_fallback.py"
SAMPLE_SVG = ROOT / "testdata" / "sample.svg"


def _run(*args: str) -> dict:
    out = subprocess.check_output([sys.executable, str(SCRIPT), *args], text=True)
    return json.loads(out)


def _run_hook(payload: dict, cwd=None, env=None) -> dict:
    out = subprocess.check_output(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        cwd=str(cwd or ROOT),
        env=env,
        text=True,
    )
    return json.loads(out)


class TestSVGExtraction:
    def test_extracts_text(self):
        data = _run(str(SAMPLE_SVG), "--json")
        texts = "\n".join(item["text"] for item in data["extracted_text"])
        assert "WebSocket handshake timeout" in texts
        assert "Reconnecting" in texts

    def test_uses_svg_backend(self):
        data = _run(str(SAMPLE_SVG), "--json")
        assert data["extraction_methods"] == ["svg_xml_text_parse"]

    def test_has_file_info(self):
        data = _run(str(SAMPLE_SVG), "--json")
        assert data["file_info"]["format"] == "SVG"
        assert data["file_info"]["width"] == "400"
        assert data["file_info"]["height"] == "120"

    def test_has_required_packet_keys(self):
        data = _run(str(SAMPLE_SVG), "--json")
        for key in ("tool", "version", "file_info", "extraction_methods",
                     "extracted_text", "confirmed_facts", "uncertainties",
                     "context_for_text_model"):
            assert key in data, f"missing key: {key}"

    def test_uncertainties_non_empty(self):
        data = _run(str(SAMPLE_SVG), "--json")
        assert len(data["uncertainties"]) >= 1

    def test_context_text_not_empty(self):
        data = _run(str(SAMPLE_SVG), "--json")
        assert len(data["context_for_text_model"]) > 200
        assert "WebSocket handshake timeout" in data["context_for_text_model"]


class TestCLI:
    def test_json_flag(self):
        out = subprocess.check_output([sys.executable, str(SCRIPT), str(SAMPLE_SVG), "--json"], text=True)
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_file_not_found(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), "/nonexistent.png"], capture_output=True, text=True)
        assert proc.returncode != 0

    def test_question_flag(self):
        data = _run(str(SAMPLE_SVG), "--json", "--question", "What is the error?")
        assert data["question"] == "What is the error?"

    def test_bad_raster_returns_packet(self, tmp_path):
        bad_png = tmp_path / "bad.png"
        bad_png.write_bytes(b"not really a png")
        data = _run(str(bad_png), "--json")
        assert data["file_info"]["filename"] == "bad.png"
        assert "image_parse_warning" in data["file_info"]
        assert data["extracted_text"] == []
        assert data["backend_errors"]
        assert "cannot be reliably determined" in data["context_for_text_model"]


class TestBackendSelection:
    def test_none_backend_skips_ocr_on_raster(self):
        # SVG text extraction is not OCR, so --ocr-backend none doesn't affect SVGs.
        # For SVGs, text is still extracted via XML parsing regardless.
        data = _run(str(SAMPLE_SVG), "--json", "--ocr-backend", "none")
        assert data["extraction_methods"] == ["svg_xml_text_parse"]

    def test_unknown_backend_reported(self):
        data = _run(str(SAMPLE_SVG), "--json", "--ocr-backend", "tesseract")
        assert data["requested_ocr_backend"] == "tesseract"

    def test_available_backends_in_packet(self):
        data = _run(str(SAMPLE_SVG), "--json")
        assert "available_backends" in data
        assert "svg" in data["available_backends"]
        assert "metadata" in data["available_backends"]


class TestFallbackHook:
    def test_bare_filename_is_detected(self):
        data = _run_hook(
            {"model_supports_images": None, "message": "Please analyze sample.svg"},
            cwd=SAMPLE_SVG.parent,
        )
        assert data["action"] == "try_direct_first"
        assert data["image_paths"] == [str(SAMPLE_SVG.resolve())]

    def test_unquoted_path_with_spaces_is_detected(self, tmp_path):
        image_path = tmp_path / "sample space.svg"
        shutil.copyfile(SAMPLE_SVG, image_path)
        data = _run_hook({"model_supports_images": None, "message": f"Please analyze {image_path}"})
        assert data["action"] == "try_direct_first"
        assert data["image_paths"] == [str(image_path.resolve())]

    def test_missing_textvision_is_structured(self):
        env = os.environ.copy()
        env["PATH"] = "/usr/bin:/bin"
        data = _run_hook(
            {"model_supports_images": False, "message": "Please analyze ./sample.svg"},
            cwd=SAMPLE_SVG.parent,
            env=env,
        )
        assert data["action"] == "replace_with_context"
        assert "textvision command not found" in data["contexts"][0]

    def test_string_image_support_flag_is_normalized(self):
        data = _run_hook(
            {"model_supports_images": "true", "message": "Please analyze sample.svg"},
            cwd=SAMPLE_SVG.parent,
        )
        assert data["action"] == "pass_through"

    def test_chinese_image_error_triggers_fallback(self):
        data = _run_hook(
            {
                "model_supports_images": None,
                "message": "Please analyze sample.svg",
                "last_error": "当前模型不支持图片输入",
            },
            cwd=SAMPLE_SVG.parent,
        )
        assert data["action"] == "replace_with_context"
        assert data["contexts"]

    def test_invalid_json_is_structured(self):
        out = subprocess.check_output([sys.executable, str(HOOK)], input="{", text=True)
        data = json.loads(out)
        assert data["action"] == "error"
