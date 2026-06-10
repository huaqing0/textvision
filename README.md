# Image Context Bridge

[中文](README.zh-CN.md)

Image Context Bridge is a small local workflow for text-only or image-unsupported AI models. It converts an image file into a structured text evidence packet, then asks the model to reason only from extracted text, metadata, and stated limitations.

It is useful when you want to use models such as DeepSeek, local LLMs, or other text-only agents on screenshots, error dialogs, SVGs, and image files without asking the model to invent visual details it cannot actually see.

## What It Includes

- `image2context`: a CLI that reads an image path and outputs Markdown or JSON evidence.
- `auto-image-fallback`: a hook helper that uses caller-provided model capability or image-input failure errors to decide whether to pass an image through or replace it with text context.
- `skills/image-context`: a Skill wrapper for agents such as Claude Code, Codex, and other skill-aware tools.

The Skill is only a workflow wrapper. The actual extraction is done by the local `image2context` command.

## How It Works

1. You provide a local image path, or an agent detects one in a message.
2. If the agent already knows the model can handle images, the image can be passed through directly.
3. If the model is text-only, image input is unavailable, or image input fails, `image2context` extracts OCR/SVG text locally.
4. The output packet includes file metadata, extracted text, confidence values when available, confirmed facts, limitations, and an instruction not to invent non-text visual details.

Image Context Bridge does not actively probe every model to discover whether it has vision. Automatic fallback depends on the agent or hook providing `model_supports_images`, or on a previous image-input error such as "image input not supported".

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

If you use a separate agent that first sends the original image to a cloud model, that behavior is controlled by that agent, not by Image Context Bridge. To avoid that, call `image2context` directly or configure your agent to use the fallback workflow first.

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

Recommended one-line install, no manual clone required.

By default, the installer is agent-neutral: it installs only the local runtime and CLI commands. It does not write into Claude Code, Codex, or other agent skill directories unless you choose a target.

macOS or Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.sh | bash
```

Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.ps1 | iex"
```

Install a Skill wrapper for a specific agent:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.sh | bash -s -- --target claude
curl -fsSL https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.sh | bash -s -- --target codex
curl -fsSL https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.sh | bash -s -- --target agents
```

Install all known Skill targets only if you explicitly want that:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.sh | bash -s -- --target all
```

Windows PowerShell target selection example:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command '$env:IMAGE_CONTEXT_BRIDGE_TARGET="claude"; irm https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.ps1 | iex'
```

Choose install paths:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.sh | bash -s -- --app-dir "$HOME/Tools/image-context-bridge" --bin-dir "$HOME/bin"
```

Use a custom Skill root. The installer creates `<skill-root>/image-context`:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.sh | bash -s -- --skill-dir "$HOME/.claude/skills"
```

Optional PaddleOCR install:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.sh | bash -s -- --with-paddleocr
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command '$env:IMAGE_CONTEXT_BRIDGE_WITH_PADDLEOCR="1"; irm https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.ps1 | iex'
```

Skip PaddleOCR on Linux if you only want metadata/SVG extraction or another manually installed backend:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.sh | bash -s -- --no-paddleocr
```

Manual clone install is also supported:

```bash
git clone https://github.com/huaqing0/image-context-bridge.git
cd image-context-bridge
bash install.sh
```

```powershell
git clone https://github.com/huaqing0/image-context-bridge.git
cd image-context-bridge
.\install.ps1
```

The installer creates:

- `~/.image-context-bridge/` for the local app files and Python virtual environment.
- `~/.image-context-bridge/testdata/sample.svg` for post-install verification.
- `~/.local/bin/image2context`
- `~/.local/bin/auto-image-fallback`

If you pass `--target claude`, `--target codex`, `--target agents`, or `--target all`, it also creates the selected `<skill-root>/image-context` directory.

Make sure `~/.local/bin` is in your `PATH`. Restart Claude Code, Codex, or your agent app after installation so it can reload the Skill.

## Post-Install Check

This section is not the normal daily workflow. It only verifies that the install works by using the sample SVG copied into `~/.image-context-bridge/testdata/`.

Step 1: check that the `image2context` command works:

```bash
image2context ~/.image-context-bridge/testdata/sample.svg --json
```

If the output contains the two lines below, the CLI can read the image and extract text:

```text
WebSocket handshake timeout
Reconnecting...
```

Step 2: check that the fallback hook works:

```bash
echo '{"message":"Please analyze ~/.image-context-bridge/testdata/sample.svg","model_supports_images":false}' | auto-image-fallback
```

This simulates a model that does not support images. If `action` is `replace_with_context`, the hook is replacing the image with a text evidence packet:

```json
{"action":"replace_with_context","contexts":["..."]}
```

## Manual CLI Usage

`CLI` means terminal command. Most users do not need to call it manually if Claude Code, Codex, or another agent already triggers the `image-context` Skill.

Use the CLI manually when:

- your agent does not trigger the Skill automatically.
- you want to convert an image into text first, then paste the result into DeepSeek or another text-only model.

Replace `screenshot.png` with the real path to your image.

```bash
# Most common: convert an image into a Markdown evidence packet
image2context screenshot.png

# Include your specific question in the packet
image2context error.png --question "Why did the build fail?"

# Output JSON for scripts or hooks
image2context screenshot.png --json
```

The most important field is `context_for_text_model`. If you are using DeepSeek manually, copy that text into the model.

### Advanced CLI Options

Most users can skip this section. These options are useful only when the default OCR backend is not good enough or when debugging backend behavior.

```bash
# Disable OCR and return only file information and limitations
image2context screenshot.png --ocr-backend none

# Force an OCR backend
image2context screenshot.png --ocr-backend native
image2context screenshot.png --ocr-backend apple_vision
image2context screenshot.png --ocr-backend windows_ocr
image2context screenshot.png --ocr-backend paddleocr
image2context screenshot.png --ocr-backend tesseract
```

Language hints are also advanced options:

```bash
image2context screenshot.png --vision-languages en-US,zh-Hans,ja-JP
image2context screenshot.png --windows-lang zh-Hans
image2context screenshot.png --tesseract-lang eng+chi_sim
```

## Skill Usage

After installation, skill-aware agents can load `image-context`.

The generic install command does not install an agent Skill by default. To install the Claude Code wrapper, run:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/image-context-bridge/main/install-remote.sh | bash -s -- --target claude
```

Automatic triggering is best-effort. The Skill can be invoked implicitly when an agent sees a local image path and the model is known to be text-only or image input has failed. If the model's image capability is unknown and the agent can send images directly, the intended flow is to try direct image input first, then fallback to `image2context` only if direct input fails.

For Claude Code or similar agents, use a prompt like:

```text
Use image-context to process ./testdata/sample.svg, then tell me what error text it contains.
```

For DeepSeek or another text-only model inside an agent, the useful behavior is:

1. The agent sees an image path.
2. The `image-context` Skill tells it to run `image2context <image_path>`.
3. The agent answers from `context_for_text_model`, not from imagined visual details.

If the agent does not trigger the Skill automatically, run the CLI yourself and paste the output into the model.

Current trigger boundaries:

- Works best with local image paths or uploaded files that the agent exposes as local paths.
- Does not download remote image URLs by itself.
- Does not run for metadata-only requests.
- Does not force agents to use the Skill; the host agent must support Skills and implicit invocation.

## Hook Usage

`auto-image-fallback` reads JSON from stdin and returns a JSON action. It does not probe the model by itself; it follows `model_supports_images` or `last_error`.

Known image support:

```bash
echo '{"message":"Check ./error.png","model_supports_images":false}' | auto-image-fallback
```

Unknown image support:

```bash
echo '{"message":"Check ./error.png","model_supports_images":null}' | auto-image-fallback
```

When support is unknown, the hook returns `try_direct_first`. Call it again with `last_error` if direct image input fails:

```bash
echo '{"message":"Check ./error.png","model_supports_images":null,"last_error":"image input not supported"}' | auto-image-fallback
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

`image2context: command not found`

Add `~/.local/bin` to your `PATH`, then restart your shell or agent app.

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Skill does not trigger in Claude Code/Codex

- Restart the agent app after installation.
- Confirm the Skill files exist under `~/.claude/skills/image-context/` or `~/.codex/skills/image-context/`.
- Ask explicitly: `Use image-context to process <image_path>`.

OCR returns no text

- Try a clearer image or crop around the text.
- Try PaddleOCR: `bash install.sh --with-paddleocr`, then `image2context image.png --ocr-backend paddleocr`.
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
python -m py_compile scripts/image2context.py hooks/auto_image_fallback.py
```

Run a local smoke test:

```bash
python scripts/image2context.py testdata/sample.svg --json
```

## License

MIT
