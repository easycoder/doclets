#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_BASE="${EASYCODER_JS_DIR:-/home/graham/dev/easycoder/easycoder.github.io/js/easycoder}"

FILES=(
  Core.js
  MarkdownRenderer.js
  Browser.js
  Compare.js
  Compile.js
  Condition.js
  JSON.js
  MQTT.js
  REST.js
  Run.js
  Value.js
  Main.js
  EasyCoder.js
  Webson.js
)

if [[ ! -d "$TARGET_BASE" ]]; then
  echo "Target directory not found: $TARGET_BASE" >&2
  echo "Set EASYCODER_JS_DIR to your easycoder js directory and retry." >&2
  exit 1
fi

cd "$ROOT_DIR"
for file in "${FILES[@]}"; do
  target="$TARGET_BASE/$file"
  if [[ ! -e "$target" ]]; then
    echo "Missing target file: $target" >&2
    exit 1
  fi
  ln -sfn "$target" "$file"
  echo "linked $file -> $target"
done

echo "Done: EasyCoder script symlinks refreshed."
