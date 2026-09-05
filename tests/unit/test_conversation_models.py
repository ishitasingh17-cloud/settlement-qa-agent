"""
tests/unit/test_conversation_models.py

Unit tests for Phase 11 conversational models and ConversationManager.
Verifies message schemas, bounded sliding-window history, context isolation,
and session reset semantics.
"""

import pytest
from datetime import datetime, timezone
from server.models.conversation import ChatMessage, MessageRole, ConversationContext
from server.agent.conversation import ConversationManager


def test_chat_message_schema():
    """Verify ChatMessage initialization and validation."""
    msg = ChatMessage(
        role=MessageRole.USER,
        content="What was the settlement amount?",
    )
    assert msg.role == MessageRole.USER
    assert msg.content == "What was the settlement amount?"
    assert len(msg.message_id) > 0
    assert isinstance(msg.timestamp, datetime)
    assert msg.validated is True
    assert msg.validation_result is None


def test_conversation_context_sliding_window():
    """Verify sliding window bounds message history to max_messages."""
    manager = ConversationManager(max_messages=6)
    ctx = manager.get_or_create(
        conversation_id=None,
        transaction_id="pay_Gz8x1001",
        investigation_id="veo_pay_Gz8x1001",
    )
    conv_id = ctx.conversation_id
    assert len(manager.get_history(conv_id)) == 0

    # Add 8 messages (4 exchanges)
    for i in range(8):
        if i % 2 == 0:
            manager.add_user_message(conv_id, f"Message {i}")
        else:
            manager.add_assistant_message(conv_id, f"Message {i}")

    # Bounded to max_messages = 6
    history = manager.get_history(conv_id)
    assert len(history) == 6
    assert history[0].content == "Message 2"
    assert history[-1].content == "Message 7"


def test_conversation_manager_lifecycle():
    """Verify ConversationManager create, get, add turn, and reset."""
    manager = ConversationManager(max_messages=10)

    # 1. Create session
    ctx = manager.get_or_create(
        conversation_id=None,
        transaction_id="pay_Gz8x1001",
        investigation_id="veo_pay_Gz8x1001",
    )
    conv_id = ctx.conversation_id
    assert conv_id.startswith("conv_")
    assert ctx.transaction_id == "pay_Gz8x1001"
    assert len(manager.get_history(conv_id)) == 0

    # 2. Add user and assistant turns
    u_msg = manager.add_user_message(conv_id, "What is the status?")
    assert u_msg.role == MessageRole.USER
    assert u_msg.content == "What is the status?"

    a_msg = manager.add_assistant_message(
        conv_id,
        "Settlement is complete.",
        validated=True,
    )
    assert a_msg.role == MessageRole.ASSISTANT
    assert a_msg.content == "Settlement is complete."

    # 3. Retrieve history
    history = manager.get_history(conv_id)
    assert len(history) == 2
    assert history[0].role == MessageRole.USER
    assert history[1].role == MessageRole.ASSISTANT

    # 4. Explicit reset
    reset_ok = manager.reset(conv_id)
    assert reset_ok is True
    assert manager.get_history(conv_id) == []


def test_conversation_manager_context_isolation_across_transactions():
    """
    CRITICAL INVARIANT: Context isolation.
    Switching to a different transaction ID automatically resets or creates a new context,
    preventing historical facts from leaking from Transaction A into Transaction B.
    """
    manager = ConversationManager()

    # Session on Transaction A
    ctx_a = manager.get_or_create(
        conversation_id=None,
        transaction_id="pay_Gz8x1001",
        investigation_id="veo_pay_Gz8x1001",
    )
    conv_id = ctx_a.conversation_id
    manager.add_user_message(conv_id, "What was the gross amount for 1001?")
    manager.add_assistant_message(conv_id, "The gross amount was INR 4500.00.")

    assert len(manager.get_history(conv_id)) == 2

    # Requesting same conv_id with Transaction B MUST isolate/reset session
    ctx_b = manager.get_or_create(
        conversation_id=conv_id,
        transaction_id="pay_Gz8x1042",
        investigation_id="veo_pay_Gz8x1042",
    )
    assert ctx_b.transaction_id == "pay_Gz8x1042"
    # History must be cleared for the new transaction
    assert len(manager.get_history(conv_id)) == 0

