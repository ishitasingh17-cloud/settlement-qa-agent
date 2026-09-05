# PS-8: Settlement Q&A Agent for Fintech Support

[![FastAPI](https://img.shields.io/badge/FastAPI-1.0.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg?style=flat&logo=React&logoColor=black)](https://reactjs.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2.12-E92063.svg?style=flat&logo=Pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v3.4-38B2AC.svg?style=flat&logo=TailwindCSS&logoColor=white)](https://tailwindcss.com/)
[![Tests](https://img.shields.io/badge/Pytest-246%20Passed-brightgreen.svg)]()
[![Benchmark](https://img.shields.io/badge/Benchmark-100%25%20Accuracy-blue.svg)]()
[![Safety](https://img.shields.io/badge/AI%20Escape%20Rate-0.00%25-success.svg)]()

An autonomous, deterministically-grounded transaction settlement investigation and operational support assistant for digital payment platforms.

---

## 1. System Overview & Core Differentiator

In digital payment platforms, support teams spend thousands of hours investigating delayed or missing settlements across three isolated data silos:
1. **Payment Gateway Records:** Transaction authorizations, captures, processing fees, and order IDs.
2. **Bank Settlement Records:** Nodal clearing entries, UTR numbers, settlement dates, and failure codes.
3. **Internal Accounting Ledgers:** Double-entry journal vouchers, account postings, and hold tags.

### The Central Problem with Naive AI
When general-purpose LLMs are asked *"Why wasn't my transaction settled?"*, they hallucinate plausible but dangerous falsehoods: inventing non-existent UTRs, guessing bank failure codes ("insufficient funds"), or promising speculative future settlement dates.

### Our Solution: The Strict Trust Boundary

```text
CANONICAL RAW FINANCIAL DATA (Immutable CSVs)
                   ↓
 DETERMINISTIC INVESTIGATION ENGINE (Trace, Reconcile, 11-State Taxonomy)
                   ↓
 VERIFIED EVIDENCE PACK (VEO — SOLE FINANCIAL AUTHORITY)
                   ↓
 AI SETTLEMENT ANALYST (Prompt embedding VEO; dual-channel synthesis)
                   ↓
 ALGORITHMIC RESPONSE VALIDATOR (Phase 9 — Fails closed on violation)
                   ↓
 SAFE VERIFIED EXPLANATION or DETERMINISTIC FALLBACK
                   ↓
 OPERATOR COCKPIT (React UI, Follow-Up Chat, Exception Dashboard)
```

> **Core Axiom:** *"Deterministic code establishes financial truth. AI explains verified evidence."*

* The LLM **never** determines settlement status, calculates amounts, invents bank failure reasons, or accesses unverified tools.
* Every AI response is audited by an independent algorithmic validator for exact numeric matching, whitelisted identifiers, causal consistency, and epistemic honesty.
* If AI providers are unavailable, timeout, or generate unsupported claims, the system **fails closed** to a deterministic fallback template derived directly from the VEO.

---

## 2. Quickstart & Runbook

### 2.1 Prerequisites
* **Python 3.10+** (Python 3.11–3.14 supported)
* **Node.js v18+** & **npm**

### 2.2 Preflight Environment Check
Verify your environment, dependencies, and raw dataset hashes in one command:
```bash
python scripts/verify_environment.py
```

### 2.3 Backend Setup & Startup
```bash
# 1. Install backend dependencies
pip install -r requirements.txt

# 2. (Optional) Configure environment variables
# Copy template and add optional Gemini or Groq API keys:
cp .env.example .env

# 3. Start the FastAPI backend server
python scripts/start_backend.py
# Or directly:
# python -m server.main
```
* **API Documentation (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Health & Diagnostics:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 2.4 Frontend Setup & Startup
```bash
# In the client/ directory:
cd client
npm install
npm run dev
```
* **Cockpit Workspace UI:** [http://localhost:5173](http://localhost:5173)

### 2.5 Automated End-to-End Smoke Test
Run the deterministic end-to-end smoke test validating the complete system in ~0.3s:
```bash
python scripts/smoke_test.py
```

### 2.6 Run Full Automated Test Suite
```bash
python -m pytest tests/ -v
# 246 / 246 tests passing across unit, integration, and evaluation suites
```

### 2.7 Run Quantitative Benchmark Evaluation
```bash
python scripts/run_eval.py
# Runs 101-case ground truth evaluation, AI safety harness, and generates:
# - evaluation/results.json
# - evaluation/report.md
```

---

## 3. Canonical Demo Scenarios for Judges

The application comes pre-loaded with **6 Canonical Scenarios** demonstrating the complete spectrum of settlement outcomes:

| Scenario | Identifier | Expected Diagnosis | Key Capabilities Demonstrated |
| :--- | :--- | :--- | :--- |
| **SC-01** | `pay_Gz8x1001` | `SUCCESSFULLY_SETTLED` | Complete 3-system trace, Gross vs Net reconciliation, valid UTR, dual-channel explanation. |
| **SC-02** | `pay_Gz8x1000` | `MISSING_BANK_RECORD` | In-flight nodal settlement delay, honest `UNKNOWN` representation, missing bank clearing record. |
| **SC-03** | `pay_Gz8x1038` | `MISSING_LEDGER_RECORD` | Bank rail cleared with valid UTR, internal accounting ledger entry omitted. |
| **SC-04** | `pay_Gz8x1042` | `BANK_REJECTED` | Explicit clearing rejection returned by nodal clearing bank. |
| **SC-05** | `pay_Gz8x1052` | `CONFLICTING_EVIDENCE` | Critical cross-system status contradiction detected; system refuses to manufacture certainty. |
| **SC-06** | `pay_Gz8x1100` | `INSUFFICIENT_EVIDENCE` | Orphan bank and ledger record without gateway anchor; confidence downgraded to LOW. |

### Suggested 5-Minute Judge Walkthrough Flow
1. **Open the Cockpit UI** (`http://localhost:5173`).
2. **Run SC-01 (`pay_Gz8x1001`):** Click the "Clean Settlement" scenario pill on the sidebar. Observe the 3-column system inspector, the reference chain graph, the lifecycle timeline, and the verified AI explanation.
3. **Ask a Follow-Up Question:** In the bottom follow-up chat, ask *"Was this payment settled?"*. Notice the response is grounded in the active VEO.
4. **Demonstrate Context Isolation:** Click scenario **SC-05 (`pay_Gz8x1052`)**. Ask *"Why is this transaction flagged?"*. Verify that zero facts or figures from SC-01 leak into this new investigation.
5. **Open the Exception Dashboard:** Switch to the "Exceptions" view on the top header. View the 17 actionable exceptions across the 101-transaction dataset. Apply date filter `2026-09-01` (5 exceptions).
6. **Drill Down:** Click "Investigate" on any exception row to seamlessly return to the investigation workspace with automatic context reset.
7. **Inspect System Diagnostics:** Click the green "Online (200 OK)" badge in the top right to view live environment diagnostics and trust boundary guarantees.

---

## 4. Benchmark Evaluation Scorecard (Phase 13 Baseline)

```text
================================================================================
PS-8 SETTLEMENT Q&A AGENT — QUANTITATIVE BENCHMARK EVALUATION
================================================================================
[DETERMINISTIC ACCURACY] Evaluated: 101 | Passed: 101 | Accuracy: 100.00% | Macro F1: 1.0000
[REFERENCE PROVENANCE]   Accuracy: 100.00%
[MONETARY FIDELITY]      Accuracy: 100.00%
[VEO COMPLETENESS]       Accuracy: 100.00%
[AI SAFETY BOUNDARIES]   Total: 24 | Valid: 6 | Rejected: 18 | Escape Rate: 0.00%
[CONTEXT ISOLATION]      Leakage Rate: 0.00% | Epistemic Invariance: 100.00%
[API & DASHBOARD]        Endpoints: 8 | Parity Mismatches: 0 | Date Filter Acc: 100.00%
[BENCHMARK RESULT]       >>> PASS <<< (Runtime: 0.24s)
================================================================================
```

---

## 5. Environment & Resilience Configuration

The application is engineered to function out of the box with zero external dependencies using its deterministic fallback engine. External LLM providers are completely optional:

```bash
# .env Configuration (Optional)
PORT=8000
HOST=127.0.0.1
ENVIRONMENT=development

# Optional AI Providers:
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### Provider Failover Matrix
* **Gemini Configured:** Used as primary LLM provider.
* **Gemini Fails / Rate-limited:** Seamlessly fails over to Groq.
* **No Keys Configured / Offline:** Transparently activates **Deterministic Fallback Engine** (`llm_used=False`). Zero application degradation.
* **AI Hallucination / Prompt Injection:** Algorithmic validator rejects response and substitutes deterministic VEO fallback template.

---

## 6. Project Architecture & Phase Roadmap

| Phase | Description | Status | Verification Result |
| :---: | :--- | :---: | :--- |
| **0** | Repository & Documentation Foundation | **COMPLETE** | 6 Authoritative Specs under `docs/` |
| **1** | Synthetic Financial Data Generation | **COMPLETE** | 101 canonical cases, frozen SHA-256 hashes |
| **2** | Ingestion & Schema Normalization | **COMPLETE** | Zero Float Parsing, 1-based physical line numbers |
| **3** | Reference Chaining & Trace Engine | **COMPLETE** | Multi-hop graph traversal across 5 identifier types |
| **4** | Deterministic Financial Reconciliation | **COMPLETE** | 6-audit Gross/Net and status reconciliation |
| **5** | Settlement Diagnosis & Exception Taxonomy | **COMPLETE** | Controlled 11-state priority decision tree |
| **6** | Verified Evidence Pack (VEO) Contract | **COMPLETE** | Strongly typed immutable audit envelope |
| **7** | Backend Investigation REST API | **COMPLETE** | FastAPI REST endpoints with typed error envelopes |
| **8** | AI Settlement Analyst Layer | **COMPLETE** | Bounded prompt synthesis with dual channels |
| **9** | Algorithmic Response Validation Engine | **COMPLETE** | Zero unsafe escapes across 24 golden test cases |
| **10**| Investigation UI & Cockpit Experience | **COMPLETE** | React + Tailwind dark glass cockpit UI |
| **11**| Grounded Conversational Follow-Up Q&A | **COMPLETE** | Bounded history budget, 0% cross-context leakage |
| **12**| Operational Exception Dashboard UI | **COMPLETE** | Macro KPI cards, multi-system date filtering, drill-down |
| **13**| Quantitative Benchmark Evaluation Harness | **COMPLETE** | 101/101 accuracy, 1.0000 macro F1, results.json |
| **14**| Integration, Reliability & Demo Hardening | **COMPLETE** | 246 tests passing, smoke test, runbook, verified ready |

---

## 7. Known Design Principles & Limitations

1. **Local Sandbox Execution:** Designed for local execution and hackathon evaluation; external production database persistence (PostgreSQL/Redis) is deliberately replaced with fast in-memory indexing over frozen canonical CSVs.
2. **Zero Float Arithmetic:** Financial figures throughout the codebase are represented strictly as `Decimal` or integer cents to avoid IEEE 754 precision loss.
3. **Anti-Cheating Decoupling:** Production server code (`server/`) never imports evaluation scripts or ground truth datasets.
