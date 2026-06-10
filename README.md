# TextVision

[中文](README.zh-CN.md)

TextVision is a local plugin for text-only or image-unsupported AI models. It converts an image file into a structured text evidence packet, then asks the model to reason only from extracted text, metadata, and stated limitations.

It is useful for using models such as DeepSeek, local LLMs, or other text-only agents on screenshots, error dialogs, SVGs, and image files without asking the model to invent visual details it cannot actually see.

## What It Includes

- `textvision`: a CLI that reads an image path and outputs Markdown or JSON evidence.
- `textvision-fallback`: a hook helper that uses caller-provided model capability or image-input failure errors to decide whether to pass an image through or replace it with text context.
- `skills/textvision`: a Skill wrapper for agents such as Claude Code, Codex, and other skill-aware tools.
- `.codex-plugin/plugin.json`: a Codex plugin manifest.

The local CLI provides the core extraction capability. The Skill and plugin manifest connect that capability to agent workflows.

## How It Works

1. You provide a local image path, or an agent detects one in a message.
2. If the agent already knows the model can handle images, the image can be passed through directly.
3. If the model is text-only, image input is unavailable, or image input fails, `textvision` extracts OCR/SVG text locally.
4. The output packet includes file metadata, extracted text, confidence values when available, confirmed facts, limitations, and an instruction not to invent non-text visual details.

TextVision does not actively probe every model to discover whether it has vision. Automatic fallback depends on the agent or hook providing `model_supports_images`, or on a previous image-input error such as "image input not supported".

Example:

```text
Input image:
  A screenshot showing "Error: connection refused on port 3000"

Evidence packet:
  - extracted text: "Error: connection refused on port 3000"
  - filename, format, size, dimensions
  - confirmed facts
  - limitations and answering instruction

Result:
  A text-only model can reason from the error text without pretending it saw the image.
```

## Privacy

OCR runs locally. This project does not upload image files, call a cloud OCR API, require an API key, or use a quota.

A separate agent may send the original image to a cloud model before this workflow runs. That behavior is controlled by the agent, not by TextVision. To avoid it, call `textvision` directly or configure the agent to use the fallback workflow first.

## Supported Inputs

Raster images:

- `.png`
- `.jpg` / `.jpeg`
- `.webp`
- `.bmp`
- `.tiff` / `.tif`
- `.gif`

Vector/text images:

- `.svg` files are parsed directly as XML/text without OCR.

## OCR Backends

| Platform | Default backend | Notes |
| --- | --- | --- |
| macOS | Apple Vision OCR | Uses the built-in Vision framework through Swift. |
| Windows | Windows OCR | Uses the built-in Windows OCR APIs through PowerShell. |
| Linux | PaddleOCR | Installed by the Linux installer path because there is no built-in OS OCR. |
| Any platform | Tesseract | Used as a fallback if installed and selected/available. |
| Any platform | PaddleOCR | Optional high-accuracy backend. |

SVG text extraction is handled separately and does not use an OCR backend.

## Install

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash
```

Default install:

- Runtime: `~/.textvision/`
- CLI: `~/.local/bin/textvision`
- Hook helper: `~/.local/bin/textvision-fallback`

No agent Skill is installed by default.

Install the Claude Code Skill:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --target claude
```

Install the Codex Skill:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --target codex
```

Restart the target agent app after installation.

## Quick Check

Run the sample SVG through the CLI:

```bash
textvision ~/.textvision/testdata/sample.svg --json
```

If the output contains the two lines below, the CLI is installed and can extract text:

```text
WebSocket handshake timeout
Reconnecting...
```

For Windows, custom paths, PaddleOCR, or manual clone installation, see [INSTALL.md](INSTALL.md).

## Manual CLI Usage

`CLI` means terminal command. When Claude Code, Codex, or another agent already triggers the `textvision` Skill, no manual CLI call is required.

Use the CLI for:

- agents that do not trigger the Skill automatically.
- converting an image into text before pasting it into DeepSeek or another text-only model.

Replace `screenshot.png` with the real image path.

```bash
# Most common: convert an image into a Markdown evidence packet
textvision screenshot.png

# Include a specific question in the packet
textvision error.png --question "Why did the build fail?"

# Output JSON for scripts or hooks
textvision screenshot.png --json
```

The most important field is `context_for_text_model`. For manual DeepSeek use, copy that text into the model.

### Advanced CLI Options

Use these options when the default OCR backend is not good enough or when debugging backend behavior.

```bash
# Disable OCR and return only file information and limitations
textvision screenshot.png --ocr-backend none

# Force an OCR backend
textvision screenshot.png --ocr-backend native
textvision screenshot.png --ocr-backend apple_vision
textvision screenshot.png --ocr-backend windows_ocr
textvision screenshot.png --ocr-backend paddleocr
textvision screenshot.png --ocr-backend tesseract
```

Language hints are also advanced options:

```bash
textvision screenshot.png --vision-languages en-US,zh-Hans,ja-JP
textvision screenshot.png --windows-lang zh-Hans
textvision screenshot.png --tesseract-lang eng+chi_sim
```

## Skill Usage

After installation with `--target claude`, `--target codex`, or another Skill target, skill-aware agents can load `textvision`.

Automatic triggering is best-effort. The Skill can be invoked implicitly when an agent sees a local image path and the model is known to be text-only or image input has failed. If the model's image capability is unknown and the agent can send images directly, the intended flow is to try direct image input first, then fallback to `textvision` only if direct input fails.

For Claude Code or similar agents, use a prompt like:

```text
Use textvision to process ./testdata/sample.svg, then tell me what error text it contains.
```

For DeepSeek or another text-only model inside an agent, the useful behavior is:

1. The agent sees an image path.
2. The `textvision` Skill tells it to run `textvision <image_path>`.
3. The agent answers from `context_for_text_model`, not from imagined visual details.

When the agent does not trigger the Skill automatically, run the CLI and paste the output into the model.

Current trigger boundaries:

- Works best with local image paths or uploaded files that the agent exposes as local paths.
- Does not download remote image URLs by itself.
- Does not run for metadata-only requests.
- Does not force agents to use the Skill; the host agent must support Skills and implicit invocation.

## Hook Usage

`textvision-fallback` reads JSON from stdin and returns a JSON action. It does not probe the model by itself; it follows `model_supports_images` or `last_error`.

Known unsupported image input:

```bash
echo '{"message":"Check ./error.png","model_supports_images":false}' | textvision-fallback
```

Unknown image support:

```bash
echo '{"message":"Check ./error.png","model_supports_images":null}' | textvision-fallback
```

When support is unknown, the hook returns `try_direct_first`. Call it again with `last_error` if direct image input fails:

```bash
echo '{"message":"Check ./error.png","model_supports_images":null,"last_error":"image input not supported"}' | textvision-fallback
```

The hook recognizes common English and Chinese image-unsupported errors, such as "image input not supported" and "不支持图片输入".

## Output Shape

JSON output contains:

- `file_info`: path, filename, extension, size, modified time, dimensions when available.
- `available_backends`: detected extraction backends.
- `requested_ocr_backend`: selected backend policy.
- `extraction_methods`: methods actually used.
- `extracted_text`: text items with source, confidence, and box when available.
- `confirmed_facts`: facts supported by extraction.
- `uncertainties`: limitations and things OCR cannot determine.
- `context_for_text_model`: the main text block to give to a text-only model.
- `backend_errors`: backend failures, if fallback attempts failed.

## Limitations

- This is OCR and SVG text extraction, not full visual understanding.
- Non-text objects, layout meaning, charts, handwriting, UI state, colors, emotion, and visual style may be missed.
- OCR accuracy depends on image quality, language support, fonts, orientation, and backend.
- The Skill wrapper does not force every agent to use the workflow. Some tools require a restart or explicit prompt.
- Automatic fallback depends on model capability metadata or a recognizable image-input error; it is not universal model capability detection.
- On Windows, native OCR availability depends on installed language packs and Windows OCR support.

## Troubleshooting

`textvision: command not found`

Add `~/.local/bin` to `PATH`, then restart the shell or agent app.

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Skill does not trigger in Claude Code/Codex

- Restart the agent app after installation.
- Confirm the Skill files exist under `~/.claude/skills/textvision/` or `~/.codex/skills/textvision/`.
- Ask explicitly: `Use textvision to process <image_path>`.

OCR returns no text

- Try a clearer image or crop around the text.
- Try PaddleOCR: `bash install.sh --with-paddleocr`, then `textvision image.png --ocr-backend paddleocr`.
- For SVGs, make sure the text is real SVG text, not converted outlines.

macOS says Swift is missing

Install Xcode Command Line Tools:

```bash
xcode-select --install
```

Windows OCR fails

- Run PowerShell as a normal user, not from a restricted environment.
- Check that Windows OCR and the relevant language pack are available.
- Try `.\install.ps1 -WithPaddleOCR` and then force PaddleOCR.

## Development

Install development dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Run tests:

```bash
python -m pytest -q
python -m py_compile scripts/textvision.py hooks/textvision_fallback.py
```

Run a local smoke test:

```bash
python scripts/textvision.py testdata/sample.svg --json
```

## License

MIT
