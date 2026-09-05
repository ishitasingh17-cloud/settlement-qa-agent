"""
evaluation/run.py

CLI executable for benchmark evaluation: python -m evaluation.run
Runs evaluation, prints formatted terminal scorecard, and exits with 0 or 1.
"""

import sys
from evaluation.runner import run_benchmark_evaluation


def main():
    print("================================================================================")
    print("PS-8 SETTLEMENT Q&A AGENT — QUANTITATIVE BENCHMARK EVALUATION")
    print("================================================================================")
    summary = run_benchmark_evaluation()

    det = summary.deterministic
    ai = summary.ai_safety
    conv = summary.conversation
    api = summary.api

    print(f"\n[DETERMINISTIC ACCURACY] Evaluated: {det.total_cases} | Passed: {det.passed_cases} | Accuracy: {det.accuracy:.2%} | Macro F1: {det.diagnosis_macro_f1:.4f}")
    print(f"[REFERENCE PROVENANCE]   Accuracy: {det.reference_accuracy:.2%}")
    print(f"[MONETARY FIDELITY]      Accuracy: {det.monetary_accuracy:.2%}")
    print(f"[VEO COMPLETENESS]       Accuracy: {det.veo_structural_validity:.2%}")
    print(f"[AI SAFETY BOUNDARIES]   Total: {ai.total_ai_cases} | Valid: {ai.valid_grounded_cases} | Rejected: {ai.validator_rejected_cases} | Escape Rate: {ai.unsafe_claim_escape_rate:.2%}")
    print(f"[CONTEXT ISOLATION]      Leakage Rate: {conv.cross_context_leakage_rate:.2%} | Epistemic Invariance: {conv.epistemic_invariance_rate:.2%}")
    print(f"[API & DASHBOARD]        Endpoints: {api.endpoints_evaluated} | Parity Mismatches: {api.parity_mismatches} | Date Filter Acc: {api.date_filter_accuracy:.2%}")
    print(f"\n[BENCHMARK RESULT]       {'>>> PASS <<<' if summary.passed_all_thresholds else '>>> FAIL <<<'}")
    print(f"[REPORTS GENERATED]      evaluation/results.json and evaluation/report.md (Runtime: {summary.runtime_seconds}s)")
    print("================================================================================")

    sys.exit(0 if summary.passed_all_thresholds else 1)


if __name__ == "__main__":
    main()
