# Doclets

Central file storage and reader for Markdown documents, now running on
[AllSpeak](https://github.com/allspeak.ai/allspeak-py) (a multilingual fork of
EasyCoder). Client/server communication uses MQTT.

## Files

- `doclets.as` — the browser UI (AllSpeak JS dialect, Webson for DOM rendering; runs on smartphones)
- `docletServer.as` — the server (AllSpeak Python dialect)
- `as_doclets.py` — Python plugin with the doclet search/manage logic (loaded by `docletServer.as`)
- `doclets.json` — Webson screen layout
- `index.html` — entry point; loads `allspeak-min.js` from `https://allspeak.ai/dist/`
- `allspeak-js/`, `allspeak-py/` — vendored AllSpeak runtimes for local development
  (`relink-allspeak.sh` replaces the JS files with symlinks to your AllSpeak checkout)
- `credentials.php`, `credentials-local`, `doclets.eclecity.net.txt` — MQTT credentials
- `docletServer.py` — cron helper that restarts `docletServer.as` daily
- `doclets` — installer script for the server (installs the `allspeak-ai` pip package)

## Running locally

- **Server:** `allspeak docletServer.as`
- **Client:** `python3 -m http.server 8080` → `http://localhost:8080`

On localhost the client prompts for the four MQTT credential values
(`dev-broker`, `dev-username`, `dev-password`, `dev-mac`) and stores them in
`localStorage`; remove those keys to reset them.

## Deploying

`./deploy.sh` deploys the three files the client needs (`index.html`,
`doclets.as`, `doclets.json`); add `--infra` to also copy `credentials.php`,
`.htaccess`, `mqtt_token.php`, `favicon.ico`. It only copies — leftover `.ecs`
files on the site should be removed by hand once the new client is confirmed
working.

Targets, in order of precedence:
1. a command-line target — `/path/to/web/root` (local `cp`) or `user@host:/path` (rsync)
2. `DOCLETS_DEPLOY_DIR=/path ./deploy.sh`
3. `deploy.conf` — copy `deploy.conf.example` and fill in `DEPLOY_USER` /
   `DEPLOY_HOST` / `DEPLOY_PATH`; then a bare `./deploy.sh` rsyncs to
   `user@doclets.eclecity.net:path`

`DEPLOY_DRY_RUN=1 ./deploy.sh` prints the rsync command without running it.

## Local LLM search (experimental)

The query box has an **AI** checkbox (or prefix any query with `LLM:`). With it
checked:

- **Synthesis questions** — "list the main topics covered by doclets in the
  Linux topic", "summarize what these doclets cover" — are answered by the
  local Ollama model from the doclets' **subject lines only** (no full-body
  reads, so this scales with the corpus).
- **Semantic searches** with no literal match (e.g. "Python MQTT messaging")
  are retrieved by embedding similarity over a per-topic cached index, then
  ranked by the model.
- Plain (unchecked) queries keep their existing behaviour: filename lookup, or
  complete literal substring matching.

The doclet server reads its LLM configuration from environment variables:

| Variable | Default |
|---|---|
| `DOCLETS_OLLAMA_URL` | `http://localhost:11434` |
| `DOCLETS_LLM_MODEL` | `qwen3.5:9b` |
| `DOCLETS_EMBED_MODEL` | `nomic-embed-text` |
| `DOCLETS_LLM_TOP_K` | `20` |
| `DOCLETS_LLM_NUM_CTX` | `8192` |
| `DOCLETS_LLM_KEEP_ALIVE` | `30m` |
| `DOCLETS_LLM_TIMEOUT` | `120` |
| `DOCLETS_EMBED_CACHE` | `~/.doclet-embeddings` |
| `DOCLETS_LLM_SYNTH` | synthesis-query markers (comma-separated) |

One-time setup on the machine running the doclet server:
`ollama pull qwen3.5:9b` and `ollama pull nomic-embed-text`. Server-side tests
(no model needed) live in `test_as_doclets.py`.
