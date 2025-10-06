#!/usr/bin/env python3
"""
Test script to demonstrate Rich logging enhancements in message building.
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
from core.llm_service import LLMService
from core.memory import SessionMemory

base_dir = Path(__file__).parent

# Initialize logger at DEBUG level to see Rich enhancements
log_file = base_dir / "logs" / "test_message_building.log"
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
session_memory = SessionMemory()

# Create LLM service instance
llm_service = LLMService(
    config_loader=config_loader,
    prompt_builder=prompt_builder,
    session_memory=session_memory,
    api_key="test_key",
    logger=logging.getLogger("app.prompt")
)

print("\n" + "="*80)
print("TESTING RICH LOGGING ENHANCEMENTS IN MESSAGE BUILDING")
print("="*80)

# Test 1: Build messages for first interaction (no history)
print("\n1. Testing message building for first interaction (no history):")
messages = llm_service.build_messages("What is the capital of France?", "test_session")
print(f"Built {len(messages)} messages")

# Test 2: Add some history and build messages again
print("\n2. Adding history and testing message building:")
from langchain_core.messages import HumanMessage, AIMessage

# Simulate some conversation history
history = session_memory.get_session("test_session")
history.add_message(HumanMessage(content="Hello, how are you?"))
history.add_message(AIMessage(content="I'm doing well, thank you! How can I help you today?"))
history.add_message(HumanMessage(content="What's the weather like?"))
history.add_message(AIMessage(content="I don't have access to real-time weather data, but I can help you find weather information if you tell me your location."))

# Now build messages with history
messages = llm_service.build_messages("Can you tell me about Paris?", "test_session")
print(f"Built {len(messages)} messages with history")

print("\n" + "="*80)
print("MESSAGE BUILDING RICH LOGGING TEST COMPLETED")
print("="*80)