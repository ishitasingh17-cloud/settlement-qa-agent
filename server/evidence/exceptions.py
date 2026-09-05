"""
server/evidence/exceptions.py

Structured exceptions for PS-8 Verified Evidence Pack (VEO) Builder (Phase 6).
Adheres strictly to docs/rules.md:
- Structured exception hierarchy
- Actionable, descriptive error messages
- Deterministic error classification
"""


class EvidencePackError(Exception):
    """Base exception for all Evidence Pack / VEO builder errors."""
    pass


class InvalidEvidenceInputError(EvidencePackError):
    """Raised when input objects (TraceResult, ReconciliationResult, DiagnosisResult) are invalid, missing, or contradictory."""
    pass


class EvidenceIntegrityError(EvidencePackError):
    """Raised when evidence references fail physical source verification or cross-entity consistency checks."""
    pass


class EvidenceCompletenessError(EvidencePackError):
    """Raised when mandatory evidence components are missing or incomplete."""
    pass


class EvidenceSerializationError(EvidencePackError):
    """Raised when serialization or deserialization of an Evidence Pack fails."""
    pass
