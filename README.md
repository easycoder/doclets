# Doclets

Central file storage and reader for Markdown documents, now running on
[AllSpeak](https://github.com/allspeak.ai/allspeak-py) (a multilingual fork of
EasyCoder). Client/server communication uses MQTT.

## Files

- `doclets.allspeak` — the browser UI (AllSpeak JS dialect, Webson for DOM rendering; runs on smartphones)
- `docletServer.allspeak` — the server (AllSpeak Python dialect)
- `as_doclets.py` — Python plugin with the doclet search/manage logic (loaded by `docletServer.allspeak`)
- `doclets.json` — Webson screen layout
- `index.html` — entry point; loads `allspeak-min.js` from `https://allspeak.ai/dist/`
- `manifest.json`, `sw.js`, `icon-*.png`, `apple-touch-icon.png` — the PWA bits (see below)
- `doclets.png` — the icon artwork; `make-icons.py` turns it into the PWA icons
- `allspeak-js/`, `allspeak-py/` — vendored AllSpeak runtimes for local development
  (`relink-allspeak.sh` replaces the JS files with symlinks to your AllSpeak checkout)
- `credentials.php` — serves the MQTT credentials JSON; `credentials-local.example` /
  `doclets.eclecity.net.txt.example` — credential schemas (the real credential
  files are gitignored; see `.gitignore`)
- `docletServer.py` — cron helper that restarts `docletServer.allspeak` daily
- `doclets` — installer script for the server (installs the `allspeak-ai` pip package)

## Progressive web app

Doclets installs as an app from the browser (Chrome/Edge/Android "Install",
iOS Safari "Add to Home Screen"):

- `manifest.json` — name, `start_url`/`scope` of `.`, `display: standalone`
  and the icon set. It is deliberately named `.json` rather than
  `.webmanifest`: the host serves `.json` as `application/json`, which every
  browser accepts for a manifest, whereas `.webmanifest` would need an
  `AddType` in `.htaccess` to avoid being served as `application/octet-stream`.
- `sw.js` — service worker. Network-first for the app shell (`index.html`,
  `doclets.allspeak`, `doclets.json`, the icons) and for the two CDN libraries
  `index.html` loads, falling back to the cache when offline. Requests for
  `doclets.allspeak?v=…` / `doclets.json?v=…` are cached without their query
  string, so the loader's cache buster can't fill the cache with copies.
  `credentials.php` is never intercepted or cached.
- `icon-*.png`, `apple-touch-icon.png` — generated from `doclets.png`:

      python3 make-icons.py [source]     # default source: doclets.png
      node pwa-check.js                  # static consistency check
      node sw-test.js                    # behavioural test of sw.js (no browser)

The service worker caches the *shell* only. Doclet content arrives over MQTT,
so the app still needs the network to show anything: installing it buys a
home-screen entry, standalone chrome and a fast (and offline-tolerant) start,
not an offline reader.

## Running locally

- **Server:** `allspeak docletServer.allspeak`
- **Client:** `python3 -m http.server 8080` → `http://localhost:8080`

On localhost the client prompts for the four MQTT credential values
(`dev-broker`, `dev-username`, `dev-password`, `dev-mac`) and stores them in
`localStorage`; remove those keys to reset them.

## Deploying

`./deploy.sh` deploys the files the client needs — `index.html`,
`doclets.allspeak`, `doclets.json`, `manifest.json`, `sw.js`, the PWA icons and
`apple-touch-icon.png`; add `--infra` to also copy `credentials.php`,
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
| `DOCLETS_LLM_KEEP_ALIVE` | `60s` — how long Ollama keeps a model resident after a request (both the chat and embedding models), and the window of doclet activity that counts as one session |
| `DOCLETS_LLM_ALIVE` | `1` — set `0` to stop the server holding the model warm |
| `DOCLETS_LLM_BEAT` | `30` — seconds between keeping-warm beats; keep it below `DOCLETS_LLM_KEEP_ALIVE` |
| `DOCLETS_LLM_VIDEO_PROCS` | `kdenlive,melt,ffmpeg,ffplay,vlc,mpv,obs,shotcut,olive-editor,handbrake,handbrakecli,resolve,davinci-resolve,blender` — the video tools: one of these running, or holding a GPU client, hands the GPU back |
| `DOCLETS_LLM_GPU_CHECK` | `2` — seconds between GPU probes; the answer is cached in between, since beats come round far more often than the GPU changes hands |
| `DOCLETS_LLM_GPU_CLIENT_MIB` | `512` — a GPU client holding at least this much VRAM counts as video work even if its name isn't in the list (0 disables) |
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

### Sharing the GPU with other work

The model sits on the GPU, so the server works to load it once per doclet
session and otherwise stay out of the way:

- A **query** (or `DOCLETS_LLM_WARMUP=1` at startup) opens a *session*, i.e. it
  loads the model and starts holding it warm.
- While a session lasts, every server-loop tick beats: an empty-messages
  `/api/chat` that costs nothing and just refreshes the keep-alive window
  (`DOCLETS_LLM_BEAT` seconds apart). Any doclet request refreshes that window
  too, so reading doclets between queries keeps the model warm — no reload.
- The session ends after `DOCLETS_LLM_KEEP_ALIVE` of no doclet activity, or the
  moment video work claims the GPU; either way the models are evicted there and
  then, and the GPU is free. The next query starts a new session — and therefore
  loads once more.

Video work is spotted two ways. A tool named in `DOCLETS_LLM_VIDEO_PROCS` that
is *running* counts — that is the coarser test, and it is what catches an editor
holding an OpenGL preview, which nvidia-smi's client list doesn't report. Then
nvidia-smi refines it with what is actually on the GPU: a client whose
executable (or a path component of it, so Flatpak-style paths work) matches one
of those names, or any client holding at least `DOCLETS_LLM_GPU_CLIENT_MIB` of
VRAM, which catches heavy work by tools that aren't in the list at all. Matching
is on the executable rather than the whole command line, because browsers pass
their flags — base64 blobs included — where a short tool name like `obs` would
eventually turn up by chance. Browsers and desktop shells hold small GPU
contexts of their own (tens of MiB) and Ollama's own runner is ignored, so
neither is mistaken for video work. The GPU is probed at most every
`DOCLETS_LLM_GPU_CHECK` seconds, and only while a session is open.

The journal says which detector is in use: `[LLM] GPU detection: nvidia-smi`, or
a line explaining why it fell back to running tools (no NVIDIA GPU, no driver
access, nvidia-smi not on PATH), in which case that coarser test is all there is.

Because the window is a *dead-man's switch* (the beats stop when the server
does), a crashed or stopped server also releases the GPU within
`DOCLETS_LLM_KEEP_ALIVE`.

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

Every section of `doclets.allspeak` / `docletServer.allspeak` is wrapped in an
AllSpeak doc block (`!!` prose, `!! @hash`, `!!!`) so the code can be reviewed
block by block in the AllSpeak editor (`edit.html` — vendored, along with
`asedit.allspeak`, `asedit.json`, `allspeak.js` and `plugins/`).

After editing a `.allspeak` file, refresh the section hashes and validate:

    python3 asdoc-check.py --write doclets.allspeak docletServer.allspeak
    python3 asdoc-check.py doclets.allspeak docletServer.allspeak   # expect 0 errors/warnings

To open the editor (block mode), run the AllSpeak dev server from this
directory — it provides the `/list`, `/read` and `/write` routes the editor
needs to open and save files — then browse to `/edit.html`:

    allspeak server.allspeak

(`server.allspeak` is the dev file server for the editor; `docletServer.allspeak`
is the separate MQTT doclet server the deployed client talks to — don't confuse
the two.)
