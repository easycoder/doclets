#!/usr/bin/env python3
"""Render documents/devto-doclets.md -> documents/devto-doclets.html.

Regenerate whenever the .md changes, so the two stay in step:

    python3 documents/md-to-html.py

Stdlib only (no pip packages). Handles the markdown subset used by the dev.to
post: front matter (stripped; title/description shown in the page header),
headings, one-line paragraphs, bullet lists, inline bold/italic/code,
[links], ![images], and raw HTML comments (passed through verbatim).
"""
import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MD = HERE / "devto-doclets.md"
HTML = HERE / "devto-doclets.html"

INLINE = [
    (re.compile(r"!\[([^\]]*)\]\(([^)]*)\)"),
     lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}">'),
    (re.compile(r"\[([^\]]*)\]\(([^)]*)\)"),
     lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>'),
    (re.compile(r"\*\*([^*]+)\*\*"), lambda m: f"<strong>{m.group(1)}</strong>"),
    (re.compile(r"\*([^*]+)\*"), lambda m: f"<em>{m.group(1)}</em>"),
    (re.compile(r"`([^`]+)`"), lambda m: f"<code>{m.group(1)}</code>"),
]


def strip_front_matter(text):
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip("\n"), parts[1]
    return text, ""


def parse_front_matter(block):
    meta = {}
    for line in block.strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"')
    return meta


def inline(text):
    text = html.escape(text, quote=False)
    for pattern, repl in INLINE:
        text = pattern.sub(repl, text)
    return text


def render_block(text):
    """Render a whitespace-delimited block (heading, list, or paragraph)."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return ""

    if lines[0].startswith("# "):
        return f"<h1>{inline(lines[0][2:])}</h1>"
    if lines[0].startswith("## "):
        return f"<h2>{inline(lines[0][3:])}</h2>"
    if lines[0].startswith("### "):
        return f"<h3>{inline(lines[0][4:])}</h3>"

    if all(ln.startswith("- ") for ln in lines):
        items = "\n".join(f"  <li>{inline(ln[2:])}</li>" for ln in lines)
        return f"<ul>\n{items}\n</ul>"

    return f"<p>{inline(' '.join(lines))}</p>"


def split_blocks(text):
    """Split text into blank-line-separated blocks."""
    blocks, current = [], []
    for line in text.splitlines():
        if line.strip():
            current.append(line)
        elif current:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def render(md):
    body, fm_block = strip_front_matter(md)
    meta = parse_front_matter(fm_block)

    # Pass HTML comments through verbatim; render everything else.
    out = []
    pos = 0
    for match in re.finditer(r"<!--.*?-->", body, re.S):
        for block in split_blocks(body[pos:match.start()]):
            out.append(render_block(block))
        out.append(match.group(0))
        pos = match.end()
    for block in split_blocks(body[pos:]):
        out.append(render_block(block))
    body_html = "\n".join(out)

    title = meta.get("title", "Doclets")
    desc = meta.get("description", "")
    header = [f"<h1>{html.escape(title)}</h1>"]
    if desc:
        header.append(f'<p class="subtitle">{html.escape(desc)}</p>')

    template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
  body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         max-width: 720px; margin: 0 auto; padding: 24px 20px 80px;
         line-height: 1.6; color: #1a1a1a; }
  h1 { font-size: 1.9em; line-height: 1.25; margin-bottom: 0.2em; }
  .subtitle { color: #555; font-size: 1.05em; }
  h2 { margin-top: 1.6em; border-bottom: 1px solid #e2e2e2; padding-bottom: 4px; }
  img { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 6px;
        display: block; margin: 1.2em auto; }
  code { background: #f3f3f3; padding: 0.1em 0.35em; border-radius: 4px;
         font-size: 0.92em; }
  a { color: #0969da; }
</style>
</head>
<body>
__HEADER__
__BODY__
</body>
</html>
"""
    return (template
            .replace("__TITLE__", html.escape(title))
            .replace("__HEADER__", "\n".join(header))
            .replace("__BODY__", body_html))


def main():
    md = MD.read_text(encoding="utf-8")
    HTML.write_text(render(md), encoding="utf-8")
    print(f"Wrote {HTML}")


if __name__ == "__main__":
    main()
