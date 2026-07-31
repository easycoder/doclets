#!/usr/bin/env bash
set -euo pipefail

# deploy.sh — deploy the AllSpeak doclets client to the doclets.eclecity.net web root.
#
# The new client needs exactly three files served by the web server:
#   index.html    – the page + loader (loads the AllSpeak CDN bundle)
#   doclets.as    – the client script (fetched by the loader)
#   doclets.json  – Webson screen layout
#
# This script copies only; it never deletes. Leftover .ecs files on the site
# (doclets.ecs, scripted.*, ...) are no longer used — remove them by hand once
# the new client is confirmed working.
#
# Optional --infra also copies the supporting files that should already be in
# place on the site: credentials.php, .htaccess, mqtt_token.php, favicon.ico.
#
# doclets.eclecity.net.txt is intentionally NOT deployed: credentials.php reads
# it from one level ABOVE the web root, and the live copy is already correct.
#
# Usage:
#   ./deploy.sh /path/to/web/root          # client files only
#   ./deploy.sh --infra /path/to/web/root  # client + supporting files
#   DOCLETS_DEPLOY_DIR=/path ./deploy.sh   # target from environment
#   ./deploy.sh -h                          # show this help

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

INFRA=0
case "${1:-}" in
  -h|--help|help)
    sed -n '2,35p' "$0"
    exit 0
    ;;
  --infra)
    INFRA=1
    shift
    ;;
esac

TARGET="${1:-${DOCLETS_DEPLOY_DIR:-}}"
if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 [--infra] TARGET_DIR   (or set DOCLETS_DEPLOY_DIR)" >&2
  exit 2
fi
if [[ ! -d "$TARGET" ]]; then
  echo "error: target directory not found: $TARGET" >&2
  exit 2
fi

CLIENT_FILES=(index.html doclets.as doclets.json)
INFRA_FILES=(credentials.php .htaccess mqtt_token.php favicon.ico)

echo "Deploying doclets client to $TARGET"
for f in "${CLIENT_FILES[@]}"; do
  [[ -f "$f" ]] || { echo "error: missing $f in repo" >&2; exit 1; }
  cp -v "$f" "$TARGET/$f"
done

if (( INFRA )); then
  for f in "${INFRA_FILES[@]}"; do
    [[ -f "$f" ]] || { echo "warning: missing $f — skipping" >&2; continue; }
    cp -v "$f" "$TARGET/$f"
  done
fi

cat <<EOF

Done.

Reminders:
- Leftover .ecs files on the site (doclets.ecs, scripted.*) are no longer used;
  delete them manually once the new client is confirmed working.
- The site's credentials.php reads ../doclets.eclecity.net.txt (one level above
  the web root); the live copy is already correct — nothing to do.
- Browsers may cache index.html for up to 10 minutes; hard-refresh
  (Ctrl+Shift+R) to test immediately.
EOF
