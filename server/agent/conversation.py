"""
server/agent/conversation.py

Session manager for PS-8 Conversational Follow-up Q&A (Phase 11).
Maintains bounded in-memory conversation contexts, enforces context isolation across transactions,
and bounds message history budgets to prevent context dilution while keeping VEO authoritative.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from server.models.conversation import ConversationContext, ChatMessage, MessageRole
from server.validation.models import ResponseValidationResult

logger = logging.getLogger("settlement_qa_agent.conversation")

# Maximum message turns retained in conversational memory
MAX_CONVERSATION_MESSAGES = 10


class ConversationManager:
    """
    Manages conversational investigation sessions.
    Thread-safe in-memory store bounding history and guaranteeing context isolation.
    """

    def __init__(self, max_messages: int = MAX_CONVERSATION_MESSAGES):
        self._max_messages = max_messages
        self._conversations: Dict[str, ConversationContext] = {}

    def get_or_create(
        self,
        conversation_id: Optional[str],
        transaction_id: str,
        investigation_id: str,
    ) -> ConversationContext:
        """
        Retrieves existing conversation or creates a new one.
        CRITICAL: Enforces Context Isolation! If an existing conversation_id is passed
        but its transaction_id differs from the active transaction_id, the conversation
        is automatically reset to the new transaction to prevent cross-transaction leakage.
        """
        if conversation_id and conversation_id in self._conversations:
            conv = self._conversations[conversation_id]
            # Context Isolation check
            if conv.transaction_id == transaction_id:
                return conv
            else:
                logger.info(
                    f"Context switch detected for {conversation_id}: "
                    f"previous transaction '{conv.transaction_id}' != new transaction '{transaction_id}'. "
                    f"Re-initializing conversation for '{transaction_id}'."
                )

        new_id = conversation_id or f"conv_{uuid4().hex[:12]}"
        new_conv = ConversationContext(
            conversation_id=new_id,
            transaction_id=transaction_id,
            investigation_id=investigation_id,
            messages=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._conversations[new_id] = new_conv
        return new_conv

    def get(self, conversation_id: str) -> Optional[ConversationContext]:
        """Retrieve conversation by ID if exists."""
        return self._conversations.get(conversation_id)

    def get_history(self, conversation_id: str) -> List[ChatMessage]:
        """Retrieve ordered chat messages for conversation."""
        conv = self._conversations.get(conversation_id)
        return list(conv.messages) if conv else []

    def add_user_message(self, conversation_id: str, content: str) -> ChatMessage:
        """Appends a user message to the conversation."""
        conv = self._conversations.get(conversation_id)
        if not conv:
            raise ValueError(f"Conversation '{conversation_id}' not found.")

        msg = ChatMessage(
            role=MessageRole.USER,
            content=content.strip(),
            timestamp=datetime.now(timezone.utc),
            validated=True,
            llm_used=False,
            is_fallback=False,
        )

        new_messages = list(conv.messages) + [msg]
        if len(new_messages) > self._max_messages:
            new_messages = new_messages[-self._max_messages:]

        updated_conv = conv.model_copy(
            update={
                "messages": new_messages,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._conversations[conversation_id] = updated_conv
        return msg

    def add_assistant_message(
        self,
        conversation_id: str,
        content: str,
        validated: bool = True,
        llm_used: bool = False,
        is_fallback: bool = False,
        validation_result: Optional[ResponseValidationResult] = None,
    ) -> ChatMessage:
        """Appends an assistant answer to the conversation."""
        conv = self._conversations.get(conversation_id)
        if not conv:
            raise ValueError(f"Conversation '{conversation_id}' not found.")

        msg = ChatMessage(
            role=MessageRole.ASSISTANT,
            content=content.strip(),
            timestamp=datetime.now(timezone.utc),
            validated=validated,
            llm_used=llm_used,
            is_fallback=is_fallback,
            validation_result=validation_result,
        )

        new_messages = list(conv.messages) + [msg]
        if len(new_messages) > self._max_messages:
            new_messages = new_messages[-self._max_messages:]

        updated_conv = conv.model_copy(
            update={
                "messages": new_messages,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._conversations[conversation_id] = updated_conv
        return msg

    def reset(self, conversation_id: str) -> bool:
        """Clears conversation messages while keeping session alive."""
        conv = self._conversations.get(conversation_id)
        if not conv:
            return False

        updated_conv = conv.model_copy(
            update={
                "messages": [],
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._conversations[conversation_id] = updated_conv
        return True

    def delete(self, conversation_id: str) -> bool:
        """Completely removes a conversation from memory."""
        return self._conversations.pop(conversation_id, None) is not None
