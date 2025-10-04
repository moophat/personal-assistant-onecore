# CLI LLM PoC

A command-line interface for interacting with Large Language Models via OpenRouter API. Features hot-reload configuration, multi-turn conversation memory, and comprehensive debugging tools.

## Features

### Core Features
- **REPL Interface**: Interactive terminal using prompt_toolkit with arrow key history and Ctrl-C handling
- **Multi-turn Memory**: Session-based conversation history using LangChain's message system
- **Hot Reload**: Automatically detects and applies config/template changes without restart
- **External Configuration**: YAML-based config for model settings and prompts
- **Template Support**: Jinja2 templates for flexible prompt customization
- **Environment Variables**: API key loaded from `.env` file
- **Error Handling**: Robust handling of missing env vars, HTTP failures, and invalid models

### Advanced Features
- **Multi-category Logging**: Three logger categories (prompt, http, langchain) with runtime control
- **Slash Commands**: Built-in commands for debugging and runtime control
- **Dual Output Logging**: File (`logs/cli.log`) + stdout with rotating file handler
- **JSON-formatted API Logs**: Detailed request/response logging
- **Runtime Log Level Control**: Adjust logging per category without restart

## Prerequisites

- Python 3.11 or higher
- OpenRouter API key (get one at https://openrouter.ai/keys)

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd poc-cli-llm
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenRouter API key
   ```

## Configuration

### config/config.yaml

Configure model parameters:

```yaml
# Model to use (see https://openrouter.ai/models)
model: google/gemini-2.5-flash-lite-preview-09-2025

# Sampling temperature (0.0 - 2.0)
temperature: 0.7

# Maximum tokens in response
max_tokens: 2000

# System prompt
system_prompt: "You are a helpful AI assistant. Be concise and accurate."
```

All parameters from `config.yaml` are passed to the OpenRouter API, so any OpenRouter-compatible parameters can be added.

### templates/prompt.jinja

Customize the system prompt template with Jinja2:

```jinja
{{ config.system_prompt if config.system_prompt else "You are a helpful AI assistant." }}
```

You can use variables like `{{ config }}` in your templates.

### .env

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

## Usage

### Start the REPL

```bash
python src/main.py
```

### Chat with the Model

Type your messages at the `>` prompt:

```
> Hello! What's the weather like?
[AI response]

> Tell me more about that.
[AI response with conversation context]
```

### Slash Commands

Built-in commands for runtime control:

- **`/history`** - Display full conversation history
- **`/clear`** - Reset conversation memory
- **`/fullhistorylog`** - Toggle between logging current turn vs full conversation
- **`/debug`** - Toggle LangChain debug mode (shows internal processing)
- **`/loglevel [category] [level]`** - Runtime log level control
  - Categories: `prompt`, `http`, `langchain`, `all`
  - Levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`
  - Status: `/loglevel status` shows current levels

**Examples:**
```
> /loglevel http DEBUG
[Loglevel] HTTP logs set to DEBUG

> /history
[Shows all conversation turns]

> /clear
[Conversation cleared]
```

### Hot Reload in Action

1. Start the REPL and have a conversation
2. In another terminal, edit `config/config.yaml` (e.g., change temperature or model)
3. Type your next message in the REPL
4. See `[Config reloaded: config]` message
5. New config applies immediately without losing conversation history

**Example:**
```bash
# Terminal 1: Start app
> Hello
[AI response]

# Terminal 2: Edit config
$ vim config/config.yaml
# Change temperature from 0.7 to 1.0

# Terminal 1: Continue
> Tell me a story
[Config reloaded: config]
[Response using new temperature]
```

### Debug Example

```bash
> /loglevel http DEBUG
[Loglevel] HTTP logs set to DEBUG

> Hello
# (Shows raw HTTP request/response logs in terminal and log file)
```

### Exit

Press `Ctrl-C` or `Ctrl-D` to exit.

## Project Structure

```
poc-cli-llm/
├── config/
│   └── config.yaml              # Model configuration
├── templates/
│   └── prompt.jinja             # Jinja2 templates
├── src/
│   ├── main.py                  # Entry point
│   ├── core/
│   │   ├── config_loader.py     # Config loading + hot reload
│   │   ├── prompt_builder.py    # Jinja2 rendering
│   │   ├── memory.py            # Session memory
│   │   └── llm_service.py       # API client + business logic
│   ├── interfaces/
│   │   └── cli.py               # REPL with commands
│   └── utils/
│       └── logger.py            # Logging system
├── logs/
│   └── cli.log                  # Application logs (auto-created)
├── requirements.txt
├── .env.example
├── .env
└── README.md
```

## Technical Implementation

### Message Flow

```
User Input
    ↓
Check Hot Reload (config/template mtime)
    ↓
Render Template (Jinja2)
    ↓
Build Messages:
    - SystemMessage (rendered template)
    - History (from SessionMemory)
    - HumanMessage (current input)
    ↓
Log API Call (current turn or full)
    ↓
Call OpenRouter API (via LangChain ChatOpenAI)
    ↓
Receive Response
    ↓
Update Session Memory (add HumanMessage + AIMessage)
    ↓
Display Response
    ↓
Loop
```

### Logging System

**Three logger categories:**
- `prompt` (app.prompt) - Application logs, config, prompts (default: INFO)
- `http` (openai/httpx/httpcore) - HTTP request/response debugging (default: WARNING)
- `langchain` - LangChain internal processing (default: WARNING)

**Logging features:**
- Dual output: File (`logs/cli.log`) + stdout
- Rotating file handler (2MB max, 2 backups)
- One-line exception formatting
- JSON-formatted API call logs
- Runtime level adjustment per category

**Logging Modes:**

*Current Turn Mode (default):*
- Logs only new user message + system prompt
- Shows API parameters (model, temperature, etc.)

*Full History Mode (`/fullhistorylog`):*
- Logs complete conversation history sent to API
- All previous turns included in log output
- Useful for debugging context issues

### Memory Architecture

- In-memory storage per session_id
- Messages stored as LangChain `BaseMessage` objects
- Currently hardcoded to `session_id="default"`
- No persistence across restarts (PoC scope)

### Hot Reload Implementation

**How it works:**
- Before each REPL iteration, check mtime of `config.yaml` and `prompt.jinja`
- Compare with last known mtime
- If changed: reload file, update mtime, log changes, notify user
- Memory/session preserved across reloads

This allows real-time experimentation with different models, temperatures, and prompts without restarting.

### API Integration Details

**OpenRouter via LangChain:**
- Uses `ChatOpenAI` with OpenRouter base URL
- Message types: `SystemMessage`, `HumanMessage`, `AIMessage`
- All config parameters passed as kwargs to API
- Dynamic client initialization per request

## Dependencies

```
langchain==0.3.17
langchain-openai==0.3.3
prompt-toolkit==3.0.48
pyyaml==6.0.2
jinja2==3.1.4
python-dotenv==1.0.1
requests==2.32.3
```

## Error Handling

The application handles:
- Missing `OPENROUTER_API_KEY` environment variable
- Invalid or missing config files
- HTTP request failures and timeouts
- Bad model slugs or API errors
- Malformed API responses

## Known Scope Limitations

As this is a proof-of-concept, the following were explicitly NOT included:
- No streaming (basic request/response)
- No fancy output formatting
- No Docker/deployment config
- No tests (PoC scope)
- No conversation persistence across restarts
- Single session per run (session_id="default")

## Development Notes

### Logger Implementation
- Custom `OneLineExceptionFormatter` class for compact stack traces
- `RotatingFileHandler` for automatic log rotation
- Per-category level control via `setLevel()`
- Both file and stdout output

### Config Parameters Supported
All parameters from `config.yaml` are passed to OpenRouter API:
- `model` - Model identifier
- `temperature` - Sampling temperature
- `max_tokens` - Response token limit
- `system_prompt` - System instruction
- Any other OpenRouter-compatible parameters

## Current State

The implementation is **complete and functional** according to initial requirements, with significant enhancements made for developer experience (logging, debugging, runtime control). The codebase is clean, modular, and well-structured for future enhancement.

## API Key Storage

OpenRouter API key stored in `api_key.txt` (already in `.gitignore`):
```
REDACTED_API_KEY
```

## License

MIT
