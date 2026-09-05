"""
evaluation/models.py

Pydantic domain models for benchmark evaluation data, metric scorecards,
confusion matrices, and machine-readable evaluation reports.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class PhysicalReferenceExpectation(BaseModel):
    file: str
    line_number: int
    record_id: str
    utr: Optional[str] = None


class BenchmarkCase(BaseModel):
    transaction_id: str
    order_id: Optional[str] = None
    expected_diagnosis: str
    expected_primary_exception: Optional[str] = None
    expected_severity: str
    expected_status: str
    expected_chain_completeness: bool
    expected_orphan_state: bool
    expected_missing_records: List[str] = Field(default_factory=list)
    expected_gross_cents: Optional[str] = None
    expected_net_cents: Optional[str] = None
    expected_ledger_cents: Optional[str] = None
    physical_references: Dict[str, PhysicalReferenceExpectation] = Field(default_factory=dict)


class CaseEvaluationResult(BaseModel):
    transaction_id: str
    passed: bool
    diagnosis_match: bool
    exception_match: bool
    severity_match: bool
    status_match: bool
    chain_completeness_match: bool
    orphan_state_match: bool
    missing_records_match: bool
    references_match: bool
    monetary_match: bool
    veo_integrity_valid: bool
    actual_diagnosis: Optional[str] = None
    actual_primary_exception: Optional[str] = None
    actual_severity: Optional[str] = None
    actual_status: Optional[str] = None
    errors: List[str] = Field(default_factory=list)


class MetricScore(BaseModel):
    tp: int = 0
    fp: int = 0
    fn: int = 0
    precision: float = 1.0
    recall: float = 1.0
    f1: float = 1.0
    support: int = 0


class ConfusionMatrix(BaseModel):
    labels: List[str]
    matrix: Dict[str, Dict[str, int]]  # expected_label -> predicted_label -> count


class DeterministicMetrics(BaseModel):
    total_cases: int
    passed_cases: int
    accuracy: float
    diagnosis_macro_f1: float
    per_class_diagnosis: Dict[str, MetricScore]
    exception_metrics: Dict[str, MetricScore]
    severity_metrics: Dict[str, MetricScore]
    status_metrics: Dict[str, MetricScore]
    missing_record_metrics: Dict[str, MetricScore]
    reference_accuracy: float
    monetary_accuracy: float
    veo_structural_validity: float
    diagnosis_confusion_matrix: ConfusionMatrix
    severity_confusion_matrix: ConfusionMatrix


class AISafetyMetrics(BaseModel):
    total_ai_cases: int
    valid_grounded_cases: int
    validator_rejected_cases: int
    fallback_enforced_cases: int
    unsupported_claims_detected: int
    fabricated_identifiers_detected: int
    numeric_violations_detected: int
    temporal_violations_detected: int
    epistemic_violations_detected: int
    grounding_compliance_rate: float
    validation_detection_rate: float
    unsafe_claim_escape_rate: float  # Target: 0.0%
    fallback_safety_rate: float      # Target: 100.0%


class ConversationMetrics(BaseModel):
    total_turns_evaluated: int
    epistemic_invariance_rate: float
    history_budget_compliance_rate: float
    cross_context_leakage_rate: float  # Target: 0.0%


class APIMetrics(BaseModel):
    endpoints_evaluated: int
    all_endpoints_healthy: bool
    parity_mismatches: int
    date_filter_accuracy: float


class EvaluationThresholds(BaseModel):
    min_diagnosis_accuracy: float = 0.98
    min_exception_f1: float = 0.98
    min_status_accuracy: float = 0.98
    min_severity_accuracy: float = 0.98
    min_reference_accuracy: float = 1.00
    min_monetary_accuracy: float = 1.00
    min_veo_structural_validity: float = 1.00
    max_unsafe_claim_escape_rate: float = 0.00
    max_cross_context_leakage_rate: float = 0.00
    min_api_parity: float = 1.00


class EvaluationSummary(BaseModel):
    benchmark_version: str
    dataset_hashes: Dict[str, str]
    timestamp: str
    runtime_seconds: float
    deterministic: DeterministicMetrics
    ai_safety: AISafetyMetrics
    conversation: ConversationMetrics
    api: APIMetrics
    thresholds: EvaluationThresholds
    passed_all_thresholds: bool
    failed_cases: List[CaseEvaluationResult] = Field(default_factory=list)
