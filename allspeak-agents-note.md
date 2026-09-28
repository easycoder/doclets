# Patch for /home/graham/dev/allspeak/AGENTS.md

Insert after the Repository Structure code block (after the line `  /examples/         Demo apps (carried over)` and the closing ``` ), before `## Working in non-English languages (FR / IT / DE / …)`:

```markdown
### Canonical source — this repo owns these files

This repository is the **primary source of truth** for the JS runtime (`js/allspeak/`), the editor (`asedit.allspeak`), the doc-block analysers (`tools/asdoc-check*.py/.allspeak`), and the learning material (`learn/`). Other projects may mirror or symlink these files locally (e.g. the doclets project symlinks `allspeak-js/*.js` here via `relink-allspeak.sh` and keeps copies of `asedit.allspeak` / `asdoc-check.py`).

- Make changes to shared files **here first**, then let consumer projects pick up the mirror.
- **Never "fix" a shared file in a consumer project's copy** — that silently forks the mirror and the divergence is hard to spot later.
- If you're working in a consumer project and need a change to a file this repo owns, switch to this repo (a separate agent session anchored here) rather than editing the copy in place.
```

The reasonix.toml `[sandbox] allow_write = ["/home/graham/dev/allspeak"]` change is already saved and will take effect from the next session.
