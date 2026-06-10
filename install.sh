#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HOME/.image-context-bridge"
BIN_DIR="$HOME/.local/bin"
VENV_DIR="$APP_DIR/.venv"
WITH_PADDLE="auto"

for arg in "$@"; do
  case "$arg" in
    --with-paddleocr) WITH_PADDLE="yes" ;;
    --no-paddleocr) WITH_PADDLE="no" ;;
    -h|--help)
      echo "Usage: bash install.sh [--with-paddleocr|--no-paddleocr]"
      echo "Default: macOS uses Apple Vision; Linux installs PaddleOCR; Windows use install.ps1."
      exit 0
      ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

OS="$(uname -s)"
if [[ "$WITH_PADDLE" == "auto" ]]; then
  if [[ "$OS" == "Linux" ]]; then
    INSTALL_PADDLE="yes"
  else
    INSTALL_PADDLE="no"
  fi
else
  INSTALL_PADDLE="$WITH_PADDLE"
fi

echo "Installing Image Context Bridge..."
echo "OS: $OS"
echo "Install PaddleOCR: $INSTALL_PADDLE"

mkdir -p "$APP_DIR/scripts" "$APP_DIR/hooks" "$APP_DIR/skills/image-context" "$APP_DIR/testdata" "$BIN_DIR"
cp -r "$ROOT_DIR/scripts/"* "$APP_DIR/scripts/"
cp "$ROOT_DIR/hooks/auto_image_fallback.py" "$APP_DIR/hooks/auto_image_fallback.py"
cp "$ROOT_DIR/requirements.txt" "$APP_DIR/requirements.txt"
cp "$ROOT_DIR/requirements-paddleocr.txt" "$APP_DIR/requirements-paddleocr.txt"
cp -R "$ROOT_DIR/skills/image-context/." "$APP_DIR/skills/image-context/"
cp "$ROOT_DIR/testdata/sample.svg" "$APP_DIR/testdata/sample.svg"

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

if [[ "$INSTALL_PADDLE" == "yes" ]]; then
  echo "Installing PaddleOCR backend. This may take a while..."
  "$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements-paddleocr.txt"
fi

cat > "$BIN_DIR/image2context" <<EOF
#!/usr/bin/env bash
"$VENV_DIR/bin/python" "$APP_DIR/scripts/image2context.py" "\$@"
EOF
chmod +x "$BIN_DIR/image2context"

cat > "$BIN_DIR/auto-image-fallback" <<EOF
#!/usr/bin/env bash
"$VENV_DIR/bin/python" "$APP_DIR/hooks/auto_image_fallback.py" "\$@"
EOF
chmod +x "$BIN_DIR/auto-image-fallback"

# Install skill for common agent locations.
mkdir -p "$HOME/.agents/skills/image-context"
cp -R "$ROOT_DIR/skills/image-context/." "$HOME/.agents/skills/image-context/"

mkdir -p "$HOME/.claude/skills/image-context"
cp -R "$ROOT_DIR/skills/image-context/." "$HOME/.claude/skills/image-context/"

mkdir -p "$HOME/.codex/skills/image-context"
cp -R "$ROOT_DIR/skills/image-context/." "$HOME/.codex/skills/image-context/"

# Syntax check.
"$VENV_DIR/bin/python" -m py_compile "$APP_DIR/scripts/image2context.py" "$APP_DIR/hooks/auto_image_fallback.py"

echo ""
echo "Installed Image Context Bridge."
echo "Command: $BIN_DIR/image2context"
echo "Hook helper: $BIN_DIR/auto-image-fallback"
echo ""
echo "Backend policy:"
echo "- macOS: Apple Vision OCR by default"
echo "- Linux: PaddleOCR by default unless --no-paddleocr was used"
echo "- SVG: direct text/XML parsing"
echo ""
echo "Make sure ~/.local/bin is in your PATH. Test with:"
echo "  image2context ~/.image-context-bridge/testdata/sample.svg --json"
