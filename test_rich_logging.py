#!/usr/bin/env python3
"""
Test script to demonstrate Rich logging enhancements in INPUT phase.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set a dummy API key for testing
os.environ["OPENROUTER_API_KEY"] = "test_key_for_demo"

# Initialize core components
from core.config_loader import ConfigLoader
from core.prompt_builder import PromptBuilder
from core.logger import init_logger, LogManager
from adapters.cli_ptk import REPLCLI

base_dir = Path(__file__).parent

# Initialize logger at DEBUG level to see Rich enhancements
log_file = base_dir / "logs" / "test.log"
init_logger(
    log_level=logging.DEBUG,
    log_file=str(log_file),
    shell_output=True,
    print_log_init=True,
)

# Initialize LogManager and set prompt logging to DEBUG
log_manager = LogManager()
log_manager.set_level("prompt", logging.DEBUG)

config_loader = ConfigLoader(base_dir / "config" / "config.yaml")
prompt_builder = PromptBuilder(base_dir / "templates" / "prompt.jinja")

# Create CLI instance
cli = REPLCLI(config_loader, prompt_builder, "test_key", log_manager)

print("\n" + "="*80)
print("TESTING RICH LOGGING ENHANCEMENTS IN INPUT PHASE")
print("="*80)

# Test 1: Process regular message input
print("\n1. Testing regular message input processing:")
result = cli.process_user_input("Hello, how are you today?")
print(f"Result: {result}")

# Test 2: Process command input
print("\n2. Testing command input processing:")
result = cli.process_user_input("/history")
print(f"Result: {result}")

# Test 3: Process empty input
print("\n3. Testing empty input processing:")
result = cli.process_user_input("   ")
print(f"Result: {result}")

# Test 4: Process input with whitespace
print("\n4. Testing input with whitespace:")
result = cli.process_user_input("  What is the weather like?  ")
print(f"Result: {result}")

# Test 5: Test command handling with Rich logging
print("\n5. Testing command handling with Rich logging:")
cli.handle_command("/loglevel status")

print("\n6. Testing unknown command:")
cli.handle_command("/unknown")

print("\n" + "="*80)
print("RICH LOGGING ENHANCEMENT TEST COMPLETED")
print("="*80)