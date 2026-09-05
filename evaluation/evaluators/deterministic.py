"""
evaluation/evaluators/deterministic.py

Evaluates the deterministic investigation pipeline against independently established ground truth:
- Diagnosis accuracy, multi-class Precision/Recall/F1
- Exception classification metrics
- Severity and Status accuracy
- Physical reference provenance (1-based line numbers, file paths)
- Zero float monetary fidelity
- VEO structural completeness
- Generation of real confusion matrices
"""

from decimal import Decimal
from typing import List, Dict, Tuple, Any
from evaluation.models import (
    BenchmarkCase,
    CaseEvaluationResult,
    MetricScore,
    ConfusionMatrix,
    DeterministicMetrics,
)
from server.api.dependencies import (
    get_data_store,
    get_trace_engine,
    get_evidence_builder,
)
from server.evidence.models import VerifiedEvidencePack


def evaluate_deterministic_dataset(cases: List[BenchmarkCase]) -> Tuple[DeterministicMetrics, List[CaseEvaluationResult]]:
    data_store = get_data_store()
    trace_engine = get_trace_engine()
    evidence_builder = get_evidence_builder()

    case_results: List[CaseEvaluationResult] = []
    
    # Trackers for confusion matrices
    diagnosis_labels = [
        "SUCCESSFULLY_SETTLED",
        "MISSING_BANK_RECORD",
        "BANK_REJECTED",
        "MISSING_LEDGER_RECORD",
        "CONFLICTING_EVIDENCE",
        "INSUFFICIENT_EVIDENCE",
    ]
    diag_matrix = {exp: {pred: 0 for pred in diagnosis_labels} for exp in diagnosis_labels}

    severity_labels = ["NONE", "HIGH", "CRITICAL"]
    sev_matrix = {exp: {pred: 0 for pred in severity_labels} for exp in severity_labels}

    status_labels = ["SETTLED", "EXCEPTION", "INSUFFICIENT_DATA"]

    # Counts for per-class metrics
    diag_counts = {lbl: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for lbl in diagnosis_labels}
    exc_labels = [
        "ERR_MISSING_BANK",
        "ERR_BANK_REJECTION",
        "ERR_MISSING_LEDGER",
        "ERR_CONFLICTING_EVIDENCE",
        "ERR_MISSING_GATEWAY",
    ]
    exc_counts = {lbl: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for lbl in exc_labels}
    sev_counts = {lbl: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for lbl in severity_labels}
    stat_counts = {lbl: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for lbl in status_labels}

    missing_sys_labels = ["GATEWAY", "BANK", "LEDGER"]
    missing_sys_counts = {lbl: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for lbl in missing_sys_labels}

    ref_correct_count = 0
    ref_total_checked = 0
    monetary_correct_count = 0
    monetary_total_checked = 0
    veo_valid_count = 0

    for case in cases:
        txn_id = case.transaction_id
        errors = []

        # 1. Execute deterministic pipeline
        trace = trace_engine.trace(txn_id)
        veo = evidence_builder.build(trace)

        actual_diag = veo.diagnosis.value
        actual_sev = veo.severity.value
        actual_stat = veo.status.value
        actual_primary_exc = veo.exceptions[0].exception_type.value if veo.exceptions else None

        # 2. Evaluate diagnosis
        diag_match = (actual_diag == case.expected_diagnosis)
        if not diag_match:
            errors.append(f"Diagnosis mismatch: expected {case.expected_diagnosis}, got {actual_diag}")
        
        if case.expected_diagnosis in diag_matrix and actual_diag in diag_matrix[case.expected_diagnosis]:
            diag_matrix[case.expected_diagnosis][actual_diag] += 1
        
        for lbl in diagnosis_labels:
            if case.expected_diagnosis == lbl:
                diag_counts[lbl]["support"] += 1
                if actual_diag == lbl:
                    diag_counts[lbl]["tp"] += 1
                else:
                    diag_counts[lbl]["fn"] += 1
            else:
                if actual_diag == lbl:
                    diag_counts[lbl]["fp"] += 1

        # 3. Evaluate primary exception
        exc_match = (actual_primary_exc == case.expected_primary_exception)
        if not exc_match:
            errors.append(f"Exception mismatch: expected {case.expected_primary_exception}, got {actual_primary_exc}")

        for lbl in exc_labels:
            is_expected = (case.expected_primary_exception == lbl)
            is_actual = (actual_primary_exc == lbl)
            if is_expected:
                exc_counts[lbl]["support"] += 1
                if is_actual:
                    exc_counts[lbl]["tp"] += 1
                else:
                    exc_counts[lbl]["fn"] += 1
            elif is_actual:
                exc_counts[lbl]["fp"] += 1

        # 4. Evaluate severity
        sev_match = (actual_sev == case.expected_severity)
        if not sev_match:
            errors.append(f"Severity mismatch: expected {case.expected_severity}, got {actual_sev}")

        if case.expected_severity in sev_matrix and actual_sev in sev_matrix[case.expected_severity]:
            sev_matrix[case.expected_severity][actual_sev] += 1

        for lbl in severity_labels:
            if case.expected_severity == lbl:
                sev_counts[lbl]["support"] += 1
                if actual_sev == lbl:
                    sev_counts[lbl]["tp"] += 1
                else:
                    sev_counts[lbl]["fn"] += 1
            elif actual_sev == lbl:
                sev_counts[lbl]["fp"] += 1

        # 5. Evaluate status
        stat_match = (actual_stat == case.expected_status)
        if not stat_match:
            errors.append(f"Status mismatch: expected {case.expected_status}, got {actual_stat}")

        for lbl in status_labels:
            if case.expected_status == lbl:
                stat_counts[lbl]["support"] += 1
                if actual_stat == lbl:
                    stat_counts[lbl]["tp"] += 1
                else:
                    stat_counts[lbl]["fn"] += 1
            elif actual_stat == lbl:
                stat_counts[lbl]["fp"] += 1

        # 6. Evaluate chain completeness & orphan state
        chain_completeness_match = (veo.is_complete_chain == case.expected_chain_completeness)
        if not chain_completeness_match:
            errors.append(f"Chain completeness mismatch: expected {case.expected_chain_completeness}, got {veo.is_complete_chain}")

        orphan_state_match = (veo.is_orphan == case.expected_orphan_state)
        if not orphan_state_match:
            errors.append(f"Orphan state mismatch: expected {case.expected_orphan_state}, got {veo.is_orphan}")

        # 7. Evaluate missing records
        actual_missing = set(veo.missing_records)
        expected_missing = set(case.expected_missing_records)
        missing_match = (actual_missing == expected_missing)
        if not missing_match:
            errors.append(f"Missing records mismatch: expected {expected_missing}, got {actual_missing}")

        for lbl in missing_sys_labels:
            is_exp = (lbl in expected_missing)
            is_act = (lbl in actual_missing)
            if is_exp:
                missing_sys_counts[lbl]["support"] += 1
                if is_act:
                    missing_sys_counts[lbl]["tp"] += 1
                else:
                    missing_sys_counts[lbl]["fn"] += 1
            elif is_act:
                missing_sys_counts[lbl]["fp"] += 1

        # 8. Evaluate physical references (1-based line number, file name, record id)
        case_ref_pass = True
        for sys_name, exp_ref in case.physical_references.items():
            ref_total_checked += 1
            if sys_name == "GATEWAY":
                act_rec = veo.gateway
            elif sys_name == "BANK":
                act_rec = veo.bank
            elif sys_name == "LEDGER":
                act_rec = veo.ledger
            else:
                act_rec = None

            if act_rec is None or act_rec.provenance is None:
                case_ref_pass = False
                errors.append(f"Physical reference missing for {sys_name}")
                continue

            prov = act_rec.provenance
            # Check file match
            file_match = prov.source_file.replace("\\", "/").endswith(exp_ref.file)
            line_match = (prov.source_row_index == exp_ref.line_number)
            id_match = True
            if sys_name == "GATEWAY":
                id_match = (act_rec.transaction_id == exp_ref.record_id)
            elif sys_name == "BANK":
                id_match = (act_rec.settlement_id == exp_ref.record_id)
            elif sys_name == "LEDGER":
                id_match = (act_rec.ledger_entry_id == exp_ref.record_id)

            if file_match and line_match and id_match:
                ref_correct_count += 1
            else:
                case_ref_pass = False
                errors.append(
                    f"Provenance mismatch for {sys_name}: expected ({exp_ref.file}, line {exp_ref.line_number}, {exp_ref.record_id}), "
                    f"got ({prov.source_file}, line {prov.source_row_index})"
                )

        # 9. Evaluate monetary fidelity (Exact Decimal comparison, zero float)
        case_monetary_pass = True
        if case.expected_gross_cents is not None:
            monetary_total_checked += 1
            expected_gross = Decimal(case.expected_gross_cents)
            if veo.gateway and veo.gateway.gross_amount == expected_gross:
                monetary_correct_count += 1
            else:
                case_monetary_pass = False
                errors.append(f"Gross amount mismatch: expected {expected_gross}, got {veo.gateway.gross_amount if veo.gateway else None}")

        if case.expected_net_cents is not None:
            monetary_total_checked += 1
            expected_net = Decimal(case.expected_net_cents)
            if veo.bank and veo.bank.net_settlement_amount == expected_net:
                monetary_correct_count += 1
            else:
                case_monetary_pass = False
                errors.append(f"Net amount mismatch: expected {expected_net}, got {veo.bank.net_settlement_amount if veo.bank else None}")

        if case.expected_ledger_cents is not None:
            monetary_total_checked += 1
            expected_led = Decimal(case.expected_ledger_cents)
            if veo.ledger and veo.ledger.ledger_amount == expected_led:
                monetary_correct_count += 1
            else:
                case_monetary_pass = False
                errors.append(f"Ledger amount mismatch: expected {expected_led}, got {veo.ledger.ledger_amount if veo.ledger else None}")

        # 10. Evaluate VEO structural completeness
        veo_valid = bool(
            veo.transaction_id
            and veo.veo_id
            and veo.integrity_hash
            and veo.diagnosis
            and veo.confidence
            and veo.severity
            and veo.status
            and veo.reconciliation
            and veo.timeline
            and veo.resolution_path
            and veo.epistemic_model
        )
        if veo_valid:
            veo_valid_count += 1
        else:
            errors.append("VEO structural validation failed: one or more required top-level attributes missing")

        case_passed = (
            diag_match
            and exc_match
            and sev_match
            and stat_match
            and chain_completeness_match
            and orphan_state_match
            and missing_match
            and case_ref_pass
            and case_monetary_pass
            and veo_valid
        )

        case_results.append(
            CaseEvaluationResult(
                transaction_id=txn_id,
                passed=case_passed,
                diagnosis_match=diag_match,
                exception_match=exc_match,
                severity_match=sev_match,
                status_match=stat_match,
                chain_completeness_match=chain_completeness_match,
                orphan_state_match=orphan_state_match,
                missing_records_match=missing_match,
                references_match=case_ref_pass,
                monetary_match=case_monetary_pass,
                veo_integrity_valid=veo_valid,
                actual_diagnosis=actual_diag,
                actual_primary_exception=actual_primary_exc,
                actual_severity=actual_sev,
                actual_status=actual_stat,
                errors=errors,
            )
        )

    # Compute metric scores
    def compute_scores(counts_dict: Dict[str, Dict[str, int]]) -> Dict[str, MetricScore]:
        scores = {}
        for lbl, c in counts_dict.items():
            tp = c["tp"]
            fp = c["fp"]
            fn = c["fn"]
            supp = c["support"]
            prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if supp == 0 else 0.0)
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
            scores[lbl] = MetricScore(
                tp=tp,
                fp=fp,
                fn=fn,
                precision=round(prec, 4),
                recall=round(rec, 4),
                f1=round(f1, 4),
                support=supp,
            )
        return scores

    per_class_diagnosis = compute_scores(diag_counts)
    exception_metrics = compute_scores(exc_counts)
    severity_metrics = compute_scores(sev_counts)
    status_metrics = compute_scores(stat_counts)
    missing_record_metrics = compute_scores(missing_sys_counts)

    # Compute macro F1 for diagnosis
    diag_f1_sum = sum(s.f1 for s in per_class_diagnosis.values())
    diag_macro_f1 = round(diag_f1_sum / len(per_class_diagnosis), 4)

    total_cases = len(cases)
    passed_cases = sum(1 for r in case_results if r.passed)
    accuracy = round(passed_cases / total_cases, 4)
    ref_accuracy = round(ref_correct_count / ref_total_checked, 4) if ref_total_checked > 0 else 1.0
    monetary_accuracy = round(monetary_correct_count / monetary_total_checked, 4) if monetary_total_checked > 0 else 1.0
    veo_validity = round(veo_valid_count / total_cases, 4)

    det_metrics = DeterministicMetrics(
        total_cases=total_cases,
        passed_cases=passed_cases,
        accuracy=accuracy,
        diagnosis_macro_f1=diag_macro_f1,
        per_class_diagnosis=per_class_diagnosis,
        exception_metrics=exception_metrics,
        severity_metrics=severity_metrics,
        status_metrics=status_metrics,
        missing_record_metrics=missing_record_metrics,
        reference_accuracy=ref_accuracy,
        monetary_accuracy=monetary_accuracy,
        veo_structural_validity=veo_validity,
        diagnosis_confusion_matrix=ConfusionMatrix(labels=diagnosis_labels, matrix=diag_matrix),
        severity_confusion_matrix=ConfusionMatrix(labels=severity_labels, matrix=sev_matrix),
    )

    return det_metrics, case_results
