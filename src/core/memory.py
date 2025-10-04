from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage
from typing import List, Dict


class InMemoryChatHistory(BaseChatMessageHistory):
    """In-memory chat message history for session management."""

    def __init__(self):
        self.messages: List[BaseMessage] = []

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the chat history."""
        self.messages.append(message)

    def clear(self) -> None:
        """Clear all messages from history."""
        self.messages = []

    @property
    def messages_list(self) -> List[BaseMessage]:
        """Get all messages."""
        return self.messages


class SessionMemory:
    """Manages multiple chat sessions with in-memory history."""

    def __init__(self):
        self.sessions: Dict[str, InMemoryChatHistory] = {}

    def get_session(self, session_id: str) -> InMemoryChatHistory:
        """
        Get or create a chat history for a session.

        Args:
            session_id: Unique identifier for the session

        Returns:
            InMemoryChatHistory instance for the session
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = InMemoryChatHistory()
        return self.sessions[session_id]

    def clear_session(self, session_id: str) -> None:
        """Clear history for a specific session."""
        if session_id in self.sessions:
            self.sessions[session_id].clear()

    def delete_session(self, session_id: str) -> None:
        """Delete a session entirely."""
        if session_id in self.sessions:
            del self.sessions[session_id]
