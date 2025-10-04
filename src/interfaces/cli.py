#!/usr/bin/env python3
"""
CLI REPL interface for LLM chat.

This module provides a terminal-based interface using prompt_toolkit.
"""

import os
import sys
import logging
import json
from pathlib import Path

from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
import langchain

# Import from core
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_loader import ConfigLoader
from core.prompt_builder import PromptBuilder
from core.memory import SessionMemory
from core.llm_service import LLMService
from utils.logger import init_logger


class REPLCLI:
    """Main REPL CLI application."""

    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Enable OpenAI SDK debug logging (shows raw HTTP requests/responses)
        os.environ["OPENAI_LOG"] = "debug"

        # Initialize root logger (base level for all loggers)
        base_dir = Path(__file__).parent.parent.parent
        log_file = base_dir / "logs" / "cli.log"
        init_logger(
            log_level=logging.DEBUG,  # Root at DEBUG to allow all categories
            log_file=str(log_file),
            shell_output=True,
            print_log_init=True,
        )

        # Create separate logger categories with individual control
        # Category: prompt - our application logs (config, prompts, etc)
        self.prompt_logger = logging.getLogger("app.prompt")
        self.prompt_logger.setLevel(logging.INFO)  # Default: show prompts

        # Category: http - HTTP request/response logs from OpenAI/httpx
        self.http_logger = logging.getLogger("http")
        openai_logger = logging.getLogger("openai")
        openai_logger.setLevel(logging.WARNING)  # Default: hide HTTP logs
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.WARNING)
        httpcore_logger = logging.getLogger("httpcore")
        httpcore_logger.setLevel(logging.WARNING)

        # Category: langchain - LangChain internal processing
        self.langchain_logger = logging.getLogger("langchain")
        self.langchain_logger.setLevel(logging.WARNING)  # Default: hide

        # Silence noisy libraries
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        # Use prompt logger as main logger
        self.logger = self.prompt_logger

        # Check for API key
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            self.logger.error("OPENROUTER_API_KEY environment variable not set")
            print("Error: OPENROUTER_API_KEY environment variable not set")
            sys.exit(1)

        # Initialize components
        config_loader = ConfigLoader(base_dir / "config" / "config.yaml")
        prompt_builder = PromptBuilder(base_dir / "templates" / "prompt.jinja")
        session_memory = SessionMemory()

        # Initialize LLM service
        self.llm_service = LLMService(
            config_loader=config_loader,
            prompt_builder=prompt_builder,
            session_memory=session_memory,
            api_key=self.api_key,
            logger=self.logger,
        )

        # Session ID (could be made dynamic if needed)
        self.session_id = "default"

        # Logging mode toggles
        self.log_full_history = False
        self.langchain_debug = False
        self.httpx_event_hooks = None  # Store httpx event hooks for patching

        # Prompt toolkit session for REPL
        self.prompt_session = PromptSession(history=InMemoryHistory())

        # Initial load
        try:
            self.llm_service.config_loader.load()
            self.llm_service.prompt_builder.load()
        except Exception as e:
            self.logger.error(f"Error loading initial configuration: {e}")
            print(f"Error loading initial configuration: {e}")
            sys.exit(1)

    def handle_command(self, command: str) -> None:
        """Handle slash commands."""
        cmd = command.strip().lower()

        if cmd == "/history":
            # Dump full conversation history
            history = self.llm_service.get_history(self.session_id)
            if not history:
                self.logger.info("No conversation history yet")
                return

            self.logger.info("=== Conversation History ===")
            for i, msg in enumerate(history, 1):
                self.logger.info(f"[{i}] {msg['type']}: {msg['content']}")
            self.logger.info(f"=== Total messages: {len(history)} ===")

        elif cmd == "/clear":
            # Clear conversation history
            self.llm_service.clear_history(self.session_id)
            self.logger.info("Conversation history cleared")

        elif cmd == "/fullhistorylog":
            # Toggle full history logging mode
            self.log_full_history = not self.log_full_history
            status = "enabled" if self.log_full_history else "disabled"
            self.logger.info(f"Full history logging {status}")

        elif cmd == "/debug":
            # Toggle LangChain debug mode (shows internal processing)
            # Note: OpenAI SDK HTTP logging is always enabled at startup
            self.langchain_debug = not self.langchain_debug

            # Enable/disable LangChain's internal debug logging
            langchain.debug = self.langchain_debug
            langchain.verbose = self.langchain_debug

            status = "enabled" if self.langchain_debug else "disabled"
            self.logger.info(f"LangChain debug mode {status}")
            if self.langchain_debug:
                self.logger.info("Will show LangChain internal processing")
            else:
                self.logger.info("HTTP request logging still active (set at startup)")

        elif cmd.startswith("/loglevel"):
            # Change log level: /loglevel prompt INFO or /loglevel http DEBUG
            parts = command.split()

            # Show current status
            if len(parts) == 1 or (len(parts) == 2 and parts[1].lower() == "status"):
                print("\n=== Current Log Levels ===")
                print(f"ROOT:      {logging.getLevelName(logging.getLogger().level)} (fixed at DEBUG)")
                print(f"prompt:    {logging.getLevelName(self.prompt_logger.level)}")
                print(f"http:      {logging.getLevelName(logging.getLogger('openai').level)}")
                print(f"langchain: {logging.getLevelName(self.langchain_logger.level)}")
                print("=========================\n")
                print("Note: ROOT is fixed at DEBUG to allow category-level control")
                return

            if len(parts) < 2 or len(parts) > 3:
                print("Usage: /loglevel [category] [level]")
                print("       /loglevel status  (show current levels)")
                print("Categories: prompt, http, langchain, all")
                print("Levels: DEBUG, INFO, WARNING, ERROR")
                print("Example: /loglevel http DEBUG")
                return

            # Parse arguments
            if len(parts) == 2:
                category = "all"
                level_name = parts[1].upper()
            else:
                category = parts[1].lower()
                level_name = parts[2].upper()

            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
            }

            if level_name not in level_map:
                self.logger.info(f"Invalid level: {level_name}. Use DEBUG, INFO, WARNING, or ERROR")
                return

            level = level_map[level_name]

            # Set log level for specified category
            if category == "prompt":
                self.prompt_logger.setLevel(level)
                print(f"[Loglevel] Prompt logs set to {level_name}")
            elif category == "http":
                logging.getLogger("openai").setLevel(level)
                logging.getLogger("httpx").setLevel(level)
                logging.getLogger("httpcore").setLevel(level)
                print(f"[Loglevel] HTTP logs set to {level_name}")
            elif category == "langchain":
                self.langchain_logger.setLevel(level)
                print(f"[Loglevel] LangChain logs set to {level_name}")
            elif category == "all":
                self.prompt_logger.setLevel(level)
                logging.getLogger("openai").setLevel(level)
                logging.getLogger("httpx").setLevel(level)
                logging.getLogger("httpcore").setLevel(level)
                self.langchain_logger.setLevel(level)
                print(f"[Loglevel] All categories set to {level_name}")
            else:
                print(f"[Loglevel] Unknown category: {category}. Use prompt, http, langchain, or all")

        else:
            self.logger.info(f"Unknown command: {command}. Available: /history, /clear, /fullhistorylog, /debug, /loglevel")

    def run(self) -> None:
        """Run the REPL loop."""
        print("CLI LLM PoC - Type your messages (Ctrl-C to exit)")
        print("=" * 50)

        # Log config on startup
        config = self.llm_service.config_loader.get_config()
        config_str = json.dumps(config, indent=2)
        self.logger.info(f"Startup config:\n{config_str}")

        while True:
            try:
                # Check for hot reload before each turn
                config_reloaded, template_reloaded = self.llm_service.check_hot_reload()

                if config_reloaded or template_reloaded:
                    reloaded_items = []
                    if config_reloaded:
                        reloaded_items.append("config")
                    if template_reloaded:
                        reloaded_items.append("template")
                    print(f"[Config reloaded: {', '.join(reloaded_items)}]")

                # Get user input
                user_input = self.prompt_session.prompt("> ")

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    self.handle_command(user_input)
                    continue

                # Send message and get response
                try:
                    response = self.llm_service.send_message(
                        user_input=user_input,
                        session_id=self.session_id,
                        log_full_history=self.log_full_history
                    )

                    print(f"\n{response}\n")

                except Exception as e:
                    self.logger.error(f"Error calling API: {e}")
                    print(f"Error calling API: {e}\n")

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                sys.exit(0)
            except EOFError:
                print("\n\nGoodbye!")
                sys.exit(0)


def main():
    """Entry point."""
    cli = REPLCLI()
    cli.run()


if __name__ == "__main__":
    main()
