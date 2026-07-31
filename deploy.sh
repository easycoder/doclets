#!/usr/bin/env bash
set -euo pipefail

# deploy.sh — deploy the AllSpeak doclets client to doclets.eclecity.net.
#
# The new client needs exactly three files served by the web server:
#   index.html    – the page + loader (loads the AllSpeak CDN bundle)
#   doclets.as    – the client script (fetched by the loader)
#   doclets.json  – Webson screen layout
#
# It only copies/pushes; it never deletes. Leftover .ecs files on the site
# (doclets.ecs, scripted.*, ...) are no longer used — remove them by hand once
# the new client is confirmed working.
#
# Target resolution, in order of precedence:
#   1. a command-line target:
#        ./deploy.sh /path/to/web/root            # local directory (cp)
#        ./deploy.sh user@host:/path/to/root      # remote host (rsync)
#   2. the DOCLETS_DEPLOY_DIR env var (local directory)
#   3. deploy.conf (copy deploy.conf.example and fill in):
#        rsync to $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PATH
#
# Options:
#   --infra        also copy credentials.php, .htaccess, mqtt_token.php, favicon.ico
#   -h | --help    show this help
#
# Environment:
#   DEPLOY_DRY_RUN=1   print the rsync command without running it
#   DEPLOY_PORT=<n>    ssh port (from deploy.conf or environment)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

INFRA=0
case "${1:-}" in
  -h|--help|help)
    sed -n '2,45p' "$0"
    exit 0
    ;;
  --infra)
    INFRA=1
    shift
    ;;
esac

# Optional per-machine connection details (never committed).
if [[ -f deploy.conf ]]; then
  # shellcheck disable=SC1091
  source deploy.conf
fi

TARGET="${1:-}"
if [[ -z "$TARGET" && -n "${DOCLETS_DEPLOY_DIR:-}" ]]; then
  TARGET="$DOCLETS_DEPLOY_DIR"
fi
if [[ -z "$TARGET" ]]; then
  if [[ -n "${DEPLOY_USER:-}" && -n "${DEPLOY_HOST:-}" && -n "${DEPLOY_PATH:-}" ]]; then
    TARGET="$DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PATH"
  else
    echo "No target given and no connection details configured." >&2
    echo "Usage: $0 [--infra] TARGET_DIR | user@host:/path" >&2
    echo "  or copy deploy.conf.example to deploy.conf and set DEPLOY_USER/DEPLOY_HOST/DEPLOY_PATH." >&2
    exit 2
  fi
fi

CLIENT_FILES=(index.html doclets.as doclets.json)
INFRA_FILES=(credentials.php .htaccess mqtt_token.php favicon.ico)

FILES=("${CLIENT_FILES[@]}")
if (( INFRA )); then
  FILES+=("${INFRA_FILES[@]}")
fi
for f in "${FILES[@]}"; do
  [[ -f "$f" ]] || { echo "error: missing $f in repo" >&2; exit 1; }
done

# --- local target: plain copy -------------------------------------------
if [[ "$TARGET" != *:* ]]; then
  if [[ ! -d "$TARGET" ]]; then
    echo "error: target directory not found: $TARGET" >&2
    exit 2
  fi
  echo "Deploying doclets client to $TARGET"
  for f in "${FILES[@]}"; do
    cp -v "$f" "$TARGET/$f"
  done
else
  # --- remote target: rsync over ssh -------------------------------------
  REMOTE="$TARGET"
  [[ "$REMOTE" == */ ]] || REMOTE="$REMOTE/"
  SSH_CMD=(ssh)
  if [[ -n "${DEPLOY_PORT:-}" ]]; then
    SSH_CMD=(ssh -p "$DEPLOY_PORT")
  fi
  RSYNC_CMD=(rsync -az -e "${SSH_CMD[*]}" "${FILES[@]}" "$REMOTE")
  if [[ -n "${DEPLOY_DRY_RUN:-}" ]]; then
    echo "Would run: ${RSYNC_CMD[*]}"
    exit 0
  fi
  echo "Deploying doclets client to $REMOTE"
  "${RSYNC_CMD[@]}"
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
