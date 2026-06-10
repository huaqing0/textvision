#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="${IMAGE_CONTEXT_BRIDGE_APP_DIR:-$HOME/.image-context-bridge}"
BIN_DIR="${IMAGE_CONTEXT_BRIDGE_BIN_DIR:-$HOME/.local/bin}"
VENV_DIR="$APP_DIR/.venv"
WITH_PADDLE="auto"
TARGET="${IMAGE_CONTEXT_BRIDGE_TARGET:-none}"
CUSTOM_SKILL_DIR="${IMAGE_CONTEXT_BRIDGE_SKILL_DIR:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-paddleocr) WITH_PADDLE="yes" ;;
    --no-paddleocr) WITH_PADDLE="no" ;;
    --target)
      [[ $# -ge 2 ]] || { echo "Missing value for --target" >&2; exit 1; }
      TARGET="$2"
      shift
      ;;
    --target=*)
      TARGET="${1#*=}"
      ;;
    --app-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for --app-dir" >&2; exit 1; }
      APP_DIR="$2"
      shift
      ;;
    --app-dir=*)
      APP_DIR="${1#*=}"
      ;;
    --bin-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for --bin-dir" >&2; exit 1; }
      BIN_DIR="$2"
      shift
      ;;
    --bin-dir=*)
      BIN_DIR="${1#*=}"
      ;;
    --skill-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for --skill-dir" >&2; exit 1; }
      CUSTOM_SKILL_DIR="$2"
      TARGET="custom"
      shift
      ;;
    --skill-dir=*)
      CUSTOM_SKILL_DIR="${1#*=}"
      TARGET="custom"
      ;;
    -h|--help)
      echo "Usage: bash install.sh [options]"
      echo ""
      echo "Options:"
      echo "  --target none|claude|codex|agents|all"
      echo "      Skill target to install. Default: none (CLI/runtime only)"
      echo "  --app-dir DIR"
      echo "      Runtime install directory. Default: ~/.image-context-bridge"
      echo "  --bin-dir DIR"
      echo "      Command wrapper directory. Default: ~/.local/bin"
      echo "  --skill-dir DIR"
      echo "      Custom skill root. Installs DIR/image-context and overrides --target."
      echo "  --with-paddleocr"
      echo "      Install PaddleOCR backend."
      echo "  --no-paddleocr"
      echo "      Skip PaddleOCR backend."
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

case "$TARGET" in
  claude|codex|agents|all|none|custom) ;;
  *) echo "Unknown target: $TARGET. Use claude, codex, agents, all, or none." >&2; exit 1 ;;
esac

if [[ "$TARGET" == "custom" && -z "$CUSTOM_SKILL_DIR" ]]; then
  echo "Custom target requires --skill-dir." >&2
  exit 1
fi

VENV_DIR="$APP_DIR/.venv"

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
echo "Install target: $TARGET"
echo "App dir: $APP_DIR"
echo "Bin dir: $BIN_DIR"
if [[ -n "$CUSTOM_SKILL_DIR" ]]; then
  echo "Custom skill dir: $CUSTOM_SKILL_DIR"
fi

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

install_skill_root() {
  local skill_root="$1"
  mkdir -p "$skill_root/image-context"
  cp -R "$ROOT_DIR/skills/image-context/." "$skill_root/image-context/"
  echo "Skill: $skill_root/image-context"
}

case "$TARGET" in
  claude)
    install_skill_root "$HOME/.claude/skills"
    ;;
  codex)
    install_skill_root "$HOME/.codex/skills"
    ;;
  agents)
    install_skill_root "$HOME/.agents/skills"
    ;;
  all)
    install_skill_root "$HOME/.claude/skills"
    install_skill_root "$HOME/.codex/skills"
    install_skill_root "$HOME/.agents/skills"
    ;;
  custom)
    install_skill_root "$CUSTOM_SKILL_DIR"
    ;;
  none)
    echo "Skill: skipped (--target none)"
    ;;
esac

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
