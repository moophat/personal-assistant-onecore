i# Refactor Plan: One Core Structure (Option 2 - Subcommands)

## Phase 1: Git Checkpoint
- [ ] Verify git status is clean
- [ ] Create checkpoint: `git add -A && git commit -m "checkpoint: before One Core refactor"`

## Phase 2: Restructure Directories
1. Move `src/core/` → `core/` (top-level)
2. Move `src/interfaces/cli.py` → `adapters/cli_ptk.py`
3. Move `src/utils/logger.py` → `core/logger.py`
4. Delete `src/main.py` (replaced by top-level `main.py`)
5. Delete empty `src/` directory tree

## Phase 3: Update All Imports
1. Fix imports in `core/` modules: `from core.X` instead of `from src.core.X`
2. Fix imports in `adapters/cli_ptk.py`: `from core.X` instead of `from src.core.X`
3. Verify no references to `src/` remain in codebase

## Phase 4: Create Launcher (main.py)
1. Create `main.py` at project root
2. Load environment: `load_dotenv()` and check `OPENROUTER_API_KEY` exists
3. Parse `sys.argv[1]` with default "cli" if not provided
4. Instantiate `ConfigLoader("config/config.yaml")` ONCE
5. Instantiate `PromptBuilder("templates/prompt.jinja")` ONCE
6. Route to adapter based on command:
   - "cli" → `from adapters.cli_ptk import run_repl`
   - Handle unknown commands with error message
7. Pass `(config_loader, prompt_builder, api_key)` to adapter

**CRITICAL:** Pass ConfigLoader and PromptBuilder **INSTANCES**, NOT frozen dicts

## Phase 5: Refactor CLI Adapter
1. In `adapters/cli_ptk.py`, define `run_repl(config_loader, prompt_builder, api_key)` function
2. Accept instances as parameters (not dicts)
3. Initialize logger inside adapter (UI-specific logging setup)
4. Session management stays in adapter (UI-specific: sync/async)
5. Preserve existing hot-reload trigger: call `config_loader.check_and_reload()` before each REPL turn (current line 239 logic)
6. Keep all slash commands, REPL logic unchanged
7. Remove old `if __name__ == "__main__"` block and `load_dotenv()` (now in launcher)

## Phase 6: Verify Functionality
- [ ] `python main.py cli` runs REPL with no errors
- [ ] `python main.py` defaults to CLI (no arg needed)
- [ ] All slash commands work (/history, /clear, /debug, /loglevel)
- [ ] Config hot-reload: edit config.yaml while running, see reload message
- [ ] Template hot-reload: edit prompt.jinja while running, see reload message
- [ ] Memory persists across turns in same session
- [ ] Logging outputs to file + stdout correctly

## Phase 7: Config Structure (Future Prep)
1. Keep `config/config.yaml` as base config
2. Create placeholder files (empty for now):
   - `config/cli_ptk.yaml` (comment: "CLI-specific overrides")
   - `config/tui_textual.yaml` (comment: "Textual TUI overrides - future")
3. Document in README: config layering pattern (base + UI-specific)

## Phase 8: Final Commit
- [ ] `git add -A`
- [ ] `git commit -m "refactor: adopt One Core structure with subcommand launcher"`
- [ ] `git log --oneline` shows clean history

## Rollback Plan (if Phase 6 fails)
```bash
git reset --hard HEAD~1  # Back to checkpoint
