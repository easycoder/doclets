# AllSpeak + Webson Guide (for AI)

AllSpeak is a multilingual fork of EasyCoder: `.allspeak` scripts, `allspeak` CLI,
`as_`-prefixed Python modules. English remains a supported language, so the
script vocabulary is unchanged from EasyCoder.

(EasyCoder's original `.ecs` source extension became `.as` in AllSpeak, and is
now `.allspeak` — see the AllSpeak `AGENTS.md`. Legacy `.as` files still run.)

## AllSpeak style in this repo
- Treat `.allspeak` as the source of high-level behavior
- Make surgical changes; preserve command vocabulary and flow
- Prefer existing labels/subroutines over introducing new structures

## Typical AllSpeak operations seen here
- attach/create/set/enable/disable
- on click / on change handlers
- JSON helpers (`json split`, `json count`, `json index`, etc.)
- MQTT send/receive and state branching

## Webson usage here
- `doclets.json` defines screen layout and element IDs
- AllSpeak attaches by those IDs
- Renaming IDs requires matching changes in `.allspeak`
- Renaming only Webson object keys is safe if IDs stay stable

## Markdown rendering
- Markdown conversion is delegated from `Browser.js` to `MarkdownRenderer.js`
- Heading lines are rendered with sans-serif
- Extended inline syntax currently supported:
  - `[[color=#800]]text[[/color]]`
  - `[[font=SansSerif]]text[[/font]]`

## Compatibility note
When targeting older Closure/JS modes, avoid `??` and similar modern syntax unless build target is upgraded.
