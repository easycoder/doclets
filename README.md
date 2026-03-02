# Doclets - Searchable Dated Notes

A system for managing and searching through dated note files. The project currently only handles keyword searches. Future development will also enable full-text queries using a local LLM, but this functionality is currently not working.

## Overview

Doclets are date-numbered text files that store notes, decisions, events, and plans. Each doclet focuses on a single subject and uses Markdown formatting.

### File Structure

```
~/Doclets/
   ├── Doclets/
   │   ├── 2026/
   │   │   ├── 260102-00.md
   │   │   ├── 260102-01.md
   │   │   ├── 260108-01.md
   │   │   └── ...
   │   ├── 2025/
   │   │   ├── 251201-01.md
   │   │   └── ...
   │   └── ...
   ├── General/
   │   ├── 2026/
   │   │   ├── 260214-00.md
   │   │   └── ...
   │   └── ...
   └── ...
```

### Doclet Format

Each doclet file:
- Named as `YYMMDD-NN.md` (e.g., `260102-01.mx`)
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
2. **EasyCoder**

## Example Doclet

**File:** `2026/260108.01.txt`

```markdown
# Setting up Ollama for local LLM

Today I configured Ollama to run locally for the doclet search system.

## Installation Steps

1 Downloaded from ollama.ai
2 Ran the install script
3 Pulled llama3.2 model

## Configuration

- Default port: 11434
- Model storage: ~/.ollama/models
- Can run multiple models

## Usage Notes

- Use 'ollama list' to see installed models
- 'ollama run llama3.2' for interactive chat
- API endpoint: http://localhost:11434/api/generate

## Tips

1 **One Topic Per Doclet** - Keep each doclet focused on a single subject for better search results
2 **Good Subject Lines** - Use descriptive subjects; they help the LLM match queries
3 **Use Markdown** - Leverage Markdown formatting for structure (headings, lists, code blocks)
4 **Regular Backups** - Back up your doclets directory regularly
5 **Model Selection** - Larger models give better search results but are slower

## Troubleshooting

**Search returns no results**
 Try rephrasing your query
 Use '#' to see all available doclets
 Check that doclets have proper subject lines
```

## Installation

The code is in two parts. First there's the doclet server; a short ***EasyCoder*** script that handles incoming queries. It uses a special plugin, `ec_doclets.py`, to provide the specific doclet functionality otherwise absent from ***EasyCoder***.

First, install ***EasyCoder***. This is a Python application:
```
pip install easycoder
```
For reasons best known to the PyPi people, on Linux this will install in `.local/bin`, which is probably not on your `$PATH`. Once you've sorted that out, check it runs:
```
$ easycoder
EasyCoder version 260228.1
$
```
Now copy `docletServer.ecs` and `ec_doclets.py` from the repository to somewhere convenient on your computer.

To run the doclet server, type
```
easycoder docletServer.ecs
```
This will immediately report that it can't find the MQTT token. The current implementation is based on the Flespi MQTT broker, so you'll need to set up an account on their free tier get a user token and save it in `~/.mqtt-token`. See [Flespi](https://flespi.io). Having got a token you can use if for other purposes besides this one.

You also need to set up a user ID at `~/.mqtt-userid`, which identifies this particular server. It will receive any MQTT messages sent to your user ID, so it has to be known to your reader client as well (see later). You can use any convenient string; I favour the MAC address of the PC with `/doclets` appended. If this sounds complex, bear in mind that Flespi is normally dealing with far bigger systems than this one.

Next, you don't yet have any doclets. These are held in a top-level folder, `Doclets`, as shown in the diagram above. The main Doclets folder has subfolders for each topic you wish to maintain. Inside these are year folders, and inside those are the actual doclets. Note that all files are date named as they're not expecting to be read other than by the doclet reader. The first line of each doclet should contain enough information to say what it's all about. So create a couple of dummy doclets.

If all is well, the doclet server will now run without reporting any errors. It will report the token, the user ID, the doclet folder and a client ID it has generated for itself. 

Now you can run the reader, on the same machine or on any other. If you're not on the same machine, the `/.mqtt_token` and `~/.mqtt_userid` will both have to be copied from the doclet server. (Note: this is a temporary mechanism; the data will eventually come from a web server.). Get `doclets.ecs` from the repo and put it somewhere convenient, then type
```
easycoder doclets.ecs
```
The UI should start up and after a second or two the buttons will become enabled. Click the `Choose` buttons to select which of your topic you want to search, then type a keyword into the `Query` box and click `Send`. You'll get back a list of doclets, and clicking any one opens another window with the doclet pretty-printed.

## Where this is heading

This project started as a means to test my MQTT implementation(s) and has grown from there. I imagine there's a lot to say, but it'll have to wait until time allows. I am currently training Copilot to understand ***EasyCoder*** to the point it can create and modify scripts. It's not doing a bad job at the moment. The repo will eventually hold information aimed specifically at AI engines, enabling them to treat ***EasyCoder*** as a top-level programming language. The aim is to be able to converse with AI at that level, without having to dive into complex Python or JS code.

A JS-based doclet reader is under construction; this will provide access to the doclet server from any smartphone browser.
