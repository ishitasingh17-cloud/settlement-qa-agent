"""
server/evidence package

PS-8 Settlement Q&A Agent — Phase 6: Verified Evidence Pack (VEO) Builder.
Provides the canonical, immutable VerifiedEvidencePack packaging all verified investigation
evidence from Phases 2-5 for downstream API (Phase 7), AI Analyst (Phase 8), and UI (Phase 10).
"""

from server.evidence.models import (
    TimelineEvent,
    GatewayEvidence,
    BankEvidence,
    LedgerEvidence,
    ReconciliationSummary,
    VerifiedEvidencePack,
    EvidencePack,
)
from server.evidence.exceptions import (
    EvidencePackError,
    InvalidEvidenceInputError,
    EvidenceIntegrityError,
    EvidenceCompletenessError,
    EvidenceSerializationError,
)
from server.evidence.validator import EvidenceValidator
from server.evidence.builder import EvidencePackBuilder, build_evidence_pack

__all__ = [
    "TimelineEvent",
    "GatewayEvidence",
    "BankEvidence",
    "LedgerEvidence",
    "ReconciliationSummary",
    "VerifiedEvidencePack",
    "EvidencePack",
    "EvidencePackError",
    "InvalidEvidenceInputError",
    "EvidenceIntegrityError",
    "EvidenceCompletenessError",
    "EvidenceSerializationError",
    "EvidenceValidator",
    "EvidencePackBuilder",
    "build_evidence_pack",
]
