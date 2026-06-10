---
name: textvision
description: Use this skill when a local image path or image file must be handled by a text-only model, an image-unsupported model, or after image input fails.
---

# TextVision

Use this skill when the current model cannot directly process images, or when image input fails. The skill does not probe model capability by itself; it provides the fallback workflow.

## Trigger rules

Use this skill when:
- The user provides a local image path or image file, and the current model cannot process images.
- The target model cannot process images.
- Image input fails with an unsupported-image/media error.
- The model's image capability is unknown and the image cannot be passed directly.
- The user wants to use a text-only model such as DeepSeek on image content.

Do not use this skill when:
- The active model clearly supports native image understanding and successfully received the image.
- The user only asks for image file metadata.
- The user provided only a remote URL and no local image file is available.

If image capability is unknown and direct image input is available, try direct image input first. Use this skill only if direct input is unavailable or fails with an image/media unsupported error.

## Required action

Before answering image-related questions for a text-only model, run:

```bash
textvision <image_path>
```

If the user asked a specific question about the image, include it:

```bash
textvision <image_path> --question "<user question>"
```

If no local image path is available, explain that `textvision` needs a local file path before it can extract evidence.

## OCR backend policy

`textvision` chooses the OCR backend automatically:

- macOS: Apple Vision OCR by default.
- Windows: Windows native OCR by default.
- Linux or systems without native OCR: PaddleOCR by default when installed by the installer.
- PaddleOCR can also be installed as an optional high-accuracy backend on macOS/Windows.
- SVG files are parsed directly as XML/text without OCR.

## Answering rules

- Do not guess image contents.
- Use extracted text and file information as evidence.
- Clearly separate:
  - confirmed OCR/text information
  - reasonable inference
  - unknown or unconfirmed visual details
- If OCR extracts little or no text, say the image was processed but cannot be reliably understood by OCR alone.
- Do not invent non-text visual details.

## Expected tool output

The `textvision` tool returns:
- file information
- extraction backend used
- extracted text
- confidence/box data when available
- confirmed facts
- uncertainties
- context for text-only models

Use `context_for_text_model` as the main source.
