## Skills
- `/ecs-js` — EasyCoder JS dialect context (use when working on `doclets.ecs`)
- `/ecs-python` — EasyCoder Python dialect context (use when working on `docletServer.ecs`)
- `/ecs-review` — syntax-check any `.ecs` file
- `/doclets-mqtt` — MQTT credentials and localhost setup

## Project overview

Central file storage and reader for Markdown documents. Client/server communication uses MQTT.

- **Server:** `docletServer.ecs` (EasyCoder Python dialect)
- **Client:** `doclets.ecs` (EasyCoder JS dialect, Webson for DOM rendering, runs on smartphones). Entry point: `index.html`.

## Running locally
- **Server:** `easycoder docletServer.ecs`
- **Client:** `python3 -m http.server 8080` → `http://localhost:8080`

Tasks will be provided as the need arises.
