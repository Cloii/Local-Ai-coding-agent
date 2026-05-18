# cloii-cli

> Personal AI coding agent — runs locally or on free cloud tiers. No subscriptions.

Built from scratch for my own workflow. Supports **Ollama** (local/offline), **Groq** (free tier, fast), and **OpenRouter** (free models). CLI + Desktop GUI.

---

## Features

- **Agent loop** — AI reads files, writes code, runs commands, searches the web autonomously
- **7 built-in tools** — bash, read_file, write_file, edit_file, list_files, web_fetch, web_search
- **3 providers** — Ollama (local), Groq (free), OpenRouter (free)
- **Desktop GUI** — Electron + React terminal-style interface
- **Zero dependencies** — Python stdlib only for the core CLI
- **Session save/load** — `/save` and `/load` your conversations

---

## Quick Start

### Requirements
- Python 3.10+
- [Ollama](https://ollama.com) (for local models)
- Node.js 18+ (for desktop GUI only)

### CLI

```bash
git clone https://github.com/Cloii/cloii-cli.git
cd cloii-cli
pip install -e .

# Run with Ollama (make sure Ollama is running)
cloii

# Run with Groq (free tier)
export GROQ_API_KEY=your_key_here
cloii --provider groq --model llama-3.3-70b-versatile

# Run with OpenRouter (free models)
export OPENROUTER_API_KEY=your_key_here
cloii --provider openrouter --model meta-llama/llama-3.3-70b-instruct:free
```

### Desktop GUI

```bash
cd desktop
npm install
npm run dev
```

---

## Providers & Free Models

| Provider | Free? | Setup |
|----------|-------|-------|
| Ollama | ✅ Always free | Install from ollama.com |
| Groq | ✅ Free tier | Get key at console.groq.com |
| OpenRouter | ✅ Free models | Get key at openrouter.ai |

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/provider [name]` | Switch provider |
| `/model [name]` | Switch model |
| `/models` | List available models |
| `/status` | Show current config |
| `/clear` | Clear conversation |
| `/save [file]` | Save session to JSON |
| `/load [file]` | Load session from JSON |
| `/cd [path]` | Change directory |
| `/pwd` | Show current directory |
| `/exit` | Quit |

---

## Tools the Agent Can Use

| Tool | What it does |
|------|-------------|
| `bash` | Run shell commands |
| `read_file` | Read any file |
| `write_file` | Create or overwrite files |
| `edit_file` | Find-and-replace in files |
| `list_files` | Browse directory contents |
| `web_fetch` | Fetch and parse web pages |
| `web_search` | Search DuckDuckGo |

---

## Project Structure

```
cloii-cli/
├── cloii_cli/
│   ├── __main__.py      # Entry point
│   ├── cli.py           # REPL + slash commands
│   ├── agent.py         # Agent loop (LLM ↔ tools)
│   ├── config.py        # Configuration
│   ├── server.py        # JSON server for desktop
│   ├── providers/
│   │   ├── ollama.py    # Ollama adapter
│   │   └── openai_compat.py  # Groq / OpenRouter
│   └── tools/
│       └── __init__.py  # All 7 tools
├── desktop/
│   ├── electron/        # Electron main + preload
│   └── src/             # React UI
└── pyproject.toml
```

---

## License

MIT — built by Cloii
