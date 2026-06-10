# Changelog

## v0.4.0

- Renamed the project to TextVision.
- Unified the CLI, hook helper, Skill name, install paths, and environment variables around `textvision`.
- Added a Codex plugin manifest.

## v0.3.0

- Default OCR policy changed:
  - macOS uses Apple Vision OCR by default.
  - Windows uses Windows native OCR by default.
  - Linux defaults to PaddleOCR because there is no built-in OS OCR.
- PaddleOCR remains optional on macOS/Windows via install flags.
- Added Windows OCR PowerShell helper.
- Kept SVG direct parsing and metadata fallback.
- Kept auto image fallback helper.

## v0.2.0

- Moved PaddleOCR out of default dependency on macOS.
- Added Apple Vision OCR backend.

## v0.1.0

- Initial PaddleOCR-based evidence packet prototype.
