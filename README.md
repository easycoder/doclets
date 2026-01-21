# Doclets - Searchable Dated Notes

A system for managing and searching through dated note files using a local LLM.

## Overview

Doclets are date-numbered text files that store notes, decisions, events, and plans. Each doclet focuses on a single subject and uses Markdown formatting.

### File Structure

```
doclets/
├── 2026/
│   ├── 260102.01.txt
│   ├── 260102.02.txt
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

## Scripts

### `doclet_create.py` - Create New Doclets

Helper script to create new doclet files with automatic numbering.

**Usage:**
```bash
# Create a new doclet (will open in editor)
./doclet_create.py "Subject of the note"

# Create with initial content
./doclet_create.py "Meeting notes" --content "Discussed project timeline and next steps"

# Create without opening editor
./doclet_create.py "Quick note" --no-edit

# Use a different directory
./doclet_create.py "Subject" --dir /path/to/doclets
```

**Features:**
- Automatically determines next available number for today
- Creates year folder if needed
- Opens in your default editor (set `$EDITOR` environment variable)
- Supports custom content

### `doclet_search.py` - Search Doclets with LLM

Search through your doclets using natural language queries powered by a local LLM.

**Usage:**
```bash
# Search for relevant doclets
./doclet_search.py "ESP32 networking"

# List all doclets
./doclet_search.py --list

# Use a different model
./doclet_search.py --model llama2 "python async programming"

# Use a different directory
./doclet_search.py --dir /path/to/doclets "topic"

# Use a different Ollama server
./doclet_search.py --url http://192.168.1.100:11434 "query"
```

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

3. **Python dependencies**
   ```bash
   pip install requests
   ```

### Installation

1. Make scripts executable:
   ```bash
   chmod +x doclet_create.py doclet_search.py
   ```

2. Optional: Add to PATH or create aliases:
   ```bash
   # In your ~/.bashrc or ~/.zshrc
   alias doclet-new='/path/to/doclets/doclet_create.py'
   alias doclet-search='/path/to/doclets/doclet_search.py'
   ```

## Example Workflow

```bash
# Create a new doclet about ESP32
./doclet_create.py "ESP32 WiFi Configuration Notes"
# ... edit the file with your notes ...

# Later, search for ESP32 related doclets
./doclet_search.py "ESP32 networking"

# List all doclets
./doclet_search.py --list
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
```

## Advanced Usage

### Custom Ollama Models

You can use any Ollama model:
```bash
ollama pull llama2
./doclet_search.py --model llama2 "your query"
```

### Remote Ollama Server

If running Ollama on another machine:
```bash
./doclet_search.py --url http://server-ip:11434 "query"
```

### Environment Variables

Set defaults:
```bash
export DOCLETS_DIR=/path/to/doclets
export OLLAMA_URL=http://localhost:11434
export EDITOR=vim
```

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

**"No doclets found"**
- Check you're in the right directory or use `--dir`
- Ensure year folders exist (e.g., `2026/`)

**Search returns no results**
- Try rephrasing your query
- Use `--list` to see all available doclets
- Check that doclets have proper subject lines
