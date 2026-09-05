# Engineering Constitution & Non-Negotiable Rules (rules.md)

## Project: PS-8 — Settlement Q&A Agent for Fintech Support
**Document Version:** 1.0.0  
**Role:** Project Engineering Constitution  
**Authority:** Authoritative across all phases, developers, and AI agents  
**Core Motto:** *Simple architecture. Deterministic financial reasoning. Bounded AI. Explicit uncertainty. Testable behavior. No unnecessary complexity.*

---

## 1. Core Engineering Principle

The foundational engineering law of this codebase is:

> **Financial truth must be deterministic. AI may explain verified evidence but must never become the source of financial truth.**

### 1.1 The Required Unidirectional Data Pipeline

```text
Raw Data (CSV)
      ↓
Normalization & Decimal Casting
      ↓
Multi-Hop Reference Resolution
      ↓
Deterministic Reconciliation Engine
      ↓
Deterministic Diagnosis Engine (1 of 11 States)
      ↓
Epistemic Exception Detection (Known vs Inferred vs Unknown)
      ↓
Verified Evidence Pack (VEO JSON)
      ↓
AI Explanation Layer (Gemini / Groq)
      ↓
Algorithmic Response Validation
      ↓
Presentation Layer (React UI)
```

### 1.2 The Forbidden Pipeline
```text
Raw CSV / File ──► LLM ──► Financial Decision / Status / Math  [STRICTLY FORBIDDEN]
```

Under no circumstances may an LLM prompt ask:
* *"Did this transaction settle?"*
* *"What is the remaining balance?"*
* *"Is there an amount mismatch?"*
* *"Why did the bank fail this transfer?"* (unless quoting an explicit bank reason provided in the evidence pack)

---

## 2. Source-of-Truth Hierarchy

When components disagree or data is ambiguous, the following hierarchy strictly governs:

```text
1. Raw Synthetic Records          (Immutable source CSVs)
2. Normalized Records             (Typed Pydantic domain models, Decimal math)
3. Reconciliation Engine Results  (Algorithmic status, amount, and reference checks)
4. Diagnosis Engine Classification(Controlled 11-state priority decision tree)
5. Exception Engine Output        (Tri-state epistemic classification: Known/Inferred/Unknown)
6. Verified Evidence Pack (VEO)   (Immutable JSON snapshot passed to AI)
7. LLM Natural-Language Synthesis (Explanatory text layer)
8. UI Presentation Layer          (Visual DOM representation)
```

**Cardinal Invariant:** A lower-level component can NEVER contradict or override a higher-level component.
* If `bank.csv` records `bank_status = PENDING`, the LLM cannot state *"The bank failed the transfer"*.
* If `reconciler` flags `ERR_AMOUNT_MISMATCH` with variance `-₹350.00`, the UI or AI cannot report amounts as *"fully balanced"*.

---

## 3. Approved Technology Stack

To maintain hackathon velocity and eliminate operational fragility, only the technologies specified in `arch.md` are permitted:

### 3.1 Frontend
* **Core:** React 18 + Vite (JavaScript / JSX)
* **Styling:** Tailwind CSS (Utility-first, light theme tokens)
* **Icons:** Lucide React (`strokeWidth={1.75}`)
* **Data Visualization:** Recharts (Restricted strictly to the Exception Dashboard if needed; no gratuitous area charts)

### 3.2 Backend
* **Runtime:** Python 3.11+
* **Web Framework:** FastAPI (Asynchronous REST API, auto OpenAPI docs)
* **Data Modeling & Validation:** Pydantic v2
* **Data Ingestion & Manipulation:** Pandas + Python Standard Library (`csv`, `decimal`, `datetime`)

### 3.3 AI / LLM
* **Providers:** Google Gemini 1.5 Flash (via `google-generativeai`) OR Groq (`llama-3.1-70b-versatile` / `llama-3-8b`)
* **Mode:** Structured JSON Output (`response_format={"type": "json_object"}`)

### 3.4 Data & Storage
* **Format:** Flat CSV files (`data/gateway.csv`, `data/bank.csv`, `data/ledger.csv`) + JSON benchmark (`data/ground_truth.json`)
* **Execution:** In-memory Python hash maps (`dict` indexed by IDs) for sub-millisecond lookups

### 3.5 Testing
* **Test Runner:** Pytest + `httpx` (for FastAPI test client)

---

## 4. Library & Dependency Boundaries

### 4.1 Allowed Libraries
Only lightweight libraries that directly resolve an explicit PS-8 requirement may be introduced:
`fastapi`, `uvicorn`, `pydantic`, `pandas`, `google-generativeai`, `groq`, `python-dotenv`, `pytest`, `httpx`, `react`, `lucide-react`, `tailwindcss`.

### 4.2 Strictly Forbidden Infrastructure & Libraries
Do NOT add any of the following to `requirements.txt` or `package.json`:
* **NO Heavy AI Orchestration:** LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex.
* **NO Vector Databases:** Pinecone, Weaviate, Milvus, ChromaDB, Qdrant, FAISS.
* **NO Relational / NoSQL Databases:** PostgreSQL, MySQL, SQLite, MongoDB.
* **NO Distributed Infrastructure:** Redis, Celery, Kafka, RabbitMQ, ZeroMQ.
* **NO Container Orchestration:** Kubernetes, Helm, Docker Compose swarms (Local dev: single Python process + single Vite process).
* **NO Heavy UI Component Suites:** Material UI, Ant Design, Bootstrap, Chakra UI (Use pure Tailwind utility classes).

*Rationale:* The hackathon problem statement requires a transparent, reproducible deterministic reconciliation engine. Adding vector databases or distributed message queues introduces 500+ transitive dependencies, configuration debt, and network latency without solving any core fintech requirement.

---

## 5. No Framework Stacking

Do not incorporate multiple libraries that solve the exact same technical problem:
* **HTTP Clients:** Choose **Fetch API** or **Axios** in the frontend. Never bundle both.
* **State Management:** Use standard **React `useState` / `useContext`** hooks. Do NOT install Redux, Zustand, MobX, or Recoil for a single-page investigation console.
* **Data Handling:** Use **Pandas** for ingestion and native **Python `dict`** for indexing. Do NOT add Polars, Dask, or PyArrow.
* **Date Parsing:** Use Python native `datetime.fromisoformat()`. Do NOT add `moment.js` or `date-fns` unless native JS `Intl` proves insufficient.

---

## 6. AI Boundary Rules

The AI layer is an **untrusted, bounded translator**, not an autonomous agent.

### 6.1 What the AI MAY Do
* Translate the structured Verified Evidence Pack into concise, human-readable English.
* Generate a dual-channel output: an internal technical summary for support agents and a courteous script for merchants.
* Organize verified facts into explicit "Known Facts" and "Missing Information / Exceptions" lists.
* Answer contextual follow-up questions strictly using the evidence provided in the active investigation context.
* Explain why a specific settlement state was assigned based on the deterministic flags provided.

### 6.2 What the AI MUST NOT Do
* **NEVER** determine the transaction status, bank clearing status, or ledger status.
* **NEVER** calculate gross amounts, net amounts, fee deductions, or currency variances.
* **NEVER** invent or assume a bank failure reason when `bank.failure_reason` is null or missing.
* **NEVER** claim that missing data indicates a failure or success.
* **NEVER** invent mock transaction IDs, UTRs, or timestamps not present in the evidence pack.
* **NEVER** alter or round financial amounts passed to it.
* **NEVER** override the deterministic diagnosis provided by code.
* **NEVER** express certainty when the evidence pack marks confidence as `LOW` or lists unresolved exceptions.

---

## 7. Data Exposure to the LLM: Zero Raw CSV Dumps

* **Rule:** Never send raw CSV files, database dumps, or unparsed table rows to an LLM prompt.
* **Reasoning:** Raw dumps cause prompt bloat, token wastage, cross-tenant data leakage risks, and hallucinations caused by attention dispersion.
* **Protocol:** The backend must first isolate the target transaction, trace its reference chain across Gateway, Bank, and Ledger, execute reconciliation, package the single resulting Verified Evidence Pack (typically $< 1\text{ KB}$ of JSON), and pass ONLY that structured object to the LLM.

---

## 8. Structured AI Output Enforcement

Free-form, unstructured LLM responses are prohibited for investigation summaries. The AI service must enforce structured JSON output adhering to this contract:

```json
{
  "internal_summary": "String detailing cross-system alignment, fee math, and technical status",
  "merchant_friendly_response": "String containing safe, professional, copyable merchant communication",
  "known_facts": [
    "String fact 1 directly backed by data row",
    "String fact 2"
  ],
  "inferred_facts": [
    "String derived conclusion (e.g. net payout math)"
  ],
  "unknown_facts": [
    "String explicit data gap (e.g. bank completion timestamp absent)"
  ],
  "recommended_action": "String guidance for frontline support agent"
}
```

If the LLM returns invalid JSON or fails schema validation, the backend must discard the output and immediately substitute the deterministic fallback template.

---

## 9. AI System Prompting Rules

Every system prompt constructed for the LLM must enforce the following guardrails:
1. *"You are the explanation layer of a fintech reconciliation system. You have NO independent knowledge of financial events."*
2. *"You must answer solely based on the provided Verified Evidence Pack JSON."*
3. *"If an attribute is null, empty, or marked missing, you must explicitly state that the information is unavailable. You must NEVER fabricate a reason, technical error, or network drop."*
4. *"Do not alter numbers, dates, currency signs, or identifiers."*
5. *"Never tell the user that funds are guaranteed to arrive by a specific time unless an explicit SLA timestamp is present in the evidence."*

---

## 10. Honest Uncertainty & The Epistemic Model

The system must actively prioritize **Honest Uncertainty** over speculative completeness:
* It is a critical defect for the system to invent an explanation for a delayed payment.
* When evidence is incomplete (e.g., Bank file has no record of the batch), the diagnosis must be `MISSING_BANK_RECORD` or `INSUFFICIENT_EVIDENCE`, and the explanation must state: *"The bank has not provided a settlement record for this batch; the root cause of the delay cannot be determined from available data."*
* Every investigation must categorize findings into:
  * **KNOWN:** Directly supported by a row field.
  * **INFERRED:** Derived by code (e.g., Gross ₹5,000 - Fee ₹150 = Expected Net ₹4,850).
  * **UNKNOWN:** Explicitly absent from datasets (e.g., Missing bank UTR or null failure reason).

---

## 11. Deterministic Financial Math & Money Rules

### 11.1 Floating-Point Prohibition
* **Rule:** Never use standard Python floating-point numbers (`float`) or JavaScript IEEE 754 floats for monetary values, fee subtractions, or variance calculations.
* **Implementation:**
  * **Python Backend:** Always use `decimal.Decimal` with explicit string instantiation: `Decimal("5000.00") - Decimal("150.00") == Decimal("4850.00")`.
  * **Comparison Tolerance:** Amounts match if $\left|\text{Expected} - \text{Actual}\right| \le \text{Decimal}("0.01")$.
* **Formatting:** All monetary figures rendered in UI or API responses must be formatted with two decimal places and currency symbol (`₹4,850.00`).

---

## 12. Strict Identifier Disambiguation

Financial rails use distinct, non-interchangeable identifiers. Code and prompts must never conflate them:

| Identifier Key | System Origin | Format / Pattern | Role |
| :--- | :--- | :--- | :--- |
| `transaction_id` | Payment Gateway | `TXN_[0-9]{5}` | Primary customer checkout transaction ID |
| `order_id` | Merchant Platform | `ORD_[0-9]{5}` | Merchant's internal shopping cart order number |
| `gateway_reference`| Payment Processor | `GW_REF_[A-Z0-9]{8}` | Processor authorization token |
| `settlement_id` | Settlement Engine | `SET_[0-9]{5}` | Batch payout container grouping transactions |
| `utr` | Banking Clearing Network | `UTR[A-Z0-9]{11,22}` | Bank Unique Transaction Reference |
| `ledger_entry_id` | Accounting Ledger | `LED_[0-9]{6}` | Double-entry journal audit log ID |

**Rule:** Never assume `transaction_id == settlement_id == utr`. The Tracing Engine must explicitly perform graph hops to resolve links.

---

## 13. Immutability of Source Synthetic Data

* Synthetic CSV files (`data/gateway.csv`, `data/bank.csv`, `data/ledger.csv`) represent cold storage financial logs.
* The application runtime must treat them as **strictly read-only**.
* The server must never write, append, overwrite, or mutate source CSV files during an investigation or Q&A interaction.
* All normalization, indexing, and state associations must happen in volatile memory.

---

## 14. Ingestion & Data Validation Rules

1. **Header Verification:** During boot, `csv_loader.py` must verify that all required columns exist in each CSV. If a mandatory column is missing, the application must abort startup with a clear fatal error.
2. **Type Casting:** Strings must be cast to `Decimal`, `datetime`, or `Literal` enums immediately upon ingestion.
3. **Malformed Row Handling:** A corrupted row must be logged with its row number and skipped or marked unparseable. The ingestion engine must never crash the entire application due to a single bad row.
4. **Duplicate Key Check:** The loader must check for anomalous duplicate primary keys (`transaction_id` in Gateway, `utr` in Bank) and record them for reconciliation checks.

---

## 15. Error Handling & Graceful Degradation

### 15.1 The Iron Rule of Error Handling
```python
# STRICTLY FORBIDDEN
try:
    do_something()
except:
    pass
```
* Never swallow exceptions silently.
* Every exception must either be resolved cleanly, logged with context, or converted into a typed domain error.

### 15.2 Standard Error Classification Hierarchy
All API errors must return structured JSON matching this schema:
```json
{
  "error_code": "TRANSACTION_NOT_FOUND",
  "message": "Transaction 'TXN_99999' was not found in Gateway, Bank, or Ledger files.",
  "details": { "query": "TXN_99999" },
  "remediation": "Verify the ID or try one of the test IDs: TXN_10001, TXN_10482."
}
```

Standard error codes:
* `INVALID_QUERY_FORMAT`
* `TRANSACTION_NOT_FOUND`
* `BROKEN_REFERENCE_CHAIN`
* `DATA_INGESTION_ERROR`
* `LLM_SERVICE_UNAVAILABLE`
* `LLM_RESPONSE_VALIDATION_FAILED`

### 15.3 Graceful AI Degradation
If the LLM provider fails, times out (threshold: $4.0\text{ seconds}$), or exceeds quota:
1. Catch the exception in `server/agent/llm_client.py`.
2. Do **NOT** fail the HTTP request with a 500 error.
3. Inject the deterministic pre-compiled fallback explanation into the response.
4. Set `llm_used: false` and `explanation.validated: true` in the API envelope.
5. The UI displays the full investigation, timeline, and status cards with a subtle badge: `[Deterministic Mode]`.

---

## 16. Algorithmic Response Validation (Anti-Hallucination Guardrail)

Every natural-language string produced by the LLM must pass through `server/validation/response_validator.py` before being sent to the client:
1. **Amount Invariance Check:** Scans the generated text for currency amounts (e.g., regex `₹[\d,]+(\.\d{2})?`). If an amount appears in the AI text that does not exist in the Verified Evidence Pack (gross, fee, net, or variance), the response is **REJECTED**.
2. **Status Invariance Check:** If the VEO indicates `bank_status: PENDING`, but the AI text contains phrases like *"the bank rejected"*, *"payment was declined"*, or *"transfer failed"*, the response is **REJECTED**.
3. **Reason Invariance Check:** If `bank.failure_reason` is null, but the AI text asserts a specific failure cause (*"server timeout"*, *"insufficient balance"*), the response is **REJECTED**.
4. **Fallback Action:** Any rejected AI text is immediately replaced by the deterministic fallback template.

---

## 17. API & Architecture Boundaries

1. **Frontend Isolation:** The React frontend must never read raw CSV files, execute joins, or compute financial reconciliation rules. All business logic lives in the Python backend.
2. **Backend Modularity:**
   * `server/reconciliation/` and `server/diagnosis/` must NEVER import AI libraries (`google.generativeai` or `groq`). They must remain 100% pure Python.
   * `server/agent/` must NEVER query `data_store.py` or read CSV files. It receives ONLY the completed `VerifiedEvidencePack`.
3. **No God Files:** 
   * `server/main.py` is strictly for FastAPI route mounting, CORS middleware, and lifespan lifecycle hooks. It must not contain reconciliation algorithms or LLM prompt strings.

---

## 18. Controlled Enums & Canonical State Taxonomies

String literals scattered across the codebase are prohibited. Enums must be used for all domain states:

### 18.1 Canonical Settlement Diagnoses (Strict 11 States)
```python
class SettlementDiagnosis(str, Enum):
    SUCCESSFULLY_SETTLED = "SUCCESSFULLY_SETTLED"
    SETTLEMENT_PENDING = "SETTLEMENT_PENDING"
    GATEWAY_FAILED = "GATEWAY_FAILED"
    BANK_REJECTED = "BANK_REJECTED"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    MISSING_BANK_RECORD = "MISSING_BANK_RECORD"
    MISSING_LEDGER_RECORD = "MISSING_LEDGER_RECORD"
    REFERENCE_MISMATCH = "REFERENCE_MISMATCH"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
```

### 18.2 Canonical Discrepancy Codes
`ERR_STATUS_MISMATCH`, `ERR_AMOUNT_MISMATCH`, `ERR_MISSING_BANK`, `ERR_MISSING_LEDGER`, `ERR_MISSING_GATEWAY`, `ERR_REFERENCE_MISMATCH`, `ERR_DUPLICATE_RECORD`, `ERR_CONFLICTING_EVIDENCE`, `INFO_UNBATCHED`.

---

## 19. Security, Secrets & Environment Rules

1. **Zero Secret Commits:** Never commit API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) to Git.
2. **Environment Configuration:** All secrets must be loaded via `pydantic-settings` from `.env`. A complete `.env.example` must be maintained in the root directory.
3. **Sanitized Error Logs:** Server logs and client error toasts must never display API keys, authorization headers, internal server paths, or raw stack traces.
4. **Read-Only Application:** No endpoints may be created that support mutating payment states, executing bank payouts, or modifying ledgers.

---

## 20. Synthetic Data & Ground Truth Integrity

1. **100% Synthetic Guarantee:** Never introduce real customer names, genuine credit card numbers, or live banking account details.
2. **Oracle Immutability:** `data/ground_truth.json` is the authoritative benchmark oracle. 
3. **Prohibition on Metric Gaming:** Never alter `ground_truth.json` simply to make an evaluation script pass. If a test fails, fix the reconciliation logic or tracing engine in the code.

---

## 21. Testing Standards & Quality Gates

Before any phase is marked complete in `memory.md`, the following quality gates must be satisfied:
1. **Deterministic Unit Tests:** Pytest suite covering all 11 canonical settlement scenarios with 100% pass rate.
2. **Amount Variance Tests:** Unit tests verifying that fee math and float-free comparisons correctly catch discrepancies down to the exact cent/paisa.
3. **Anti-Hallucination Evaluation:** The evaluation script (`scripts/run_eval.py`) must verify that missing fields in ground truth are never asserted as known facts by the AI.
4. **Fast Execution:** The entire unit test suite must execute in under 10 seconds locally.

---

## 22. Code Style & Documentation Discipline

1. **Type Annotations:** All Python functions in `server/` must have complete type hints (`def trace(query: str) -> ResolvedChain:`).
2. **Docstrings & Comments:** Comments must document **WHY** a financial or business decision was made, not merely what the syntax does.
   * *Bad:* `# Check if status is pending`
   * *Good:* `# Bank pending status is not treated as a failure because processing SLAs permit up to 24h before clearing.`
3. **Clean Code:** No unused imports, no commented-out blocks of dead code, and no temporary debug `print()` statements in production paths (use Python's standard `logging` module).

---

## 23. Scope Control & The "No-Overengineering" Test

Before writing any new class, adding a dependency, or creating an abstraction layer, the engineer must answer:

> **"What explicit requirement in `prd.md` mandates this?"**

If the answer is *"it might be useful later"* or *"it makes the architecture look more enterprise-grade"*, **DO NOT BUILD IT.**

### Explicitly Excluded from MVP:
* Real payment gateway integrations (Stripe, Razorpay)
* Real banking protocols (Swift, ISO 20022, UPI switches)
* User authentication and Role-Based Access Control (RBAC)
* Webhook receivers or asynchronous task workers (Celery)
* Vector search, RAG pipelines, or document chunking
* Autonomous multi-agent coordination frameworks

---

## 24. Ten Non-Negotiable Commandments

1. **Never let the LLM determine financial truth.**
2. **Never invent, guess, or assume missing evidence.**
3. **Never hide uncertainty, missing records, or data contradictions.**
4. **Never hardcode API keys, secrets, or credentials.**
5. **Never silently swallow exceptions with bare `except: pass`.**
6. **Never duplicate financial reconciliation rules in the frontend.**
7. **Never introduce databases, message queues, or vector stores to this MVP.**
8. **Never alter ground truth data to artificially inflate evaluation scores.**
9. **Never treat a business data exception as an application software crash.**
10. **Never sacrifice financial correctness for an impressive-looking AI demo.**

---

> **Implementation Note:** This document has also been saved to disk at [`rules.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/rules.md) in the project workspace directory `C:\Users\HP\.gemini\antigravity\scratch\settlement-qa-agent` alongside [`prd.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/prd.md), [`arch.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/arch.md), [`design.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/design.md), and [`memory.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/memory.md) to serve as the binding engineering constitution.
