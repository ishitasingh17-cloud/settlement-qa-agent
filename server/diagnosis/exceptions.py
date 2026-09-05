"""
server/diagnosis/exceptions.py

Structured exceptions for PS-8 Settlement Q&A Agent Diagnosis Engine (Phase 5).
"""


class DiagnosisError(Exception):
    """Base exception for diagnosis pipeline errors."""
    pass


class InvalidDiagnosisInputError(DiagnosisError):
    """Raised when input to the diagnosis engine is malformed or invalid."""
    pass
