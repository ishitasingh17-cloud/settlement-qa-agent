"""
server/api package

PS-8 Settlement Q&A Agent — Phase 7: Backend Investigation API.
Provides FastAPI routes, schemas, and orchestration services for deterministic transaction investigation.
"""

from server.api.schemas import (
    InvestigationRequest,
    UnifiedQueryRequest,
    ExplanationResponse,
    InvestigationResponse,
    SettlementListItem,
    BatchInvestigationSummary,
    ExceptionDashboardSummary,
    ErrorResponse,
)
from server.api.service import InvestigationService
from server.api.routes import router

__all__ = [
    "InvestigationRequest",
    "UnifiedQueryRequest",
    "ExplanationResponse",
    "InvestigationResponse",
    "SettlementListItem",
    "BatchInvestigationSummary",
    "ExceptionDashboardSummary",
    "ErrorResponse",
    "InvestigationService",
    "router",
]
