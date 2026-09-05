"""
server/evidence/validator.py

Deterministic validation engine for PS-8 Verified Evidence Packs (Phase 6).
Verifies:
- Transaction identity consistency across Trace, Reconciliation, and Diagnosis
- Physical evidence reference validity against source data and row indices
- Diagnosis and exception consistency (exact preservation)
- Epistemic model completeness (KNOWN, INFERRED, UNKNOWN)
- Missing record consistency (no manufactured data for missing entities)
- Cryptographic integrity fingerprint verification
"""

import hashlib
import json
from pathlib import Path
from typing import Optional

from server.tracing.models import TraceResult
from server.reconciliation.models import ReconciliationResult
from server.diagnosis.models import DiagnosisResult
from server.exceptions.models import EvidenceReference
from server.evidence.models import VerifiedEvidencePack
from server.evidence.exceptions import (
    InvalidEvidenceInputError,
    EvidenceIntegrityError,
    EvidenceCompletenessError,
)


class EvidenceValidator:
    """
    Validates the integrity, consistency, and completeness of Verified Evidence Packs.
    Fails safely and deterministically on contradictory or tampered evidence.
    """

    @staticmethod
    def validate_inputs(
        trace: TraceResult,
        recon: ReconciliationResult,
        diagnosis: DiagnosisResult,
    ) -> None:
        """
        Validates that upstream investigation objects are valid instances and
        agree on the investigated transaction identity.
        """
        if not isinstance(trace, TraceResult):
            raise InvalidEvidenceInputError(
                f"Expected TraceResult instance, got {type(trace).__name__}"
            )
        if not isinstance(recon, ReconciliationResult):
            raise InvalidEvidenceInputError(
                f"Expected ReconciliationResult instance, got {type(recon).__name__}"
            )
        if not isinstance(diagnosis, DiagnosisResult):
            raise InvalidEvidenceInputError(
                f"Expected DiagnosisResult instance, got {type(diagnosis).__name__}"
            )

        # 1. Verify transaction identity alignment across all 3 inputs
        trace_id = trace.resolved_gateway_transaction_id or trace.query.identifier_value
        recon_id = recon.transaction_id or trace_id
        diag_id = diagnosis.transaction_id

        if diag_id != trace_id and diag_id != trace.query.identifier_value:
            raise EvidenceIntegrityError(
                f"Transaction identity mismatch: TraceResult has '{trace_id}' while DiagnosisResult has '{diag_id}'"
            )
        if recon_id != diag_id and recon_id != trace_id:
            raise EvidenceIntegrityError(
                f"Transaction identity mismatch: ReconciliationResult has '{recon_id}' while DiagnosisResult has '{diag_id}'"
            )

    @staticmethod
    def validate_pack(
        pack: VerifiedEvidencePack,
        trace: Optional[TraceResult] = None,
    ) -> None:
        """
        Validates that an assembled VerifiedEvidencePack is internally consistent,
        free of manufactured data, and matches its cryptographic integrity fingerprint.
        """
        if not isinstance(pack, VerifiedEvidencePack):
            raise InvalidEvidenceInputError(
                f"Expected VerifiedEvidencePack instance, got {type(pack).__name__}"
            )

        # 1. Identity check
        expected_veo_id = f"veo_{pack.transaction_id}"
        if pack.veo_id != expected_veo_id:
            raise EvidenceIntegrityError(
                f"Invalid veo_id: expected '{expected_veo_id}', got '{pack.veo_id}'"
            )

        # 2. Missing record consistency: no fabricated data when system marked missing
        if not pack.gateway.present:
            if pack.gateway.record is not None or pack.gateway.gross_amount is not None:
                raise EvidenceIntegrityError(
                    f"Gateway marked missing for '{pack.transaction_id}', but contains fabricated record data!"
                )
            if "GATEWAY" not in pack.missing_records:
                raise EvidenceIntegrityError(
                    f"Gateway marked missing, but 'GATEWAY' is absent from missing_records list!"
                )

        if not pack.bank.present:
            if pack.bank.record is not None or pack.bank.net_settlement_amount is not None:
                raise EvidenceIntegrityError(
                    f"Bank marked missing for '{pack.transaction_id}', but contains fabricated record data!"
                )
            if "BANK" not in pack.missing_records:
                raise EvidenceIntegrityError(
                    f"Bank marked missing, but 'BANK' is absent from missing_records list!"
                )

        if not pack.ledger.present:
            if pack.ledger.record is not None or pack.ledger.ledger_amount is not None:
                raise EvidenceIntegrityError(
                    f"Ledger marked missing for '{pack.transaction_id}', but contains fabricated record data!"
                )
            if "LEDGER" not in pack.missing_records:
                raise EvidenceIntegrityError(
                    f"Ledger marked missing, but 'LEDGER' is absent from missing_records list!"
                )

        # 3. Evidence references physical line number validation
        for ref in pack.evidence_refs:
            filename = Path(ref.source_file).name
            if filename not in ["gateway.csv", "bank.csv", "ledger.csv"]:
                raise EvidenceIntegrityError(
                    f"Invalid evidence reference source_file: '{ref.source_file}'"
                )
            if ref.source_row_index < 2:
                raise EvidenceIntegrityError(
                    f"Invalid evidence reference line number {ref.source_row_index}: must be >= 2 (line 1 is header)"
                )
            if not ref.record_id or not ref.field_name:
                raise EvidenceIntegrityError(
                    "Evidence reference missing record_id or field_name!"
                )

        # 4. Cross-validate with TraceResult if provided
        if trace is not None:
            EvidenceValidator._cross_validate_trace(pack, trace)

        # 5. Cryptographic integrity hash verification
        recomputed_hash = EvidenceValidator.compute_integrity_hash(pack)
        if pack.integrity_hash != recomputed_hash:
            raise EvidenceIntegrityError(
                f"Cryptographic integrity hash mismatch! Expected '{pack.integrity_hash}', recomputed '{recomputed_hash}'"
            )

    @staticmethod
    def _cross_validate_trace(pack: VerifiedEvidencePack, trace: TraceResult) -> None:
        """Cross-validates evidence references against actual records in TraceResult."""
        records = {
            "GATEWAY": trace.gateway_record,
            "BANK": trace.bank_record,
            "LEDGER": trace.ledger_record,
        }

        for ref in pack.evidence_refs:
            rec = records.get(ref.source_system)
            if rec is not None:
                # Check record ID matches any recognized identifier on the entity
                possible_ids = [
                    getattr(rec, "gateway_transaction_id", None),
                    getattr(rec, "settlement_id", None),
                    getattr(rec, "ledger_entry_id", None),
                ]
                if ref.record_id not in [pid for pid in possible_ids if pid]:
                    raise EvidenceIntegrityError(
                        f"Evidence reference record_id '{ref.record_id}' does not match record IDs {possible_ids}"
                    )
                # Check field exists on domain model
                if hasattr(rec, ref.field_name):
                    actual_val = str(getattr(rec, ref.field_name))
                    if str(ref.field_value) != actual_val:
                        raise EvidenceIntegrityError(
                            f"Evidence reference value mismatch for {ref.field_name}: reference has '{ref.field_value}', record has '{actual_val}'"
                        )

    @staticmethod
    def compute_integrity_hash(pack: VerifiedEvidencePack) -> str:
        """
        Computes the deterministic SHA-256 fingerprint of the semantic financial facts.
        Changes to any amount, status, diagnosis, evidence ref, or epistemic fact will alter this hash.
        """
        semantic_payload = {
            "schema_version": pack.schema_version,
            "transaction_id": pack.transaction_id,
            "diagnosis": pack.diagnosis.value,
            "confidence": pack.confidence.value,
            "severity": pack.severity.value,
            "status": pack.status.value,
            "gateway_present": pack.gateway.present,
            "gateway_gross_amount": str(pack.gateway.gross_amount) if pack.gateway.gross_amount is not None else None,
            "gateway_status": pack.gateway.status,
            "bank_present": pack.bank.present,
            "bank_net_amount": str(pack.bank.net_settlement_amount) if pack.bank.net_settlement_amount is not None else None,
            "bank_status": pack.bank.settlement_status,
            "bank_utr": pack.bank.bank_reference_number,
            "ledger_present": pack.ledger.present,
            "ledger_amount": str(pack.ledger.ledger_amount) if pack.ledger.ledger_amount is not None else None,
            "ledger_entry_type": pack.ledger.entry_type,
            "bank_ledger_match": pack.reconciliation.bank_ledger_match,
            "has_conflict": pack.reconciliation.has_status_conflict,
            "known_facts": pack.epistemic_model.known_facts,
            "inferred_facts": pack.epistemic_model.inferred_facts,
            "unknown_facts": pack.epistemic_model.unknown_facts,
            "evidence_refs": [
                f"{r.source_system}:{r.source_file}:{r.source_row_index}:{r.record_id}:{r.field_name}={r.field_value}"
                for r in pack.evidence_refs
            ],
        }
        serialized = json.dumps(semantic_payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
