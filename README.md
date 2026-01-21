# Doclets - Searchable Dated Notes

A system for managing and searching through dated note files using a local LLM.

## Overview

Doclets are date-numbered text files that store notes, decisions, events, and plans. Each doclet focuses on a single subject and uses Markdown formatting.

### File Structure

```
doclets/
├── 2026/
│   ├── 260102.00.txt
│   ├── 260102.01.txt
│   ├── 260108.01.txt
│   └── ...
├── 2025/
│   ├── 251201.01.txt
│   └── ...
└── ...
```

### Doclet Format

Each doclet file:
- Named as `YYMMDD.NN.txt` (e.g., `260102.01.txt`)
- First line is subject: `# Subject line here`
- Rest is Markdown-formatted content
- Organized in year folders for easy management

**Features:**
- Uses local LLM (Ollama) for intelligent search
- Returns list of matching files for multiple matches
- Returns full content for single match
- Natural language queries
- No cloud services required

## Setup

### Requirements

1. **Python 3.6+**

2. **Ollama** (local LLM server)
   ```bash
   # Install Ollama (see https://ollama.ai)
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Pull a model (e.g., llama3.2)
   ollama pull llama3.2
   
   # Start the server (runs on http://localhost:11434 by default)
   ollama serve
   ```

## Example Doclet

**File:** `2026/260108.01.txt`

```markdown
# Setting up Ollama for local LLM

Today I configured Ollama to run locally for the doclet search system.

## Installation Steps

1. Downloaded from ollama.ai
2. Ran the install script
3. Pulled llama3.2 model

## Configuration

- Default port: 11434
- Model storage: ~/.ollama/models
- Can run multiple models

## Usage Notes

- Use `ollama list` to see installed models
- `ollama run llama3.2` for interactive chat
- API endpoint: http://localhost:11434/api/generate

## Tips

1. **One Topic Per Doclet** - Keep each doclet focused on a single subject for better search results
2. **Good Subject Lines** - Use descriptive subjects; they help the LLM match queries
3. **Use Markdown** - Leverage Markdown formatting for structure (headings, lists, code blocks)
4. **Regular Backups** - Back up your doclets directory regularly
5. **Model Selection** - Larger models give better search results but are slower

## Troubleshooting

**"Error querying LLM"**
- Ensure Ollama is running: `ollama serve`
- Check the URL: default is `http://localhost:11434`

**Search returns no results**
- Try rephrasing your query
- Use `#` to see all available doclets
- Check that doclets have proper subject lines
