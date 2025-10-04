"""
Core LLM service for handling chat interactions.

This module contains the business logic for:
- Building messages with conversation history
- Calling LLM APIs
- Managing session memory
- Config and template rendering
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage


class OpenRouterClient:
    """Client for OpenRouter API using LangChain's ChatOpenAI."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = None  # Will be initialized per request with model config

    def chat_completion(self, model: str, messages: List[BaseMessage], **kwargs) -> str:
        """
        Send chat completion request to OpenRouter via LangChain.

        Args:
            model: Model identifier (e.g., anthropic/claude-3.5-sonnet)
            messages: List of LangChain message objects
            **kwargs: Additional API parameters (temperature, max_tokens, etc.)

        Returns:
            Response content from the model

        Raises:
            Exception: On API errors
        """
        # Initialize ChatOpenAI with current config
        client = ChatOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            model=model,
            **kwargs
        )

        # Invoke the model
        response = client.invoke(messages)

        return response.content


class LLMService:
    """
    Core service for LLM interactions.

    This class handles all business logic including:
    - Message construction with history
    - Template rendering
    - API calls
    - Session memory management
    """

    def __init__(
        self,
        config_loader,
        prompt_builder,
        session_memory,
        api_key: str,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize LLM service.

        Args:
            config_loader: ConfigLoader instance
            prompt_builder: PromptBuilder instance
            session_memory: SessionMemory instance
            api_key: OpenRouter API key
            logger: Optional logger instance
        """
        self.config_loader = config_loader
        self.prompt_builder = prompt_builder
        self.session_memory = session_memory
        self.client = OpenRouterClient(api_key)
        # Use app.prompt logger category for prompt/config logging
        self.logger = logger or logging.getLogger("app.prompt")

    def check_hot_reload(self) -> tuple[bool, bool]:
        """
        Check and reload config/template if modified.

        Returns:
            Tuple of (config_reloaded, template_reloaded)
        """
        config_reloaded, _ = self.config_loader.check_and_reload()
        template_reloaded, _ = self.prompt_builder.check_and_reload()

        if config_reloaded:
            config = self.config_loader.get_config()
            config_str = json.dumps(config, indent=2)
            self.logger.info(f"Config reloaded:\n{config_str}")

        return config_reloaded, template_reloaded

    def build_messages(self, user_input: str, session_id: str) -> List[BaseMessage]:
        """
        Build messages list including system prompt and conversation history.

        Args:
            user_input: Current user input
            session_id: Session identifier

        Returns:
            List of LangChain message objects
        """
        config = self.config_loader.get_config()
        messages = []

        # Add system prompt if configured
        system_prompt = config.get("system_prompt", "")
        if system_prompt:
            rendered_system = self.prompt_builder.render(
                user_input=user_input,
                config=config
            )
            messages.append(SystemMessage(content=rendered_system))

        # Add conversation history (LangChain messages are already in correct format)
        history = self.session_memory.get_session(session_id)
        messages.extend(history.messages_list)

        # Add current user input
        messages.append(HumanMessage(content=user_input))

        return messages

    def build_api_params(self) -> tuple[str, Dict[str, Any]]:
        """
        Build API call parameters from config.

        Returns:
            Tuple of (model, kwargs) where kwargs are additional API parameters
        """
        config = self.config_loader.get_config()

        # Extract model separately
        model = config["model"]

        # Build kwargs for ChatOpenAI from config
        # Skip non-API params like system_prompt and model
        skip_keys = {"system_prompt", "model"}
        kwargs = {}
        for key, value in config.items():
            if key not in skip_keys:
                kwargs[key] = value

        return model, kwargs

    def _messages_to_dict(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """Convert LangChain messages to dict format for logging."""
        result = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                result.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                result.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                result.append({"role": "assistant", "content": msg.content})
        return result

    def send_message(
        self,
        user_input: str,
        session_id: str,
        log_full_history: bool = False
    ) -> str:
        """
        Send a message and get response.

        Args:
            user_input: User's message
            session_id: Session identifier
            log_full_history: Whether to log full conversation history

        Returns:
            Model's response
        """
        # Build messages with history
        messages = self.build_messages(user_input, session_id)

        # Build API parameters
        model, kwargs = self.build_api_params()

        # Log inference call details
        if log_full_history:
            # Log complete API call with all parameters and full history
            messages_dict = self._messages_to_dict(messages)
            api_call = {
                "model": model,
                **kwargs,
                "messages": messages_dict
            }
            api_call_str = json.dumps(api_call, indent=2)
            self.logger.info(f"API call (full with history):\n{api_call_str}")
        else:
            # Log only current turn's constructed prompt
            config = self.config_loader.get_config()
            current_turn = []

            # Add system prompt if configured
            system_prompt = config.get("system_prompt", "")
            if system_prompt:
                rendered_system = self.prompt_builder.render(
                    user_input=user_input,
                    config=config
                )
                current_turn.append(SystemMessage(content=rendered_system))

            # Add current user input (allow template injection)
            rendered_user = self.prompt_builder.render_user(
                user_input=user_input,
                config=config
            )
            current_turn.append(HumanMessage(content=rendered_user))

            # Log current turn with API parameters
            current_turn_dict = self._messages_to_dict(current_turn)
            api_call = {
                "model": model,
                **kwargs,
                "messages": current_turn_dict
            }
            api_call_str = json.dumps(api_call, indent=2)
            self.logger.info(f"API call (current turn):\n{api_call_str}")

        # Call API
        response = self.client.chat_completion(model=model, messages=messages, **kwargs)

        # Save to memory
        history = self.session_memory.get_session(session_id)
        history.add_message(HumanMessage(content=user_input))
        history.add_message(AIMessage(content=response))

        return response

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of message dictionaries with 'type' and 'content'
        """
        history = self.session_memory.get_session(session_id)
        return [
            {"type": msg.type, "content": msg.content}
            for msg in history.messages_list
        ]

    def clear_history(self, session_id: str) -> None:
        """
        Clear conversation history for a session.

        Args:
            session_id: Session identifier
        """
        self.session_memory.clear_session(session_id)
