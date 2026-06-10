# Install Options

The README keeps common install commands. This file lists additional install options.

## Windows

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.ps1 | iex"
```

Install the Skill wrapper for Claude Code on Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command '$env:TEXTVISION_TARGET="claude"; irm https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.ps1 | iex'
```

## Other Skill Targets

Install into the generic agents Skill directory:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --target agents
```

Install all known Skill targets:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --target all
```

## Custom Paths

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --app-dir "$HOME/Tools/textvision" --bin-dir "$HOME/bin"
```

Use a custom Skill root. The installer creates `<skill-root>/textvision`:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --skill-dir "$HOME/.claude/skills"
```

## PaddleOCR

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --with-paddleocr
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command '$env:TEXTVISION_WITH_PADDLEOCR="1"; irm https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.ps1 | iex'
```

Skip PaddleOCR on Linux for metadata/SVG extraction only, or when managing the OCR backend separately:

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --no-paddleocr
```

## Manual Clone

```bash
git clone https://github.com/huaqing0/textvision.git
cd textvision
bash install.sh
```

```powershell
git clone https://github.com/huaqing0/textvision.git
cd textvision
.\install.ps1
```

## Hook Check

This simulates a model that does not support images. If `action` is `replace_with_context`, the hook is replacing the image with a text evidence packet:

```bash
echo '{"message":"Please analyze ~/.textvision/testdata/sample.svg","model_supports_images":false}' | textvision-fallback
```

```json
{"action":"replace_with_context","contexts":["..."]}
```
