"""
Example of how to extend LLMService with streaming support.

This shows the proposed streaming methods without modifying the original.
"""

from typing import Iterator, Generator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.llm_service import LLMService, OpenRouterClient
from langchain_openai import ChatOpenAI
import json


class OpenRouterClientStreaming(OpenRouterClient):
    """Extended client with streaming support."""

    def stream_completion(self, model: str, messages, **kwargs) -> Iterator[str]:
        """
        Stream chat completion from OpenRouter via LangChain.

        Args:
            model: Model identifier
            messages: List of LangChain message objects
            **kwargs: Additional API parameters

        Yields:
            Response content chunks from the model
        """
        # Initialize ChatOpenAI with streaming enabled
        client = ChatOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            model=model,
            streaming=True,  # Enable streaming
            **kwargs
        )

        # Stream the response
        for chunk in client.stream(messages):
            if chunk.content:
                yield chunk.content


class LLMServiceStreaming(LLMService):
    """Extended LLM service with streaming support."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace client with streaming version
        self.client = OpenRouterClientStreaming(self.client.api_key)

    def stream_message(
        self,
        user_input: str,
        session_id: str,
        log_full_history: bool = False
    ) -> Generator[str, None, str]:
        """
        Stream a message response.

        Args:
            user_input: User's message
            session_id: Session identifier
            log_full_history: Whether to log full conversation history

        Yields:
            Response chunks as they arrive

        Returns:
            Complete response after streaming finishes
        """
        # Build messages with history (same as send_message)
        messages = self.build_messages(user_input, session_id)

        # Build API parameters
        model, kwargs = self.build_api_params()

        # Log inference call details (same as send_message)
        if log_full_history:
            messages_dict = self._messages_to_dict(messages)
            api_call = {
                "model": model,
                **kwargs,
                "messages": messages_dict,
                "streaming": True
            }
            api_call_str = json.dumps(api_call, indent=2)
            self.logger.info(f"API call (streaming, full history):\n{api_call_str}")
        else:
            # Log only current turn
            config = self.config_loader.get_config()
            current_turn = []

            system_prompt = config.get("system_prompt", "")
            if system_prompt:
                rendered_system = self.prompt_builder.render(
                    user_input=user_input,
                    config=config
                )
                current_turn.append(SystemMessage(content=rendered_system))

            rendered_user = self.prompt_builder.render_user(
                user_input=user_input,
                config=config
            )
            current_turn.append(HumanMessage(content=rendered_user))

            current_turn_dict = self._messages_to_dict(current_turn)
            api_call = {
                "model": model,
                **kwargs,
                "messages": current_turn_dict,
                "streaming": True
            }
            api_call_str = json.dumps(api_call, indent=2)
            self.logger.info(f"API call (streaming, current turn):\n{api_call_str}")

        # Stream response and collect chunks
        chunks = []
        for chunk in self.client.stream_completion(model=model, messages=messages, **kwargs):
            chunks.append(chunk)
            yield chunk

        # Combine all chunks
        full_response = "".join(chunks)

        # Save to memory (after streaming completes)
        history = self.session_memory.get_session(session_id)
        history.add_message(HumanMessage(content=user_input))
        history.add_message(AIMessage(content=full_response))

        return full_response
