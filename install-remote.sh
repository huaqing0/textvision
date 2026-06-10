#!/usr/bin/env bash
set -euo pipefail

REPO="${TEXTVISION_REPO:-huaqing0/textvision}"
REF="${TEXTVISION_REF:-main}"
URL="${TEXTVISION_TARBALL_URL:-https://codeload.github.com/${REPO}/tar.gz/${REF}}"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/textvision.XXXXXX")"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

download() {
  local url="$1"
  local output="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$output"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$output" "$url"
  elif command -v python3 >/dev/null 2>&1; then
    python3 - "$url" "$output" <<'PY'
import sys
import urllib.request

url, output = sys.argv[1], sys.argv[2]
with urllib.request.urlopen(url) as response:
    data = response.read()
with open(output, "wb") as f:
    f.write(data)
PY
  else
    echo "Error: curl, wget, or python3 is required to download TextVision." >&2
    exit 1
  fi
}

echo "Downloading TextVision from ${REPO}@${REF}..."
ARCHIVE="$TMP_DIR/source.tar.gz"
download "$URL" "$ARCHIVE"
tar -xzf "$ARCHIVE" -C "$TMP_DIR"

SOURCE_DIR="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
if [[ -z "$SOURCE_DIR" || ! -f "$SOURCE_DIR/install.sh" ]]; then
  echo "Error: downloaded archive did not contain install.sh." >&2
  exit 1
fi

bash "$SOURCE_DIR/install.sh" "$@"
