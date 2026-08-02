#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_BASE="${ALLSPEAK_JS_DIR:-/home/graham/dev/allspeak/js/allspeak}"

FILES=(
  config.js
  Core.js
  Browser.js
  MarkdownRenderer.js
  Webson.js
  JSON.js
  MQTT.js
  REST.js
  Compare.js
  Condition.js
  Value.js
  Run.js
  Opcodes.js
  Language.js
  LanguagePack_en.js
  Compile.js
  Main.js
  AllSpeak.js
)

if [[ ! -d "$TARGET_BASE" ]]; then
  echo "Target directory not found: $TARGET_BASE" >&2
  echo "Set ALLSPEAK_JS_DIR to your allspeak js directory and retry." >&2
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

echo "Done: AllSpeak script symlinks refreshed."
