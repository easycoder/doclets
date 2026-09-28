# Architecture Notes (for AI)

## Runtime layers
1. AllSpeak runtime modules (JS)
2. AllSpeak scripts (`.allspeak`) for app logic
3. Webson JSON for UI structure
4. Python plugin/server for doclet content and search

## UI path
- `doclets.allspeak` calls `render MainScreenWebson in Body`
- `Browser.js` handles `render` command
- `Webson.js` builds DOM from `doclets.json`

## Data path
- Client sends MQTT actions (`topics`, `query`, `view`)
- Server returns payloads
- `doclets.allspeak` updates state and DOM content

## State machine hints
Common states in `doclets.allspeak`:
- `topics`: waiting/processing available topics
- `query`: processing search results
- `content`: showing selected doclet

## UI behavior rules currently used
- Query input should remain usable
- Send button is enabled only when topics are loaded and selected
- Topic label has three clear states:
  - no selection
  - partial selection
  - all selected

## PWA layer
- `index.html` links `manifest.json`, sets the iOS/theme meta, and registers
  `sw.js` on `load`
- `sw.js` caches the *shell* only (network-first, cache fallback); doclet
  content still needs MQTT, so there is no offline reader
- Shell requests are cached with the query string stripped, because the loader
  fetches `doclets.allspeak?v=` cat now
- Icons are generated from `doclets.png` by `make-icons.py`; `node pwa-check.js`
  re-checks manifest/icons/`sw.js`/`deploy.sh` consistency and `node sw-test.js`
  drives `sw.js` against a stub Cache API. Keep the PWA files in `deploy.sh`'s
  `CLIENT_FILES` or they won't reach the site

## Known integration sensitivity
If `render ... in Body` fails with "Webson engine is not loaded":
- ensure `Webson.js` is loaded by `index.html`
- ensure Browser render logic and Webson symbol name agree (`AllSpeak_Webson` vs legacy `Webson`)

## Dialect notes
- The AllSpeak JS runtime looks for a `<pre id="allspeak-script">` element
- The runtime debug/tracer element id is `allspeak-tracer` (declared in
  `doclets.json` and attached in `doclets.allspeak`); do not rename it back to the
  EasyCoder spelling `easycoder-tracer`
- The Python plugin (`as_doclets.py`) imports its base classes from the
  `allspeak` package (`from allspeak import Handler, ECValue, ...`)
