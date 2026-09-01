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
- `credentials.php` — serves the MQTT credentials JSON; `credentials-local.example` /
  `doclets.eclecity.net.txt.example` — credential schemas (the real credential
  files are gitignored; see `.gitignore`)
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

The query bar has two buttons — **Plain query** and **LLM query** (or prefix
any query with `LLM:`). With the LLM button:

- **Synthesis questions** — "list the main topics covered by doclets in the
  Linux topic", "summarize what these doclets cover" — are answered by the
  local Ollama model from the doclets' **subject lines only** (no full-body
  reads, so this scales with the corpus).
- **Semantic searches** with no literal match (e.g. "Python MQTT messaging")
  are retrieved by embedding similarity over a per-topic cached index, then
  ranked by the model. If the model declines to pick (or errors), the
  embedding-retrieved candidates are returned instead — so a fickle model
  can't turn a good query into "no results".
- Plain queries keep their existing behaviour: filename lookup, or complete
  literal substring matching. An empty query lists every doclet in the
  selected topics.

While a query is in flight the two query buttons turn amber and are disabled;
if it fails (timeout) they turn red.

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
| `DOCLETS_LLM_TEMPERATURE` | `0.3` — lower = more deterministic ranking; raise for more variety |
| `DOCLETS_EMBED_CACHE` | `~/.doclet-embeddings` |
| `DOCLETS_ACL_PATH` | `~/.doclet-save.acl` — topic permissions (see Access control) |
| `DOCLETS_ACTIVITY_LOG` | `~/.doclet-activity.log` — append-only action log |
| `DOCLETS_LLM_SYNTH` | synthesis-query markers (comma-separated) |
| `DOCLETS_LLM_WARMUP` | `0` — set `1` to load the model at server startup so the first query is fast |

One-time setup on the machine running the doclet server:
`ollama pull qwen3.5:9b` and `ollama pull nomic-embed-text`. Server-side tests
(no model needed) live in `test_as_doclets.py`.

Note: the first LLM query after a server restart can take up to a minute (model
load + first-time embedding); the client allows ~2 minutes for AI queries
(plain queries keep the ~10s wait). If first-query latency bothers you, set
`DOCLETS_LLM_WARMUP=1` on the server.

## Access control (topics)

Every request carries the caller's auth token as its first line
(`token\n<request>`); an empty token means anonymous. Permissions live in
`~/.doclet-save.acl` (version 2), additive over the older write-grants format:

    { "version": 2,
      "entries": [ {"name": "Alice", "token": "…", "topics": ["Linux", "*"]} ],
      "topics": { "Private": {"owner": "…", "public": false,
                                "readers": ["…"], "deleters": ["…"]} } }

- **Unconfigured topics stay open** — anyone may read; writes via `entries`.
- `entries` → create/modify rights (unchanged behaviour; `*` = all topics).
- `topics.<name>.owner` → full rights (read/write/delete).
- `public: true` → anyone may read; `false` → owner + `readers` only
  (writers may also read what they edit).
- `deleters` → who may delete (on unconfigured topics the write grant
  still implies delete).

Activity log: append-only JSONL at `~/.doclet-activity.log` recording
create/modify/delete and permission denials (who did what and when; no
reader tooling yet).

## Editor support (doc blocks)

Every section of `doclets.as` / `docletServer.as` is wrapped in an AllSpeak doc
block (`!!` prose, `!! @hash`, `!!!`) so the code can be reviewed block by
block in the AllSpeak editor (`edit.html` — vendored, along with `asedit.as`,
`asedit.json`, `allspeak.js` and `plugins/`).

After editing a `.as` file, refresh the section hashes and validate:

    python3 asdoc-check.py --write doclets.as docletServer.as
    python3 asdoc-check.py doclets.as docletServer.as   # expect 0 errors/warnings

To open the editor (block mode), run the AllSpeak dev server from this
directory — it provides the `/list`, `/read` and `/write` routes the editor
needs to open and save files — then browse to `/edit.html`:

    allspeak server.as

(`server.as` is the dev file server for the editor; `docletServer.as` is the
separate MQTT doclet server the deployed client talks to — don't confuse the
two.)
