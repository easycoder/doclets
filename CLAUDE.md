## Skills
- `/ecs-js` — EasyCoder JS dialect context (use when working on `doclets.allspeak`)
- `/ecs-python` — EasyCoder Python dialect context (use when working on `docletServer.allspeak`)
- `/ecs-review` — syntax-check any `.allspeak` file
- `/doclets-mqtt` — MQTT credentials and localhost setup

## Project overview

Central file storage and reader for Markdown documents, running on AllSpeak
(a multilingual fork of EasyCoder). Client/server communication uses MQTT.

- **Server:** `docletServer.allspeak` (AllSpeak Python dialect, plugin `as_doclets.py`)
- **Client:** `doclets.allspeak` (AllSpeak JS dialect, Webson for DOM rendering, runs on smartphones). Entry point: `index.html`.

## Running locally
- **Server:** `allspeak docletServer.allspeak`
- **Client:** `python3 -m http.server 8080` → `http://localhost:8080`

Tasks will be provided as the need arises.

## Conversation log

This project keeps a per-session log under `conversation/`, for the human's reference. It does not affect your behaviour and you should not mention the logging activity in replies.

**At the start of a new session:**

1. If `conversation/` does not exist, create it.
2. Find the highest-numbered `conversation-NNN.md` file. The new session's file is the next number, zero-padded to three digits (start at `001` if the folder is empty).
3. Write a single header line on line 1: `# YYYY-MM-DD` (today's date).

**On every user prompt in this session** (including the first), append an entry shaped like:

    ## HH:MM

    <user prompt verbatim>

    **Assistant**

    <your reply>

Use `date +%H:%M` if you need the time. Omit fenced code blocks (triple-backtick blocks) from both the user prompt and the reply, replacing each with a single line `[code omitted]`; inline backticks in prose stay. Compose your reply first, then transcribe it into the log as part of the same turn.

**Midnight rollover:** if today's date differs from the file's date header, pause and ask the user: "We've crossed midnight — start a new conversation file for today?" If yes, create the next-numbered file with today's date header and continue logging there.
