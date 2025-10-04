#!/usr/bin/env python3
"""
One Core launcher - routes to different UI adapters.

Usage:
    python main.py [adapter]

Adapters:
    cli     - CLI REPL interface (default)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for required API key
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("Error: OPENROUTER_API_KEY environment variable not set")
    print("Please add it to your .env file")
    sys.exit(1)

# Initialize core components (shared across all adapters)
from core.config_loader import ConfigLoader
from core.prompt_builder import PromptBuilder

base_dir = Path(__file__).parent
config_loader = ConfigLoader(base_dir / "config" / "config.yaml")
prompt_builder = PromptBuilder(base_dir / "templates" / "prompt.jinja")

# Parse command line argument (default to "cli")
adapter = sys.argv[1] if len(sys.argv) > 1 else "cli"

# Route to appropriate adapter
if adapter == "cli":
    from adapters.cli_ptk import run_repl
    run_repl(config_loader, prompt_builder, api_key)
else:
    print(f"Error: Unknown adapter '{adapter}'")
    print("Available adapters: cli")
    sys.exit(1)
