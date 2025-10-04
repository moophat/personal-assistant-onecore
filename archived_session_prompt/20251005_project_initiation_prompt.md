Build a CLI LLM PoC with these constraints:

**Stack:**
- Python 3.11+
- OpenRouter API (OpenAI-compatible endpoint)
- LangChain for memory (RunnableWithMessageHistory)
- prompt_toolkit for terminal REPL

**Must haves:**
1. REPL interface (> prompt, arrow key history, Ctrl-C handling)
2. Multi-turn memory (session-based, in-memory is fine)
3. External config file (YAML preferred) containing:
   - Model slug (e.g., anthropic/claude-sonnet-4.5)
   - Temperature, max_tokens
   - System prompt text or reference
4. External prompt template (Jinja2 or plain text with variable substitution)
5. Environment variable for API key (OPENROUTER_API_KEY)
6. Error handling for missing env vars, HTTP failures, bad model slugs

**File structure:**
poc-cli-llm/
├─ config/config.yaml
├─ templates/prompt.jinja
├─ src/
│  ├─ main.py
│  ├─ config_loader.py
│  ├─ prompt_builder.py
│  └─ memory.py
├─ requirements.txt
└─ .env.example

**Hot reload mechanism:**
- Store last-modified timestamps for config.yaml and prompt.jinja
- At start of each REPL iteration (before accepting user input):
  - Check if files changed (compare current mtime vs stored)
  - If changed: reload config + rebuild template, log "Config reloaded"
  - Memory/session unaffected
- User gets immediate feedback on config changes without restarting

**Expected flow per turn:**
1. Check config/template files for changes → reload if modified
2. User types input (prompt_toolkit REPL)
3. Load current config + render template with vars
4. Fetch memory for session_id (prior turns)
5. Send composed messages to OpenRouter
6. Print response
7. Append turn to memory
8. Loop to step 1

**Dev workflow:**
1. Run: python src/main.py (starts REPL with session)
2. Chat with model
3. Edit config.yaml or prompt.jinja in another window
4. Type next message in REPL → auto-detects change → applies new config → responds
5. Repeat steps 3-4 without ever restarting

**What I don't need:**
- No streaming (basic request/response is fine)
- No fancy output formatting
- No Docker/deployment config
- No tests (this is a PoC)

**Deliverable:**
Working code + requirements.txt + README with setup/run instructions.

