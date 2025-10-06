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

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
import langchain

# Rich imports for beautiful CLI formatting
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.text import Text
from rich.status import Status
from rich.columns import Columns
from rich import box

# Import from core
from core.config_loader import ConfigLoader
from core.prompt_builder import PromptBuilder
from core.memory import SessionMemory
from core.llm_service import LLMService


class REPLCLI:
    """Main REPL CLI application."""

    def __init__(self, config_loader, prompt_builder, api_key, log_manager):
        """
        Initialize CLI REPL.

        Args:
            config_loader: ConfigLoader instance (for hot-reload)
            prompt_builder: PromptBuilder instance (for hot-reload)
            api_key: OpenRouter API key
            log_manager: LogManager instance (from core)
        """
        # Initialize Rich console for beautiful output
        self.console = Console()

        # Enable OpenAI SDK debug logging (shows raw HTTP requests/responses)
        os.environ["OPENAI_LOG"] = "debug"

        # Store log manager (initialized in launcher)
        self.log_manager = log_manager

        # Use prompt logger as main logger
        self.logger = logging.getLogger("app.prompt")

        # Store API key
        self.api_key = api_key

        # Initialize session memory (adapter-specific)
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
            # Dump full conversation history with Rich formatting
            history = self.llm_service.get_history(self.session_id)
            if not history:
                self.console.print(Panel("No conversation history yet", title="📜 History", border_style="yellow"))
                return

            # Create a table for conversation history
            table = Table(title="📜 Conversation History", box=box.ROUNDED)
            table.add_column("#", style="dim", width=4)
            table.add_column("Type", style="bold", width=10)
            table.add_column("Content", style="white")

            for i, msg in enumerate(history, 1):
                msg_type = msg['type']
                content = msg['content']
                
                # Truncate long content for table display
                if len(content) > 100:
                    content = content[:97] + "..."
                
                # Style based on message type
                if msg_type == "human":
                    type_style = "[bold blue]👤 Human[/bold blue]"
                elif msg_type == "ai":
                    type_style = "[bold green]🤖 AI[/bold green]"
                else:
                    type_style = f"[dim]{msg_type}[/dim]"
                
                table.add_row(str(i), type_style, content)

            self.console.print(table)
            self.console.print(f"[dim]Total messages: {len(history)}[/dim]")

        elif cmd == "/clear":
            # Clear conversation history
            self.llm_service.clear_history(self.session_id)
            self.console.print(Panel("🗑️  Conversation history cleared", border_style="green"))

        elif cmd == "/fullhistorylog":
            # Toggle full history logging mode
            self.log_full_history = not self.log_full_history
            status = "enabled" if self.log_full_history else "disabled"
            icon = "✅" if self.log_full_history else "❌"
            style = "green" if self.log_full_history else "red"
            self.console.print(Panel(f"{icon} Full history logging {status}", border_style=style))

        elif cmd == "/debug":
            # Toggle LangChain debug mode (shows internal processing)
            # Note: OpenAI SDK HTTP logging is always enabled at startup
            self.langchain_debug = not self.langchain_debug

            # Enable/disable LangChain's internal debug logging
            langchain.debug = self.langchain_debug
            langchain.verbose = self.langchain_debug

            status = "enabled" if self.langchain_debug else "disabled"
            icon = "🔍" if self.langchain_debug else "🔇"
            style = "cyan" if self.langchain_debug else "dim"
            
            panel_content = f"{icon} LangChain debug mode {status}"
            if self.langchain_debug:
                panel_content += "\n[dim]Will show LangChain internal processing[/dim]"
            else:
                panel_content += "\n[dim]HTTP request logging still active (set at startup)[/dim]"
            
            self.console.print(Panel(panel_content, title="Debug Mode", border_style=style))

        elif cmd.startswith("/loglevel"):
            # Change log level: /loglevel prompt INFO or /loglevel http DEBUG
            parts = command.split()

            # Show current status
            if len(parts) == 1 or (len(parts) == 2 and parts[1].lower() == "status"):
                # Get status from LogManager
                status = self.log_manager.get_status()

                # Create a table for log levels
                table = Table(title="📊 Current Log Levels", box=box.ROUNDED)
                table.add_column("Category", style="bold cyan", width=12)
                table.add_column("Level", style="bold", width=10)
                table.add_column("Description", style="dim")

                # Add root logger
                table.add_row("ROOT", status["root"], "auto-adjusts to lowest component")

                # Add component loggers
                components = self.log_manager.get_ui_components()
                for component, info in components.items():
                    current_level = status["components"].get(component, "N/A")
                    table.add_row(component, current_level, info["description"])

                self.console.print(table)
                self.console.print("[dim]Tip: Use '/loglevel --all' to see all active loggers[/dim]")
                return

            # Show all loggers (advanced mode)
            if len(parts) == 2 and parts[1] == "--all":
                all_loggers = self.log_manager.get_all_loggers()
                self.console.print(Panel(
                    f"[bold]All Active Loggers ({len(all_loggers)}):[/bold]\n\n" +
                    "\n".join(f"  • {logger}" for logger in all_loggers[:50]) +
                    (f"\n  ... and {len(all_loggers) - 50} more" if len(all_loggers) > 50 else ""),
                    title="🔍 Advanced Debug",
                    border_style="cyan"
                ))
                return

            if len(parts) < 2 or len(parts) > 3:
                # Build usage with dynamic component list
                components = self.log_manager.get_ui_components()
                component_list = ", ".join(components.keys()) + ", all"

                usage_panel = Panel(
                    "[bold]Usage:[/bold]\n"
                    "  /loglevel [category] [level]\n"
                    "  /loglevel status  (show current levels)\n"
                    "  /loglevel --all   (show all active loggers)\n\n"
                    f"[bold]Categories:[/bold] {component_list}\n"
                    "[bold]Levels:[/bold] DEBUG, INFO, WARNING, ERROR\n\n"
                    "[bold]Example:[/bold] /loglevel http DEBUG",
                    title="📋 Log Level Command",
                    border_style="yellow"
                )
                self.console.print(usage_panel)
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
                self.console.print(Panel(f"❌ Invalid level: {level_name}\nUse: DEBUG, INFO, WARNING, or ERROR",
                                       title="Error", border_style="red"))
                return

            level = level_map[level_name]

            # Use LogManager to set level (handles smart root adjustment)
            success, message = self.log_manager.set_level(category, level)

            if success:
                self.console.print(Panel(f"✅ {message}", border_style="green"))
            else:
                self.console.print(Panel(f"❌ {message}", title="Error", border_style="red"))

        else:
            available_commands = "/history, /clear, /fullhistorylog, /debug, /loglevel"
            self.console.print(Panel(f"❓ Unknown command: {command}\n\n[bold]Available commands:[/bold]\n{available_commands}", 
                                   title="Command Help", border_style="yellow"))

    def run(self) -> None:
        """Run the REPL loop."""
        # Beautiful startup welcome
        welcome_panel = Panel(
            "[bold blue]🤖 Personal Assistant - One Core[/bold blue]\n\n"
            "[dim]Type your messages to chat with the AI\n"
            "Use slash commands for special functions\n"
            "Press Ctrl-C to exit[/dim]",
            title="Welcome",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(welcome_panel)

        # Display startup config in a beautiful table
        config = self.llm_service.config_loader.get_config()
        
        config_table = Table(title="🔧 Configuration", box=box.ROUNDED)
        config_table.add_column("Setting", style="bold cyan", width=20)
        config_table.add_column("Value", style="white")
        
        for key, value in config.items():
            if isinstance(value, dict):
                value_str = json.dumps(value, indent=2)
            else:
                value_str = str(value)
            config_table.add_row(key, value_str)
        
        self.console.print(config_table)

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
                    
                    reload_text = f"🔄 Reloaded: {', '.join(reloaded_items)}"
                    self.console.print(Panel(reload_text, border_style="green"))

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
                    # Show thinking indicator
                    with self.console.status("[bold green]🤔 Thinking...", spinner="dots"):
                        response = self.llm_service.send_message(
                            user_input=user_input,
                            session_id=self.session_id,
                            log_full_history=self.log_full_history
                        )

                    # Display AI response in a beautiful panel with markdown
                    response_panel = Panel(
                        Markdown(response),
                        title="🤖 AI Response",
                        border_style="green",
                        padding=(1, 2)
                    )
                    self.console.print(response_panel)

                except Exception as e:
                    self.logger.error(f"Error calling API: {e}")
                    error_panel = Panel(
                        f"❌ Error calling API: {e}",
                        title="Error",
                        border_style="red"
                    )
                    self.console.print(error_panel)

            except KeyboardInterrupt:
                goodbye_panel = Panel(
                    "👋 Thanks for using Personal Assistant!\nGoodbye!",
                    title="Farewell",
                    border_style="blue"
                )
                self.console.print(goodbye_panel)
                sys.exit(0)
            except EOFError:
                goodbye_panel = Panel(
                    "👋 Thanks for using Personal Assistant!\nGoodbye!",
                    title="Farewell",
                    border_style="blue"
                )
                self.console.print(goodbye_panel)
                sys.exit(0)


def run_repl(config_loader, prompt_builder, api_key, log_manager):
    """
    Run the CLI REPL interface.

    Args:
        config_loader: ConfigLoader instance (for hot-reload)
        prompt_builder: PromptBuilder instance (for hot-reload)
        api_key: OpenRouter API key
        log_manager: LogManager instance (from core)
    """
    cli = REPLCLI(config_loader, prompt_builder, api_key, log_manager)
    cli.run()
