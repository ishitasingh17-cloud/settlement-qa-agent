"""
server/validation/models.py

Pydantic models and data contracts for Phase 9: AI Response Validation Layer.
Defines:
- ValidationDecision: PASS, REVISE, REJECT
- ViolationType: Categorized validation failure reasons
- ClaimType: Taxonomy of extracted natural language propositions
- ClaimStatus: Evidence verification outcomes for individual claims
- ExtractedClaim: Structured representation of a claim and its verification
- ValidationViolation: Structured violation record with severity and description
- ResponseValidationResult: Complete validation audit container
"""

from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class ValidationDecision(str, Enum):
    """Controlled decision states for AI response validation."""
    PASS = "PASS"
    REVISE = "REVISE"
    REJECT = "REJECT"


class ViolationType(str, Enum):
    """Categorized violation codes for response validation failures."""
    DIAGNOSIS_MISMATCH = "DIAGNOSIS_MISMATCH"
    STATUS_CONTRADICTION = "STATUS_CONTRADICTION"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    FABRICATED_IDENTIFIER = "FABRICATED_IDENTIFIER"
    FABRICATED_EVIDENCE_REF = "FABRICATED_EVIDENCE_REF"
    UNSUPPORTED_CAUSAL_CLAIM = "UNSUPPORTED_CAUSAL_CLAIM"
    UNSUPPORTED_TEMPORAL_CLAIM = "UNSUPPORTED_TEMPORAL_CLAIM"
    EPISTEMIC_VIOLATION_UNKNOWN = "EPISTEMIC_VIOLATION_UNKNOWN"
    EPISTEMIC_VIOLATION_INFERRED = "EPISTEMIC_VIOLATION_INFERRED"
    MATERIAL_OMISSION = "MATERIAL_OMISSION"


class ClaimType(str, Enum):
    """Taxonomy of natural language claims extracted from AI output."""
    FACTUAL = "FACTUAL"
    NUMERIC = "NUMERIC"
    IDENTIFIER = "IDENTIFIER"
    STATUS_DIAGNOSIS = "STATUS_DIAGNOSIS"
    CAUSAL = "CAUSAL"
    TEMPORAL = "TEMPORAL"
    EPISTEMIC = "EPISTEMIC"
    RECOMMENDATION = "RECOMMENDATION"
    NON_FACTUAL = "NON_FACTUAL"


class ClaimStatus(str, Enum):
    """Verification outcome of an extracted claim against authoritative VEO."""
    SUPPORTED = "SUPPORTED"
    INFERRED_AND_CORRECTLY_QUALIFIED = "INFERRED_AND_CORRECTLY_QUALIFIED"
    UNKNOWN_AND_CORRECTLY_QUALIFIED = "UNKNOWN_AND_CORRECTLY_QUALIFIED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"


class ExtractedClaim(BaseModel):
    """Structured representation of an extracted claim from the AI response."""
    claim_type: ClaimType = Field(..., description="Category of the claim")
    claim_text: str = Field(..., description="Exact or normalized claim proposition")
    status: ClaimStatus = Field(default=ClaimStatus.UNSUPPORTED, description="Verification outcome")
    evidence_match: Optional[str] = Field(default=None, description="Authoritative VEO field or fact matched")
    source_field: Optional[str] = Field(default=None, description="AI response field where claim occurred")

    model_config = ConfigDict(frozen=True)


class ValidationViolation(BaseModel):
    """Detailed audit record for a single validation violation."""
    violation_type: ViolationType = Field(..., description="Controlled violation classification")
    claim_text: str = Field(..., description="The offending claim text or token")
    expected_evidence: str = Field(..., description="The authoritative truth from VEO or rule violated")
    severity: str = Field(default="HIGH", description="Operational severity: CRITICAL, HIGH, MEDIUM, LOW")
    description: str = Field(..., description="Human-readable explanation of why this claim failed validation")

    model_config = ConfigDict(frozen=True)


class ResponseValidationResult(BaseModel):
    """
    Complete algorithmic validation result emitted by ResponseValidator.
    Tracks every inspected claim, detected violation, and the final safety decision.
    """
    is_valid: bool = Field(..., description="True if response passes all safety and grounding rules")
    decision: ValidationDecision = Field(..., description="PASS, REVISE, or REJECT")
    violations: List[ValidationViolation] = Field(
        default_factory=list,
        description="List of all detected validation violations"
    )
    verified_claims: List[str] = Field(
        default_factory=list,
        description="Factual claims successfully matched to authoritative VEO evidence"
    )
    unsupported_claims: List[str] = Field(
        default_factory=list,
        description="Claims lacking backing evidence in the VEO"
    )
    contradictions: List[str] = Field(
        default_factory=list,
        description="Claims that directly contradict VEO facts or statuses"
    )
    epistemic_violations: List[str] = Field(
        default_factory=list,
        description="Violations upgrading UNKNOWN to KNOWN or asserting speculative causes"
    )
    numeric_violations: List[str] = Field(
        default_factory=list,
        description="Violations involving mutated or alien currency amounts"
    )
    fabricated_references: List[str] = Field(
        default_factory=list,
        description="Identifiers or evidence references not present in the VEO"
    )
    diagnosis_drift: Optional[str] = Field(
        default=None,
        description="Diagnosis claimed by AI if different from authoritative VEO diagnosis"
    )
    validation_version: str = Field(
        default="1.0.0",
        description="Semantic version of the validation engine rules"
    )

    model_config = ConfigDict(frozen=True)
