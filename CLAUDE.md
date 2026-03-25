Read the following primer prompts:

https://easycoder.github.io/agent-primer-python.md
https://easycoder.github.io/agent-primer-js.md

The project is a central file storage system and reader for Markdown documents. Communication between the two is done with MQTT.

The server is docletServer.ecs. This is written in the Python dialect of EasyCoder.

The client is doclets.ecs. It's a web application written in the JS dialect of EasyCoder and uses Webson for all DOM rendering. It runs on any smartphone. The entry point is index.html, which contains a loader to start up the main script.

## Syntax differences between JS and Python EasyCoder

The primers don't cover everything. Key differences discovered from the runtime source:

### HTTP GET
- **JS:** `rest get Variable from URL`
- **Python:** `get Variable from url URL [or {command}]`

### JSON parsing
- **JS:** `json get Variable from JsonString key KeyName`
- **Python:** Parse into a dictionary first, then extract entries:
  ```
  put json StringVar into DictVar
  put entry `key` of DictVar into Variable
  ```

### MQTT token
In both runtimes, `mqtt token Username Password` (two arguments) creates a `{username, password}` credentials object for non-flespi brokers.

### Newlines in strings (JS)
`\n` escape sequences do not work inside backtick strings. Use `cat newline cat` instead:
```
put prompt `Line 1:` cat newline cat `Line 2:` into Variable
```

### Hostname detection (JS)
`the hostname` returns `window.location.hostname` (e.g. `localhost` in dev, the real domain in production).

## Doclets project specifics

### Running locally
- **Server:** `easycoder docletServer.ecs` (Python)
- **Client:** `python3 -m http.server 8080` from the project directory, then open `http://localhost:8080`

### MQTT credentials
The production client fetches credentials from `https://doclets.eclecity.net/credentials.php`, which returns a JSON object with four fields: `broker`, `username`, `password`, `serverID`.

On `localhost`, CORS blocks this request. Instead, the client prompts for all four values on first load and stores them in `localStorage` under `dev-broker`, `dev-username`, `dev-password`, `dev-serverID`. To reset them, remove those keys from `localStorage`.

## EasyCoder Python runtime

When fixing bugs in the core Python runtime, edit the source at `~/dev/easycoder.github.io/easycoder-py/easycoder/` — that's where the flit builder runs. After editing, reinstall with `pip install -e .` or rebuild/publish as appropriate. Don't edit the installed copies under `~/.local/lib/` directly (or do so only as a temporary test, then apply the same change to the source).

Tasks will be provided as the need arises.
