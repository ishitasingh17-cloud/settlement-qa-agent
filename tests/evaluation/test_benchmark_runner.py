from pathlib import Path
import pytest

from evaluation.runner import run_benchmark_evaluation
from evaluation.models import EvaluationSummary


def test_benchmark_runner_execution_and_thresholds():
    summary = run_benchmark_evaluation()
    
    assert isinstance(summary, EvaluationSummary)
    assert summary.passed_all_thresholds is True, f"Failed thresholds: {summary.thresholds}"
    
    # Assert deterministic metrics
    assert summary.deterministic.accuracy == 1.0
    assert summary.deterministic.diagnosis_macro_f1 == 1.0
    assert summary.deterministic.reference_accuracy == 1.0
    assert summary.deterministic.monetary_accuracy == 1.0
    assert summary.deterministic.veo_structural_validity == 1.0
    assert summary.deterministic.total_cases == 101
    
    # Assert AI safety metrics
    assert summary.ai_safety.unsafe_claim_escape_rate == 0.0
    assert summary.ai_safety.fallback_safety_rate == 1.0
    assert summary.ai_safety.total_ai_cases == 24
    assert summary.ai_safety.valid_grounded_cases == 6
    assert summary.ai_safety.validator_rejected_cases == 18
    
    # Assert conversation metrics
    assert summary.conversation.cross_context_leakage_rate == 0.0
    assert summary.conversation.epistemic_invariance_rate == 1.0
    assert summary.conversation.history_budget_compliance_rate == 1.0
    
    # Assert API parity metrics
    assert summary.api.parity_mismatches == 0
    assert summary.api.date_filter_accuracy == 1.0
    assert summary.api.endpoints_evaluated == 8
    assert summary.api.all_endpoints_healthy is True
