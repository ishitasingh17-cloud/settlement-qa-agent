# PS-8 Settlement Q&A Agent — Benchmark Evaluation Scorecard

**Benchmark Version:** `1.0.0`  
**Evaluation Timestamp:** `2026-09-06T12:53:55.985195+00:00`  
**Total Runtime:** `0.24s`  
**Overall Benchmark Status:** **PASSED (100% OF THRESHOLDS MET)**

---

## 1. Executive Summary

This quantitative evaluation independently measures the deterministic investigation engine, AI safety boundaries, conversational context isolation, and public API parity for the PS-8 Settlement Q&A Agent.

- **Total Dataset Evaluated:** 101 distinct transactions across Gateway, Bank, and Ledger CSVs.
- **Deterministic Accuracy:** **100.00%** (101/101 cases matching independently frozen ground truth).
- **Physical Reference Provenance:** **100.00%** bit-for-bit match on 1-based CSV line numbers, source file paths, and entity primary keys.
- **Monetary Accuracy:** **100.00%** exact Decimal comparison without floating-point arithmetic.
- **AI Safety / Unsafe Claim Escape Rate:** **0.00%** (0 out of 18 adversarial poisoned attacks bypassed the Phase 9 validator).
- **Cross-Investigation Leakage:** **0.00%** (zero cross-transaction data leakage across multi-turn sessions).
- **API Multi-Layer Parity:** **0 mismatches** across Direct Engine, Investigation Service, REST API, and Exception Dashboard.

---

## 2. Threshold Scorecard

| Evaluation Metric | Measured Value | Threshold Target | Status |
| :--- | :---: | :---: | :---: |
| Deterministic Diagnosis Accuracy | 100.00% | >= 98.00% | PASS |
| Diagnosis Macro F1 | 1.0000 | >= 0.9800 | PASS |
| Physical Reference Provenance Accuracy | 100.00% | 100.00% | PASS |
| Zero Float Monetary Fidelity | 100.00% | 100.00% | PASS |
| VEO Structural Completeness | 100.00% | 100.00% | PASS |
| Unsafe Financial Claim Escape Rate | 0.00% | 0.00% | PASS |
| Fallback Safety Enforcement Rate | 100.00% | 100.00% | PASS |
| Cross-Investigation Context Leakage Rate | 0.00% | 0.00% | PASS |
| Multi-Layer API Parity Mismatches | 0 | 0 | PASS |
| Exception Dashboard Date Filter Accuracy | 100.00% | 100.00% | PASS |

---

## 3. Deterministic Diagnosis Evaluation

### 3.1 Macro Metrics
- **Evaluated Cases:** 101
- **Correct Diagnoses:** 101
- **Accuracy:** 100.00%
- **Macro F1:** 1.0000

### 3.2 Diagnosis Confusion Matrix
| Expected \ Predicted | SUCCESSFULLY_SETTLED | MISSING_BANK_RECORD | BANK_REJECTED | MISSING_LEDGER_RECORD | CONFLICTING_EVIDENCE | INSUFFICIENT_EVIDENCE | Total |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SUCCESSFULLY_SETTLED** | 84 | 0 | 0 | 0 | 0 | 0 | 84 |
| **MISSING_BANK_RECORD** | 0 | 11 | 0 | 0 | 0 | 0 | 11 |
| **BANK_REJECTED** | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| **MISSING_LEDGER_RECORD** | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| **CONFLICTING_EVIDENCE** | 0 | 0 | 0 | 0 | 3 | 0 | 3 |
| **INSUFFICIENT_EVIDENCE** | 0 | 0 | 0 | 0 | 0 | 1 | 1 |

---

## 4. Exception Classification Metrics

| Exception Code | TP | FP | FN | Precision | Recall | F1 | Support |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `ERR_MISSING_BANK` | 11 | 0 | 0 | 100.00% | 100.00% | 1.0000 | 11 |
| `ERR_BANK_REJECTION` | 1 | 0 | 0 | 100.00% | 100.00% | 1.0000 | 1 |
| `ERR_MISSING_LEDGER` | 1 | 0 | 0 | 100.00% | 100.00% | 1.0000 | 1 |
| `ERR_CONFLICTING_EVIDENCE` | 3 | 0 | 0 | 100.00% | 100.00% | 1.0000 | 3 |
| `ERR_MISSING_GATEWAY` | 1 | 0 | 0 | 100.00% | 100.00% | 1.0000 | 1 |

---

## 5. Severity & Status Accuracy

### 5.1 Severity Confusion Matrix
| Expected \ Predicted | NONE | HIGH | CRITICAL | Total |
| :--- | :---: | :---: | :---: | :---: |
| **NONE** | 84 | 0 | 0 | 84 |
| **HIGH** | 0 | 13 | 0 | 13 |
| **CRITICAL** | 0 | 0 | 4 | 4 |

---

## 6. AI Grounding, Safety & Validator Metrics

- **Total AI Cases Evaluated:** 24
- **Valid Grounded Responses (PASS):** 6 (100% valid acceptance)
- **Adversarial / Poisoned Responses (REJECT):** 18
- **Fallback Enforcement Rate:** 100.00%
- **Unsafe Financial Claim Escape Rate:** **0.00%** (Target: 0.00%)
- **Violations Caught by Phase 9 Validator:**
  - Unsupported Causal Claims Detected: `6`
  - Fabricated Identifiers Detected: `3`
  - Numeric & Amount Violations Detected: `2`
  - Temporal & Future Arrival Claims Detected: `3`
  - Epistemic Status Violations Detected: `0`

---

## 7. Conversational Follow-Up & Context Isolation

- **Turns Evaluated:** 6
- **Epistemic Invariance Rate:** 100.00% (Refusal to confirm unrecorded causes)
- **History Budget Compliance:** 100.00% (Sliding window strictly bounded at <= 10 turns)
- **Cross-Investigation Context Leakage Rate:** **0.00%** (Absolute zero fact leakage between transactions)

---

## 8. API Layer & Exception Dashboard Evaluation

- **Endpoints Evaluated:** 8
- **All Endpoints Healthy:** Yes (200 OK / Controlled Envelopes)
- **Multi-Layer Parity Mismatches:** 0 (Direct Engine == Service == REST API)
- **Date Filter Accuracy:** 100.00% (Verified 2026-09-01, 2026-09-02, empty dates, and 400 Bad Request error envelopes)

---

## 9. Failure Analysis

- **Total Failed Cases:** 0
