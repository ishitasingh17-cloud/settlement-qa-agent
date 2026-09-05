from pathlib import Path
import pytest

from evaluation.ground_truth import load_benchmark_cases, load_benchmark_ground_truth, get_ground_truth_path
from evaluation.models import BenchmarkCase


def test_ground_truth_file_exists():
    path = get_ground_truth_path()
    assert path.exists(), f"Benchmark ground truth file missing: {path}"


def test_ground_truth_case_count_and_completeness():
    cases = load_benchmark_cases()
    assert len(cases) == 101, f"Expected exactly 101 benchmark cases, got {len(cases)}"
    
    tx_ids = set()
    for case in cases:
        assert isinstance(case, BenchmarkCase)
        assert case.transaction_id.startswith("pay_")
        assert case.transaction_id not in tx_ids, f"Duplicate transaction ID: {case.transaction_id}"
        tx_ids.add(case.transaction_id)
        assert case.expected_diagnosis in [
            "SUCCESSFULLY_SETTLED",
            "MISSING_BANK_RECORD",
            "MISSING_LEDGER_RECORD",
            "BANK_REJECTED",
            "CONFLICTING_EVIDENCE",
            "INSUFFICIENT_EVIDENCE",
        ]
        assert case.expected_status in ["RESOLVED", "EXCEPTION", "INSUFFICIENT_DATA"]
        assert case.expected_severity in ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_ground_truth_distribution():
    cases = load_benchmark_cases()
    diagnoses = {}
    for case in cases:
        diagnoses[case.expected_diagnosis] = diagnoses.get(case.expected_diagnosis, 0) + 1
        
    assert diagnoses.get("SUCCESSFULLY_SETTLED") == 84
    assert diagnoses.get("MISSING_BANK_RECORD") == 11
    assert diagnoses.get("MISSING_LEDGER_RECORD") == 1
    assert diagnoses.get("BANK_REJECTED") == 1
    assert diagnoses.get("CONFLICTING_EVIDENCE") == 3
    assert diagnoses.get("INSUFFICIENT_EVIDENCE") == 1


def test_ground_truth_lookup_by_tx():
    cases = load_benchmark_cases()
    by_tx = {c.transaction_id: c for c in cases}
    case = by_tx.get("pay_Gz8x1001")
    assert case is not None
    assert case.transaction_id == "pay_Gz8x1001"
    assert case.expected_diagnosis == "SUCCESSFULLY_SETTLED"
    assert case.expected_status == "RESOLVED"
    assert case.expected_severity == "NONE"
