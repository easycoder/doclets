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
