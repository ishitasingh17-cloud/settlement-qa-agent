"""
evaluation/evaluators/conversation.py

Evaluates multi-turn conversational follow-up (Phase 11):
- Epistemic invariance across multi-turn dialogues
- History budget window enforcement (max 10 messages)
- Cross-investigation context isolation (0% leakage between transactions)
"""

import asyncio
from typing import List, Dict, Any
from evaluation.models import ConversationMetrics
from server.agent.conversation import ConversationManager
from server.api.service import InvestigationService
from server.api.dependencies import (
    get_data_store,
    get_trace_engine,
    get_evidence_builder,
    get_settlement_analyst,
    get_conversation_manager,
)


def evaluate_conversation() -> ConversationMetrics:
    conv_mgr = ConversationManager(max_messages=10)
    service = InvestigationService(
        data_store=get_data_store(),
        trace_engine=get_trace_engine(),
        evidence_builder=get_evidence_builder(),
        settlement_analyst=get_settlement_analyst(),
        conversation_manager=conv_mgr,
    )

    total_turns = 0
    epistemic_invariance_count = 0
    budget_compliance_count = 0
    leakage_count = 0

    # -------------------------------------------------------------
    c_id = None

    questions = [
        "What is the settlement status of this payment?",
        "What is the bank UTR reference number?",
        "Was there any ledger record posted?",
        "Did the customer get charged twice?",
        "Will another payout arrive tomorrow?",
    ]

    async def run_dialogue():
        nonlocal total_turns, epistemic_invariance_count, budget_compliance_count, c_id
        for q in questions:
            total_turns += 1
            resp = await service.ask_question(identifier="pay_Gz8x1001", question=q, conversation_id=c_id)
            c_id = resp.conversation_id

            # Check epistemic permanence: answer must not invent tomorrow arrival
            ans_text = (resp.answer or resp.internal_summary).lower()
            if "tomorrow" not in ans_text or "cannot confirm" in ans_text or "unrecorded" in ans_text:
                epistemic_invariance_count += 1

            # Check history budget window (<= 10 messages)
            hist = conv_mgr.get_history(c_id)
            if len(hist) <= 10:
                budget_compliance_count += 1

    asyncio.run(run_dialogue())

    # -------------------------------------------------------------
    # 2. Cross-Context Leakage Test (Transaction A -> Transaction B)
    # -------------------------------------------------------------
    # Session on Transaction A (pay_Gz8x1001: Amount 111358, UTR721609600)
    # Now switch directly to Transaction B (pay_Gz8x1042: Amount 11126, UTR242224154)
    async def run_leakage_test():
        nonlocal total_turns, leakage_count
        # User attempts to query using prior session ID but different transaction ID
        total_turns += 1
        resp_b = await service.ask_question(
            identifier="pay_Gz8x1042",
            question="What is the gross amount and UTR for this transaction?",
            conversation_id=c_id,  # Passing c_id from pay_Gz8x1001
        )

        b_text = (resp_b.answer or resp_b.internal_summary)
        # Verify ZERO facts from pay_Gz8x1001 leaked into pay_Gz8x1042
        leaked_a_amount = "111358" in b_text
        leaked_a_utr = "UTR721609600" in b_text
        leaked_a_id = "pay_Gz8x1001" in b_text

        if leaked_a_amount or leaked_a_utr or leaked_a_id:
            leakage_count += 1

    asyncio.run(run_leakage_test())

    epistemic_rate = round(epistemic_invariance_count / len(questions), 4)
    budget_rate = round(budget_compliance_count / len(questions), 4)
    leakage_rate = round(leakage_count / 1, 4)

    return ConversationMetrics(
        total_turns_evaluated=total_turns,
        epistemic_invariance_rate=epistemic_rate,
        history_budget_compliance_rate=budget_rate,
        cross_context_leakage_rate=leakage_rate,
    )
