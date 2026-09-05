# Implementation Roadmap & Phase Execution Plan (phases.md)

## Project: PS-8 — Settlement Q&A Agent for Fintech Support
**Document Version:** 1.0.0  
**Authority:** Authoritative Implementation Guide across all phases  
**Governing Documents:** `prd.md`, `arch.md`, `rules.md`, `design.md`, `memory.md`  
**Primary Invariant:** *Deterministic systems establish financial truth; AI explains verified evidence.*

---

## 1. Implementation Philosophy

The implementation roadmap translates the architecture and engineering rules into a **strict, sequential, and verifiable build order**:

$$\text{Foundation} \longrightarrow \text{Data} \longrightarrow \text{Trace} \longrightarrow \text{Reconciliation} \longrightarrow \text{Diagnosis} \longrightarrow \text{Evidence Pack} \longrightarrow \text{API} \longrightarrow \text{AI} \longrightarrow \text{Validation} \longrightarrow \text{UI} \longrightarrow \text{Evaluation} \longrightarrow \text{Hardening}$$

### 1.1 Why the Deterministic Pipeline Must Precede the AI Layer
1. **Mathematical Truth Precedes Natural Language:** An LLM cannot explain a financial break if the exact numerical discrepancy has not been calculated in code.
2. **Elimination of Hallucination Ground:** By constructing the immutable Verified Evidence Pack (VEO) first, the LLM prompt is bounded to a closed world of verified facts.
3. **Continuous Demoability & Offline Independence:** The application remains 100% functional as an investigation tool even if the LLM endpoint is offline, rate-limited, or disabled.
4. **Testability at Every Gate:** Unit tests can rigorously verify financial reconciliation without spending API credits or contending with non-deterministic model outputs.

---

## 2. Phase Dependency Graph

```text
Phase 0: Repo & Doc Foundation
   ↓
Phase 1: Synthetic Data & Ground Truth
   ↓
Phase 2: Ingestion & Normalization
   ↓
Phase 3: Reference Resolution & Trace Engine
   ↓
Phase 4: Deterministic Reconciliation Engine
   ↓
Phase 5: Diagnosis & Epistemic Exception Engine
   ↓
Phase 6: Verified Evidence Pack Contract
   ↓
Phase 7: Backend Investigation REST API
   ↓
Phase 8: AI Settlement Analyst (LLM Integration)
   ↓
Phase 9: AI Response Validation & Anti-Hallucination
   ↓
Phase 10: Investigation Workspace UI (React/Vite)
   ↓
Phase 11: Conversational Follow-up Q&A
   ↓
Phase 12: Exception Dashboard & Batch Ops
   ↓
Phase 13: Automated Evaluation Benchmark
   ↓
Phase 14: Integration, Reliability & Demo Hardening
```

### 2.1 Parallelization Guidelines
* **Phases 0 through 7 must be executed strictly sequentially.** No AI or frontend logic can be written before the deterministic core and API are verified.
* **Phase 10 (UI)** scaffolding may begin once Phase 7 (API) is complete, but UI integration with AI must wait until Phase 9 (Validation) is verified.
* **Phase 13 (Evaluation)** relies on Phase 1 (`ground_truth.json`) and Phase 7/9 to run automated assertion suites.

---

## 3. Detailed Phase Specifications

---

### Phase 0 — Repository & Documentation Foundation

#### Objective
Establish the project directory skeleton, configure environment tooling, enforce engineering documents, and verify that both backend and frontend execution environments boot cleanly.

#### Scope
* Initialize directory layout: `client/`, `server/`, `data/`, `scripts/`, `tests/`.
* Configure root `.gitignore` and `.env.example`.
* Place and verify governing specifications: `prd.md`, `arch.md`, `rules.md`, `design.md`, `memory.md`, `phases.md`.
* Minimal FastAPI bootstrap endpoint (`GET /api/health`).
* Minimal Vite + React + Tailwind frontend bootstrap shell.

#### Files / Modules
* `package.json`, `vite.config.js`, `tailwind.config.js`, `client/src/App.jsx`, `client/src/main.jsx`
* `server/main.py`, `server/config/settings.py`, `requirements.txt`
* `.gitignore`, `.env.example`, `README.md`

#### Implementation Tasks
1. Scaffold clean directory tree per `arch.md`.
2. Create Python virtual environment and install baseline dependencies (`fastapi`, `uvicorn`, `pydantic`, `pandas`, `pytest`).
3. Scaffold React application with Vite, install Tailwind CSS and Lucide React.
4. Implement `GET /api/health` returning `{"status": "healthy", "service": "settlement-qa-agent"}`.
5. Create `.env.example` defining `PORT=8000`, `GEMINI_API_KEY=`, `GROQ_API_KEY=`.

#### Tests
* `tests/unit/test_health.py`: Verifies `GET /api/health` returns status code 200 and healthy payload.

#### Verification
* Backend runs via `uvicorn server.main:app --port 8000` and passes healthcheck.
* Frontend runs via `npm run dev` and renders a clean Tailwind landing shell.
* No API keys or `.env` files are tracked by Git.

#### Exit Criteria
- [ ] Root directory contains all 6 governing Markdown documents.
- [ ] Backend starts without import errors.
- [ ] Frontend builds cleanly with zero linting/build errors.
- [ ] `GET /api/health` test passes.

#### Must NOT Implement Yet
* Do not write reconciliation algorithms or data parsing logic.
* Do not configure LLM API clients.
* Do not generate synthetic transaction records.

---

### Phase 1 — Synthetic Financial Data Foundation

#### Objective
Build the synthetic data generation engine and produce internally consistent, edge-case-rich CSV datasets along with a synchronized ground-truth evaluation oracle.

#### Scope
* Script `scripts/generate_mock_data.py`.
* Generate `data/gateway.csv` (100+ rows).
* Generate `data/bank.csv` (100+ rows).
* Generate `data/ledger.csv` (100+ rows).
* Generate `data/ground_truth.json` (authoritative oracle for all 11 controlled scenarios).

#### Files / Modules
* `scripts/generate_mock_data.py`
* `data/gateway.csv`
* `data/bank.csv`
* `data/ledger.csv`
* `data/ground_truth.json`

#### Implementation Tasks
1. Write deterministic generator with fixed random seed (`seed=42`) for reproducibility.
2. Model realistic data fields:
   * Gateway: `transaction_id`, `order_id`, `gateway_reference`, `amount`, `fee`, `status`, `created_at`, `captured_at`, `settlement_id`.
   * Bank: `settlement_id`, `utr`, `amount`, `settlement_date`, `bank_status`, `failure_reason`.
   * Ledger: `ledger_entry_id`, `transaction_id`, `entry_type`, `debit`, `credit`, `entry_date`, `ledger_status`, `reference`.
3. Embed all 11 canonical test scenarios from `prd.md`:
   * SC-01: Clean Settled
   * SC-02: Bank Pending
   * SC-03: Bank Rejected (`INVALID_ACCOUNT`)
   * SC-04: Gateway Failed
   * SC-05: Amount Mismatch (fee variance)
   * SC-06: Missing Bank Record
   * SC-07: Missing Ledger Entry
   * SC-08: Reference ID Mismatch
   * SC-09: Duplicate Bank UTR
   * SC-10: Conflicting Evidence (Gateway Failed + Bank Settled)
   * SC-11: In-Flight Unbatched Capture
4. Export synchronized `ground_truth.json` mapping each `transaction_id` to expected diagnosis, confidence, and discrepancies.

#### Tests
* `tests/unit/test_data_integrity.py`:
  * Validates non-empty datasets.
  * Asserts all 11 scenarios exist in `ground_truth.json`.
  * Verifies foreign-key chaining consistency for happy-path cases.

#### Verification
* Command `python scripts/generate_mock_data.py` executes in $< 1.0\text{ s}$ and outputs valid CSVs and JSON.
* Manual inspection confirms distinct ID prefixes (`TXN_`, `ORD_`, `SET_`, `UTR`, `LED_`).

#### Exit Criteria
- [ ] All 4 data artifacts exist in `data/`.
- [ ] All 11 canonical scenarios are verified present in `ground_truth.json`.
- [ ] Zero floating-point artifacts in CSV strings (exact 2 decimal places: `5000.00`).

#### Must NOT Implement Yet
* Do not write API routes.
* Do not load CSVs into memory yet.

---

### Phase 2 — Data Ingestion & Normalization

#### Objective
Implement safe, validated ingestion of the three synthetic CSVs into strongly typed Pydantic models with sub-millisecond in-memory indexing.

#### Scope
* Type casting using `decimal.Decimal` and ISO-8601 `datetime`.
* Pydantic domain models for `GatewayRecord`, `BankRecord`, `LedgerRecord`.
* In-memory index hash maps (`dict`) for $\mathcal{O}(1)$ lookups.
* Malformed row detection and startup schema validation.

#### Files / Modules
* `server/models/domain.py`
* `server/ingestion/csv_loader.py`
* `server/ingestion/data_store.py`

#### Implementation Tasks
1. Define immutable domain models in `server/models/domain.py` using Pydantic v2.
2. Implement `server/ingestion/csv_loader.py`:
   * Reads CSV rows safely via Python standard `csv` module and `Decimal`.
   * Strips whitespace, parses null representations (`""`, `"null"`, `"NONE"` $\rightarrow$ `None`).
   * Logs warnings and skips malformed rows without crashing.
3. Implement `server/ingestion/data_store.py`:
   * Loads CSVs at startup.
   * Builds in-memory lookup indexes:
     * `gateway_by_txn_id`, `gateway_by_order_id`, `gateway_by_settlement_id`
     * `bank_by_settlement_id`, `bank_by_utr`
     * `ledger_by_txn_id`, `ledger_by_reference`

#### Tests
* `tests/unit/test_csv_loader.py`:
  * Verifies correct Decimal parsing (`Decimal('4850.00')`).
  * Verifies handling of missing optional values (`utr = None`).
  * Verifies graceful error logging on corrupted CSV input.

#### Verification
* Boot test confirms data store loads all 100+ records in $< 100\text{ ms}$ with zero float conversions.

#### Exit Criteria
- [ ] Domain models reject invalid statuses or negative monetary amounts.
- [ ] In-memory indexes resolve sample `TXN_10001` in $< 1\text{ ms}$.
- [ ] Unit tests pass.

#### Must NOT Implement Yet
* Do not implement multi-hop chaining or reconciliation logic.

---

### Phase 3 — Reference Resolution & Transaction Trace Engine

#### Objective
Build the deterministic graph-traversal engine that connects disparate identifiers (`transaction_id` $\leftrightarrow$ `settlement_id` $\leftrightarrow$ `utr` $\leftrightarrow$ `ledger_entry_id`) and detects broken chains.

#### Scope
* Support lookup by `transaction_id`, `order_id`, `settlement_id`, or `utr`.
* Forward and backward reference resolution across Gateway, Bank, and Ledger.
* Identification of broken links and orphan records.
* Chronological event timeline assembly.

#### Files / Modules
* `server/tracing/reference_tracer.py`
* `server/models/trace_models.py`

#### Implementation Tasks
1. Define `ResolvedTrace` model containing linked Gateway, Bank, and Ledger records, plus reference hop metadata.
2. Implement `trace_transaction(identifier: str)` in `reference_tracer.py`:
   * Try direct Gateway match (`transaction_id`, `order_id`).
   * If Gateway found, follow `settlement_id` to Bank and `transaction_id` to Ledger.
   * If not found in Gateway, try Bank match (`utr`, `settlement_id`) and walk backward.
   * If found in Ledger only, walk backward to Gateway.
3. Detect chain integrity:
   * Emit `is_complete_chain: bool`.
   * Flag `missing_links` (e.g., Gateway has `SET_55012`, but Bank record is absent).
4. Build chronological event list sorted by UTC timestamp:
   * Payment Initiated $\rightarrow$ Captured $\rightarrow$ Ledger Credited $\rightarrow$ Batched $\rightarrow$ Bank Dispatched.

#### Tests
* `tests/unit/test_reference_tracer.py`:
  * Forward lookup via `TXN_10001`.
  * Backward lookup via `UTR...`.
  * Broken chain handling (SC-06: missing bank).

#### Verification
* Querying by Bank UTR correctly reconstructs the parent Gateway and Ledger records.

#### Exit Criteria
- [ ] All 11 canonical scenarios correctly resolve their expected trace graphs.
- [ ] Broken chains emit explicit `ERR_MISSING_BANK` / `ERR_MISSING_LEDGER` flags rather than raising `KeyError`.

#### Must NOT Implement Yet
* Do not perform amount math checks or assign settlement state diagnoses.

---

### Phase 4 — Deterministic Reconciliation Engine

#### Objective
Implement the pure algorithmic reconciliation engine that compares records across systems, evaluates the 9 discrepancy rules, and flags financial mismatches.

#### Scope
* Audit existence across all 3 systems.
* Audit monetary amounts: $\text{Gross} - \text{Fee} == \text{Bank Disbursed} == \text{Ledger Credit}$.
* Audit cross-system statuses.
* Audit reference consistency.
* Audit duplicate records.
* Audit temporal consistency ($\text{created} \le \text{captured} \le \text{cleared}$).

#### Files / Modules
* `server/reconciliation/reconciler.py`
* `server/reconciliation/discrepancy_rules.py`
* `server/models/reconciliation_models.py`

#### Implementation Tasks
1. Implement pure audit functions in `discrepancy_rules.py`:
   * `check_amounts(gateway, bank, ledger) -> Optional[Discrepancy]`
   * `check_statuses(gateway, bank, ledger) -> List[Discrepancy]`
   * `check_references(gateway, bank, ledger) -> Optional[Discrepancy]`
   * `check_duplicates(trace) -> Optional[Discrepancy]`
   * `check_temporal_order(trace) -> Optional[Discrepancy]`
2. Implement `ReconciliationEngine.reconcile(trace: ResolvedTrace) -> ReconciliationResult`:
   * Runs all audit functions using `Decimal` math with $\pm 0.01$ tolerance.
   * Compiles list of active `Discrepancy` objects with severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
   * Assembles `MathVerification` summary (gross, fee, net, disbursed, variance).

#### Tests
* `tests/unit/test_reconciler.py`:
  * Clean match: 0 discrepancies, variance $0.00$.
  * Amount mismatch (SC-05): flags `ERR_AMOUNT_MISMATCH` with exact variance `-350.00`.
  * Status contradiction (SC-10): flags `ERR_CONFLICTING_EVIDENCE`.

#### Verification
* 100% of mathematical checks pass without float rounding errors.

#### Exit Criteria
- [ ] Reconciler correctly identifies all discrepancy types defined in `prd.md`.
- [ ] Zero reliance on external AI libraries.

#### Must NOT Implement Yet
* Do not assign final human-facing diagnosis strings or confidence scores.

---

### Phase 5 — Diagnosis & Exception Engine

#### Objective
Map reconciliation results onto the controlled 11-state settlement taxonomy using a strict priority decision tree, compute rule-based confidence, and categorize findings into the Tri-State Epistemic Model.

#### Scope
* 11-State Settlement Taxonomy classifier.
* Rule-based Confidence Scorer (`HIGH`, `MEDIUM`, `LOW`).
* Epistemic Fact Classifier (KNOWN vs INFERRED vs UNKNOWN).
* Actionable recommendation generator.

#### Files / Modules
* `server/diagnosis/decision_engine.py`
* `server/exceptions/exception_engine.py`
* `server/models/diagnosis_models.py`

#### Implementation Tasks
1. Implement `determine_diagnosis(trace, reconciliation)` in `decision_engine.py`:
   * Evaluate rules in strict priority order (Section 7.2 of `arch.md`):
     1. Insufficient Evidence / Missing Gateway
     2. Gateway Failed
     3. Duplicate Record
     4. Conflicting Evidence
     5. Bank Rejected
     6. Settlement Pending (Unbatched)
     7. Missing Bank Record
     8. Missing Ledger Record
     9. Amount Mismatch
     10. Reference Mismatch
     11. Settlement Pending (Bank in-flight)
     12. Successfully Settled
2. Implement `calculate_confidence(trace, diagnosis, reconciliation)`:
   * Returns `HIGH`, `MEDIUM`, or `LOW` plus an explainable heuristic rationale string.
3. Implement `classify_epistemic_facts(trace, reconciliation, diagnosis)` in `exception_engine.py`:
   * `known_facts`: Direct row attributes present in records.
   * `inferred_facts`: Mathematical deductions (e.g. net payout).
   * `unknown_facts`: Missing timestamps, null UTRs, unrecorded failure reasons.

#### Tests
* `tests/unit/test_decision_engine.py`:
  * Tests all 11 scenarios against expected diagnoses.
  * Verifies SC-03 outputs `BANK_REJECTED` with confidence `HIGH`.
  * Verifies SC-06 outputs `MISSING_BANK_RECORD` with confidence `LOW`.
* `tests/unit/test_exception_engine.py`:
  * Asserts pending bank with null reason tags reason as UNKNOWN.

#### Verification
* Evaluating all 100+ synthetic records matches `ground_truth.json` with 100% precision.

#### Exit Criteria
- [ ] Decision engine outputs exactly 1 of the 11 controlled enums.
- [ ] Epistemic model never marks an unrecorded field as KNOWN.

#### Must NOT Implement Yet
* Do not format natural-language text or call LLM endpoints.

---

### Phase 6 — Evidence Pack & Investigation Result Contract

#### Objective
Assemble and serialize the complete, immutable Verified Evidence Pack (VEO) that acts as the single source of truth for both the UI and the AI explanation layer.

#### Scope
* Pydantic serialization of the complete investigation state.
* Enforce schema invariants (exact amounts, IDs, timestamps, and discrepancies).
* Implement serialization unit tests.

#### Files / Modules
* `server/models/evidence_pack.py`
* `server/models/schemas.py`
* `server/agent/packager.py`

#### Implementation Tasks
1. Define `VerifiedEvidencePack` schema in `server/models/evidence_pack.py` adhering to Section 9.1 of `arch.md`.
2. Implement `build_evidence_pack(trace, reconciliation, diagnosis, confidence, epistemic) -> VerifiedEvidencePack`.
3. Include timeline events, system states, math breakdown, and epistemic fact lists.
4. Add JSON export serialization helper with clean Decimal formatting.

#### Tests
* `tests/unit/test_evidence_pack.py`:
  * Validates JSON round-trip serialization.
  * Asserts required fields (`investigation_id`, `diagnosis`, `confidence`) are non-null.

#### Verification
* Generated VEO JSON matches the specification contract in `prd.md`.

#### Exit Criteria
- [ ] VEO contains zero raw unparsed CSV rows.
- [ ] All monetary fields serialize with exactly 2 decimal places.

#### Must NOT Implement Yet
* Do not send VEO to external APIs.

---

### Phase 7 — Backend Investigation API

#### Objective
Expose the deterministic investigation pipeline through FastAPI REST endpoints with structured error handling, request validation, and full offline usability.

#### Scope
* Routes:
  * `POST /api/investigate`: Single-transaction investigation.
  * `POST /api/query`: Unified search (ID, date, or basic natural-language query).
  * `GET /api/settlements`: Batch investigation summary by date.
  * `GET /api/exceptions`: Macro exception dashboard metrics.
* Comprehensive HTTP error envelopes (`400`, `404`, `500`).

#### Files / Modules
* `server/api/routes.py`
* `server/api/dependencies.py`
* `server/api/query_parser.py`
* `server/main.py`

#### Implementation Tasks
1. Implement `query_parser.py` using regex to extract `TXN_`, `ORD_`, `SET_`, `UTR` or ISO dates from raw query strings.
2. Implement `POST /api/investigate`:
   * Validates query string.
   * Runs Tracer $\rightarrow$ Reconciler $\rightarrow$ Diagnoser $\rightarrow$ Packager.
   * Returns 200 OK with `VerifiedEvidencePack` and deterministic fallback explanation.
3. Implement `GET /api/settlements` and `GET /api/exceptions`:
   * Scans in-memory records filtered by date.
   * Aggregates counts: Settled, Pending, Rejected, Mismatches, Missing.
4. Implement standard error middleware catching `TransactionNotFoundException`.

#### Tests
* `tests/integration/test_api_routes.py`:
  * `POST /api/investigate` with `TXN_10482` returns 200 OK with full VEO.
  * `POST /api/investigate` with `TXN_99999` returns 404 Not Found with remediation guide.
  * `GET /api/exceptions` returns accurate aggregated counts.

#### Verification
* Running API locally allows querying any transaction via cURL/Postman without an active internet connection or LLM key.

#### Exit Criteria
- [ ] All endpoints return typed Pydantic responses.
- [ ] Deterministic pipeline executes in $< 50\text{ ms}$.

#### Must NOT Implement Yet
* Do not call LLM API inside the route handler yet.

---

### Phase 8 — AI Settlement Analyst

#### Objective
Integrate the LLM explanation layer using a modular provider abstraction (Gemini / Groq) to synthesize dual-channel natural language explanations strictly bounded by the Verified Evidence Pack.

#### Scope
* Provider abstraction: `LLMClient` with Gemini 1.5 Flash and Groq implementations.
* Parameterized system prompt enforcing financial guardrails and epistemic honesty.
* Enforced JSON structured output: `internal_summary`, `merchant_friendly_response`, `known_facts`, `unknown_facts`.
* Timeout ($4.0\text{ s}$) and graceful failure handling.

#### Files / Modules
* `server/agent/llm_client.py`
* `server/agent/prompts.py`
* `server/agent/explainer.py`

#### Implementation Tasks
1. Implement `server/agent/prompts.py` embedding the strict financial safety instructions from Section 9 of `rules.md`.
2. Implement `server/agent/llm_client.py`:
   * Read API keys from environment settings.
   * Support Gemini 1.5 Flash as primary, with Groq as failover.
   * Set request timeout to 4.0 seconds.
3. Implement `server/agent/explainer.py`:
   * Formats VEO into prompt.
   * Invokes LLM requesting structured JSON.
   * If call times out or throws exception, catches error and returns pre-compiled deterministic explanation.

#### Tests
* `tests/unit/test_prompts.py`: Verifies VEO fields correctly populate template placeholders.
* `tests/integration/test_llm_client.py` (marked `@pytest.mark.external`): Verifies live API returns valid JSON when keys are configured.

#### Verification
* When `GEMINI_API_KEY` is dummy or internet is disabled, pipeline gracefully returns deterministic explanation without crashing.

#### Exit Criteria
- [ ] Output contains both `internal_summary` and `merchant_friendly_response`.
- [ ] Zero unhandled API exceptions bubble to the HTTP router.

#### Must NOT Implement Yet
* Do not bypass response validation.

---

### Phase 9 — AI Response Validation & Safety Layer

#### Objective
Implement an algorithmic gatekeeper that inspects the LLM's natural-language output and rejects any response that mutates monetary amounts, invents bank failure reasons, or contradicts verified statuses.

#### Scope
* Regex scanner for currency amounts in AI text.
* Status contradiction detector.
* Unattributed bank reason detector.
* Automatic fallback substitution on validation breach.

#### Files / Modules
* `server/validation/response_validator.py`
* `tests/unit/test_response_validator.py`

#### Implementation Tasks
1. Implement `ResponseValidator.validate(ai_output, evidence_pack) -> ValidationResult`:
   * **Amount Check:** Extracts all numbers preceded by currency signs. Asserts every number exists in `[gross, fee, net, disbursed, variance]`.
   * **Status Check:** If `bank_status == PENDING`, asserts text does not contain *"rejected"*, *"failed"*, or *"declined"*.
   * **Failure Reason Check:** If `bank.failure_reason == None`, asserts text does not assert a specific external cause (*"server down"*, *"insufficient funds"*).
2. If validation fails:
   * Log critical warning with discrepancy details.
   * Replace `ai_output` with deterministic fallback text.
   * Set `validation_passed: false` and `fallback_used: true`.

#### Tests
* `tests/unit/test_response_validator.py`:
  * Passes on faithful explanation.
  * Rejects adversarial hallucination mutating ₹4,850.00 to ₹4,500.00.
  * Rejects hallucinated bank rejection reason when record is pending.

#### Verification
* Feeding deliberately poisoned AI mock responses triggers 100% rejection and clean fallback substitution.

#### Exit Criteria
- [ ] Validator executes in $< 5\text{ ms}$.
- [ ] Zero hallucinated amounts can pass to the client.

#### Must NOT Implement Yet
* Do not implement frontend components.

---

### Phase 10 — Investigation UI

#### Objective
Construct the responsive, high-density React frontend workspace following `design.md`, rendering status banners, the 3-system inspector, the reference chain diagram, the timeline, and dual explanations.

#### Scope
* Universal Investigation Search Bar.
* Status Banner & Confidence Meter.
* 3-Column Evidence Inspector (Gateway | Bank | Ledger).
* Signature Component: Reference Chain Node Diagram.
* Signature Component: Chronological Lifecycle Timeline.
* Dual Explanation Panel with one-click copy button for merchant scripts.
* Multi-stage deterministic progress loader.

#### Files / Modules
* `client/src/components/investigation/SearchBar.jsx`
* `client/src/components/investigation/DiagnosisHeader.jsx`
* `client/src/components/investigation/SystemInspector.jsx`
* `client/src/components/investigation/ReferenceChain.jsx`
* `client/src/components/investigation/TimelineView.jsx`
* `client/src/components/investigation/ExplanationDualView.jsx`
* `client/src/hooks/useInvestigation.js`
* `client/src/services/api.js`

#### Implementation Tasks
1. Implement API client service (`client/src/services/api.js`) connecting to `/api/investigate`.
2. Build `SearchBar` with suggestions (`TXN_10482`, `ORD_90210`).
3. Build `DiagnosisHeader` displaying semantic status color badge and explainable confidence pill.
4. Build `SystemInspector` rendering Gateway, Bank, and Ledger cards with monetary hierarchy.
5. Build `ReferenceChain` visualizing hops with clean SVG nodes and dashed broken links.
6. Build `TimelineView` showing chronological event history.
7. Build `ExplanationDualView` with active copy button (`✓ Copied to Clipboard`).
8. Implement multi-step progress bar during fetch.

#### Tests
* Frontend component smoke tests / manual test checklist:
  * Searching `TXN_10482` renders all cards within 1 second.
  * Copy button copies clean merchant script to clipboard.
  * Empty state and 404 error banner display correctly.

#### Verification
* Visual appearance matches `design.md` specifications and adheres to the light-first palette.

#### Exit Criteria
- [ ] Zero unhandled console errors during search.
- [ ] Tabular alignment on all monetary numbers.

#### Must NOT Implement Yet
* Do not build follow-up Q&A thread or batch exception dashboard.

---

### Phase 11 — Conversational Follow-up Q&A

#### Objective
Add interactive follow-up Q&A allowing the agent to ask contextual questions about the active transaction, strictly bounded by the cached Verified Evidence Pack.

#### Scope
* `POST /api/follow-up` endpoint.
* Bounded single-turn LLM prompt containing cached VEO.
* Contextual prompt suggestion chips (*"Was customer charged twice?"*, *"What was the bank reason?"*).
* Interactive chat thread below explanation card.

#### Files / Modules
* `server/api/routes.py`
* `server/agent/follow_up_agent.py`
* `client/src/components/conversation/FollowUpChat.jsx`
* `client/src/hooks/useFollowUp.js`

#### Implementation Tasks
1. Implement `POST /api/follow-up`:
   * Accepts `{ "transaction_id": str, "question": str }`.
   * Retrieves cached VEO from data store.
   * Instructs LLM to answer using ONLY VEO facts; if absent, state *"Information not available in records."*
2. Implement `FollowUpChat.jsx` in frontend:
   * Displays 3 clickable quick chips.
   * Appends user question and agent reply to thread.
   * Disables input while query is in-flight.

#### Tests
* `tests/integration/test_follow_up.py`:
  * Validates query on fee deductions returns exact ₹150.00.
  * Validates out-of-scope question (*"What is customer's phone number?"*) returns data unavailable disclaimer.

#### Verification
* Support agent can ask 3 successive questions about `TXN_10482` and receive grounded answers.

#### Exit Criteria
- [ ] Follow-up agent never queries raw files or executes external tools.
- [ ] Responses render in $< 2.5\text{ s}$.

#### Must NOT Implement Yet
* Do not build macro exception dashboard.

---

### Phase 12 — Exception Dashboard & Investigation Intelligence

#### Objective
Build the macro-level operational overview dashboard allowing support leads and operations specialists to monitor batch settlement breaks, filter by category, and drill down into individual transactions.

#### Scope
* `GET /api/settlements` and `GET /api/exceptions` integration.
* Top-level KPI cards: Total Volume, Settled Rate, Pending, Rejections, Mismatches.
* Interactive filterable exception table.
* One-click row drill-down loading transaction into Investigation Workspace.

#### Files / Modules
* `client/src/components/dashboard/ExceptionDashboard.jsx`
* `client/src/components/dashboard/KpiCards.jsx`
* `client/src/components/dashboard/ExceptionTable.jsx`
* `client/src/pages/DashboardPage.jsx`

#### Implementation Tasks
1. Connect frontend dashboard page to `/api/settlements` and `/api/exceptions`.
2. Render 5 KPI summary cards with semantic status colors.
3. Render interactive table grouping issues:
   * `AMOUNT_MISMATCH`
   * `BANK_REJECTED`
   * `MISSING_BANK_RECORD`
   * `SETTLEMENT_PENDING`
4. Add click handler on table row: switches active tab to "Investigate" and triggers search for clicked ID.

#### Tests
* Manual verification: Clicking an exception row (`TXN_10025`) instantly opens its deep investigation view.

#### Verification
* Operations dashboard renders 500-transaction summary in $< 300\text{ ms}$.

#### Exit Criteria
- [ ] All 11 scenario categories are represented in the exception table.
- [ ] Clean navigation between Dashboard and Investigation views.

#### Must NOT Implement Yet
* Do not add heavy analytics or PDF exports.

---

### Phase 13 — Automated Evaluation & Ground-Truth Verification

#### Objective
Build the automated test harness (`scripts/run_eval.py`) that evaluates the entire pipeline against `data/ground_truth.json` and outputs a benchmark scorecard.

#### Scope
* CLI evaluation runner `scripts/run_eval.py`.
* Automated metric calculations:
  * Deterministic Diagnosis Accuracy (Target: 100%)
  * Discrepancy Detection Precision & Recall (Target: 100%)
  * Reference Chaining Success Rate (Target: 100%)
  * Epistemic Honesty Score (Target: $> 98\%$)
  * AI Hallucination Rate (Target: 0%)

#### Files / Modules
* `scripts/run_eval.py`
* `tests/evaluation/test_ground_truth_accuracy.py`

#### Implementation Tasks
1. Implement `scripts/run_eval.py`:
   * Loads `data/ground_truth.json`.
   * Iterates through all test cases, running the pipeline end-to-end.
   * Compares actual diagnosis with `expected_diagnosis`.
   * Inspects AI explanation text to ensure unknown facts were not asserted as known.
   * Formats and prints a terminal scorecard.
2. Integrate into Pytest suite under `tests/evaluation/`.

#### Tests
* Command `python scripts/run_eval.py` runs and evaluates 100 cases.

#### Verification
* Terminal scorecard reports 100% deterministic accuracy and 0% hallucinations.

#### Exit Criteria
- [ ] Evaluation harness runs unattended in $< 30\text{ s}$.
- [ ] Meets all target thresholds defined in `prd.md`.

#### Must NOT Implement Yet
* Do not modify `ground_truth.json` to hide code bugs.

---

### Phase 14 — Integration, Reliability & Demo Hardening

#### Objective
Conduct end-to-end system hardening, verify all 7 canonical demo scenarios, test adversarial network/API failures, and finalize the presentation delivery script.

#### Scope
* Comprehensive cross-browser and responsive layout verification.
* Verification of 7 canonical demonstration test cases.
* Adversarial stress testing (empty search, corrupted inputs, disconnected LLM).
* Documentation finalization and demo script walkthrough.

#### Files / Modules
* `README.md` (Quickstart, architecture overview, demo walkthrough)
* `memory.md` (Updated to final verified state)

#### Implementation Tasks
1. Execute full verification across the 7 demo test cases (Section 6).
2. Simulate LLM failure (invalid API key) and verify system operates gracefully in deterministic mode.
3. Test edge cases:
   * Query with spaces, lower-case, or special characters.
   * Non-existent ID (`TXN_99999`).
4. Update `README.md` with 2-minute setup instructions (`pip install`, `npm install`, `npm run dev`).
5. Update `memory.md` recording Phase 14 completion.

#### Tests
* Complete test run: `pytest` executes all unit, integration, and evaluation tests with zero failures.

#### Verification
* A developer on a fresh machine can clone, configure `.env`, and launch the app in under 3 minutes.

#### Exit Criteria
- [ ] All 7 demo scenarios execute flawlessly.
- [ ] 100% test suite passes.
- [ ] `memory.md` marks project DEMO READY.

---

## 4. Priority Categorization (P0 / P1 / P2)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FEATURE PRIORITIES                            │
├──────────────────────┬──────────────────────┬───────────────────────────┤
│   P0 (Must Have)     │   P1 (Important)     │   P2 (Polish)             │
│   Non-Negotiable MVP │   Demo Differentiators│   Post-Hackathon Stretch  │
├──────────────────────┼──────────────────────┼───────────────────────────┤
│ • Phase 0: Repo Base │ • Phase 11: Follow-Up│ • Time-series failure     │
│ • Phase 1: Mock Data │   Contextual Q&A     │   trend line charts       │
│ • Phase 2: Ingestion │ • Phase 12: Exception│ • Exportable investigation│
│ • Phase 3: Trace     │   Dashboard          │   PDF incident report     │
│ • Phase 4: Reconcile │ • Phase 13: Ground   │ • Multi-currency live fx  │
│ • Phase 5: Diagnosis │   Truth Benchmark    │   conversion simulator    │
│ • Phase 6: VEO Pack  │ • Micro-interaction  │ • Automated incoming      │
│ • Phase 7: REST API  │   animations         │   ticket webhook listener │
│ • Phase 8: AI Layer  │ • Suggested search   │                           │
│ • Phase 9: Validator │   query chips        │                           │
│ • Phase 10: React UI │                      │                           │
│ • Phase 14: Hardening│                      │                           │
└──────────────────────┴──────────────────────┴───────────────────────────┘
```

*Rule:* P1 and P2 features must never be implemented if any P0 capability is incomplete or failing verification.

---

## 5. Global Definition of Done (DoD)

A phase is considered **COMPLETE** if and only if all of the following conditions are met:
1. **Scope Executed:** All tasks listed under the phase's implementation scope are written.
2. **Automated Tests Pass:** New unit or integration tests for the phase execute and pass with zero failures.
3. **No Regressions:** All existing tests from earlier phases continue to pass.
4. **Architectural Compliance:** The code strictly adheres to `arch.md` module boundaries and `rules.md` engineering laws.
5. **No Speculative Code:** No future-phase functionality has been prematurely implemented.
6. **No Committed Secrets:** `.env` and sensitive API keys remain uncommitted.
7. **Memory Updated:** `memory.md` is updated with the phase completion log, modified files, and next active task.

---

## 6. Canonical Demonstration Acceptance Scenarios

Before declaring the project demo-ready in Phase 14, the following 7 scenarios must be demonstrated live:

### Demo 1: The Clean Settlement (SC-01)
* **Input:** `TXN_10001`
* **Result:** Status `SUCCESSFULLY_SETTLED`. All cards green. Bank UTR visible. High Confidence. Merchant response confirms payout completed.

### Demo 2: The In-Flight Settlement Delay (SC-02)
* **Input:** `TXN_10482`
* **Result:** Status `SETTLEMENT_PENDING`. Gateway captured, Ledger posted, Bank pending without UTR. Medium Confidence. AI explicitly explains delay without inventing an unrecorded bank rejection reason.

### Demo 3: The Amount Break (SC-05)
* **Input:** `TXN_10025`
* **Result:** Status `AMOUNT_MISMATCH`. Gateway net is ₹4,850.00; Bank disbursed is ₹4,500.00. Prominent alert banner highlights the exact ₹350.00 variance.

### Demo 4: The Missing Bank Record (SC-06)
* **Input:** `TXN_10040`
* **Result:** Status `MISSING_BANK_RECORD`. Gateway batched payment, but Bank clearing file has no record. Low Confidence. Epistemic model tags bank clearing confirmation as UNKNOWN.

### Demo 5: The Verified Bank Rejection (SC-03)
* **Input:** `TXN_10015`
* **Result:** Status `BANK_REJECTED`. Bank failure code `INVALID_ACCOUNT`. AI explains the exact returned reason and instructs support agent to request updated banking details from the merchant.

### Demo 6: Conflicting Cross-System Evidence (SC-10)
* **Input:** `TXN_10080`
* **Result:** Status `CONFLICTING_EVIDENCE`. Bank reports settled, but Gateway reports failed. The agent refuses to declare settlement success, surfaces the contradiction, and routes to operations triage.

### Demo 7: Graceful AI Failure Resilience
* **Input:** `TXN_10482` with invalid `GEMINI_API_KEY`.
* **Result:** System displays `[Deterministic Mode]` badge. All cards, tables, amounts, and timelines render flawlessly using pre-compiled deterministic explanation templates. Zero application crashes.

---

## 7. AI Coding Agent Execution Protocol

When an autonomous AI agent implements a phase from this roadmap, it must strictly follow this protocol:

1. **Orientation:** Read `memory.md` to identify the current phase. Read `prd.md`, `arch.md`, and `rules.md`.
2. **Strict Boundary:** Implement ONLY the tasks and files specified in the current phase. Do not jump ahead.
3. **Inspect Before Create:** Check existing files to reuse domain models and helpers.
4. **Test After Implementation:** Run `pytest` and verify the exit criteria.
5. **Report & Update:** Report progress using the standard execution template and record the completion in `memory.md`.

```text
================================================================================
PHASE EXECUTION REPORT
================================================================================
PHASE: <Phase Number> — <Phase Name>
STATUS: COMPLETE / BLOCKED

IMPLEMENTED:
- <Summary of functionality built>

FILES CREATED:
- <List of created files>

FILES MODIFIED:
- <List of modified files>

TESTS EXECUTED:
- <Pytest command and pass/fail summary>

VERIFICATION:
- <Evidence that phase works as intended>

KNOWN LIMITATIONS:
- <Any bounded behavior deferred to later phases>

NEXT PHASE:
- <Phase Number + 1>
================================================================================
```

---

## 8. Final Roadmap Summary

| Phase | Phase Name | Primary Output | Priority | Key Milestone |
| :---: | :--- | :--- | :---: | :--- |
| **0** | Foundation | Runnable Skeleton & Docs | P0 | Environment & Docs Operational |
| **1** | Synthetic Data | CSVs & Ground Truth Oracle | P0 | Benchmark Test Data Ready |
| **2** | Ingestion & Normalization | Typed Pydantic In-Memory Store | P0 | Fast Float-Free Data Layer |
| **3** | Reference Resolution | Multi-Hop Transaction Tracer | P0 | Graph Resolution Operational |
| **4** | Deterministic Reconciler | Algorithmic Audit Engine | P0 | Exact Financial Math Verified |
| **5** | Diagnosis & Exceptions | 11-State Decision Tree | P0 | Deterministic Truth Established |
| **6** | Evidence Pack | VEO JSON Contract | P0 | Clean AI Boundary Formalized |
| **7** | Backend REST API | FastAPI Investigation Routes | P0 | Offline API Fully Functional |
| **8** | AI Settlement Analyst | Constrained LLM Explainer | P0 | Dual Natural Language Synthesized |
| **9** | Response Validator | Anti-Hallucination Gatekeeper | P0 | Zero Unsupported Claims Permitted |
| **10**| Investigation UI | React / Vite Dashboard | P0 | Interactive Support Cockpit Live |
| **11**| Follow-up Q&A | Contextual Q&A Thread | P1 | Interactive Investigation Assistant |
| **12**| Exception Dashboard | Macro Batch Triage Table | P1 | Operational Health Visualized |
| **13**| Evaluation Harness | Ground Truth Test Runner | P1 | Benchmark Proven (100% / 0%) |
| **14**| Demo Hardening | Hardened Full-Stack System | P0 | Hackathon Demo Ready |

---

> **Implementation Note:** This document has also been saved to disk at [`phases.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/phases.md) in the project workspace directory `C:\Users\HP\.gemini\antigravity\scratch\settlement-qa-agent` alongside [`prd.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/prd.md), [`arch.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/arch.md), [`design.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/design.md), [`rules.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/rules.md), and [`memory.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/memory.md) to serve as the strict sequential roadmap for development.
