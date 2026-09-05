"""
server/api/routes.py

FastAPI REST endpoints for PS-8 Settlement Q&A Agent (Phase 7).
Endpoints:
- POST /api/investigate: Single-transaction investigation by identifier
- GET /api/investigate/{identifier}: Convenience GET endpoint for single transaction
- POST /api/query: Unified search endpoint (ID or date)
- GET /api/settlements: Batch investigation listing
- GET /api/exceptions: Macro exception dashboard summary
- GET /api/health: System health and dataset readiness check
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from server.api.schemas import (
    InvestigationRequest,
    UnifiedQueryRequest,
    InvestigationResponse,
    BatchInvestigationSummary,
    ExceptionDashboardSummary,
    ErrorResponse,
    AskQuestionRequest,
    FollowUpRequest,
    ResetConversationRequest,
    ResetConversationResponse,
)
from server.agent.models import AIAnalystResponse
from server.api.dependencies import get_investigation_service
from server.api.service import InvestigationService
from server.tracing.exceptions import (
    TransactionNotFoundException,
    InvalidQueryException,
    UnsupportedIdentifierTypeException,
    AmbiguousIdentifierException,
)
from server.evidence.exceptions import EvidenceIntegrityError, EvidencePackError

router = APIRouter(prefix="/api", tags=["Investigation API"])


@router.post(
    "/investigate",
    response_model=InvestigationResponse,
    summary="Investigate a financial transaction",
    description=(
        "Runs the deterministic investigation pipeline across Gateway, Bank, and Ledger records. "
        "Returns the complete VerifiedEvidencePack (VEO) and dual-channel explanations."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query identifier or unsupported type"},
        404: {"model": ErrorResponse, "description": "Transaction identifier not found in records"},
        500: {"model": ErrorResponse, "description": "Internal evidence integrity failure"},
    },
)
async def investigate_transaction(
    request: InvestigationRequest,
    service: InvestigationService = Depends(get_investigation_service),
):
    try:
        return await service.investigate(
            query=request.query,
            query_type=request.query_type,
        )
    except TransactionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "error_code": "TRANSACTION_NOT_FOUND", "message": str(e), "status_code": 404},
        )
    except UnsupportedIdentifierTypeException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "UNSUPPORTED_IDENTIFIER_TYPE", "error_code": "UNSUPPORTED_IDENTIFIER_TYPE", "message": str(e), "status_code": 400},
        )
    except InvalidQueryException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_QUERY", "error_code": "INVALID_QUERY", "message": str(e), "status_code": 400},
        )
    except AmbiguousIdentifierException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "AMBIGUOUS_IDENTIFIER", "error_code": "AMBIGUOUS_IDENTIFIER", "message": str(e), "status_code": 400},
        )
    except EvidenceIntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTEGRITY_ERROR", "error_code": "INTEGRITY_ERROR", "message": str(e), "status_code": 500},
        )


@router.post(
    "/investigate/ask",
    response_model=AIAnalystResponse,
    summary="Ask a question about an investigated transaction",
    description="Grounded AI question answering over the transaction's Verified Evidence Pack.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid question or identifier"},
        404: {"model": ErrorResponse, "description": "Transaction identifier not found"},
    },
)
async def ask_transaction_question(
    request: AskQuestionRequest,
    service: InvestigationService = Depends(get_investigation_service),
):
    try:
        return await service.ask_question(
            identifier=request.identifier,
            question=request.question,
            query_type=request.query_type,
            conversation_id=request.conversation_id,
        )
    except TransactionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "error_code": "TRANSACTION_NOT_FOUND", "message": str(e), "status_code": 404},
        )
    except UnsupportedIdentifierTypeException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "UNSUPPORTED_IDENTIFIER_TYPE", "error_code": "UNSUPPORTED_IDENTIFIER_TYPE", "message": str(e), "status_code": 400},
        )
    except InvalidQueryException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_QUERY", "error_code": "INVALID_QUERY", "message": str(e), "status_code": 400},
        )
    except AmbiguousIdentifierException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "AMBIGUOUS_IDENTIFIER", "error_code": "AMBIGUOUS_IDENTIFIER", "message": str(e), "status_code": 400},
        )


@router.get(
    "/investigate/{identifier}",
    response_model=InvestigationResponse,
    summary="Investigate transaction by path parameter",
    description="Convenience GET endpoint for single-transaction investigation.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid identifier"},
        404: {"model": ErrorResponse, "description": "Identifier not found"},
    },
)
async def investigate_by_path(
    identifier: str,
    query_type: Optional[str] = Query(default=None, description="Optional identifier type"),
    service: InvestigationService = Depends(get_investigation_service),
):
    try:
        return await service.investigate(query=identifier, query_type=query_type)
    except TransactionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "error_code": "TRANSACTION_NOT_FOUND", "message": str(e), "status_code": 404},
        )
    except UnsupportedIdentifierTypeException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "UNSUPPORTED_IDENTIFIER_TYPE", "error_code": "UNSUPPORTED_IDENTIFIER_TYPE", "message": str(e), "status_code": 400},
        )
    except InvalidQueryException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_QUERY", "error_code": "INVALID_QUERY", "message": str(e), "status_code": 400},
        )
    except AmbiguousIdentifierException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "AMBIGUOUS_IDENTIFIER", "error_code": "AMBIGUOUS_IDENTIFIER", "message": str(e), "status_code": 400},
        )


@router.post(
    "/query",
    summary="Unified search (ID or date)",
    description="Universal lookup endpoint. If query is a date, returns settlements for that date. Otherwise runs single transaction investigation.",
)
async def unified_query(
    request: UnifiedQueryRequest,
    service: InvestigationService = Depends(get_investigation_service),
):
    try:
        return await service.query(request.query)
    except TransactionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "error_code": "TRANSACTION_NOT_FOUND", "message": str(e), "status_code": 404},
        )
    except UnsupportedIdentifierTypeException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "UNSUPPORTED_IDENTIFIER_TYPE", "error_code": "UNSUPPORTED_IDENTIFIER_TYPE", "message": str(e), "status_code": 400},
        )
    except InvalidQueryException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_QUERY", "error_code": "INVALID_QUERY", "message": str(e), "status_code": 400},
        )


@router.get(
    "/settlements",
    response_model=BatchInvestigationSummary,
    summary="List batch settlements",
    description="Lists investigated transactions with optional date or diagnosis status filters.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query or date parameter"},
    },
)
async def list_settlements(
    date: Optional[str] = Query(default=None, description="Filter by date (YYYY-MM-DD)"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by diagnosis code (e.g. SUCCESSFULLY_SETTLED)"),
    service: InvestigationService = Depends(get_investigation_service),
):
    try:
        return service.list_settlements(date=date, status=status_filter)
    except InvalidQueryException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_DATE_FORMAT", "error_code": "INVALID_DATE_FORMAT", "message": str(e), "status_code": 400},
        )


@router.get(
    "/exceptions",
    response_model=ExceptionDashboardSummary,
    summary="Exception dashboard summary",
    description="Returns aggregate counts of settlement discrepancies and list of flagged transactions requiring operational review.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query or date parameter"},
    },
)
async def get_exceptions_dashboard(
    date: Optional[str] = Query(default=None, description="Optional date filter (YYYY-MM-DD)"),
    severity: Optional[str] = Query(default=None, description="Optional severity filter (CRITICAL, HIGH, MEDIUM, LOW)"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Optional status or diagnosis filter"),
    service: InvestigationService = Depends(get_investigation_service),
):
    try:
        return service.get_exceptions_dashboard(date=date, severity=severity, status=status_filter)
    except InvalidQueryException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_DATE_FORMAT", "error_code": "INVALID_DATE_FORMAT", "message": str(e), "status_code": 400},
        )



@router.get(
    "/health",
    summary="Service health check",
    description="Returns service health status and loaded dataset metrics with environment diagnostics.",
)
async def health_check(
    service: InvestigationService = Depends(get_investigation_service),
):
    store = service.data_store

    # Check LLM provider availability safely without exposing secrets
    gemini_configured = False
    groq_configured = False
    if service.settlement_analyst and service.settlement_analyst._router:
        for p in service.settlement_analyst._router.providers:
            if p.provider_name == "gemini" and p.is_configured():
                gemini_configured = True
            elif p.provider_name == "groq" and p.is_configured():
                groq_configured = True

    dataset_verified = (
        store.total_gateway_records > 0
        and store.total_bank_records > 0
        and store.total_ledger_records > 0
    )

    return {
        "status": "ok",
        "service": "settlement-qa-agent",
        "version": "1.0.0",
        "mode": "Phase 14 - Integration & Demo Hardening",
        "records_loaded": {
            "gateway": store.total_gateway_records,
            "bank": store.total_bank_records,
            "ledger": store.total_ledger_records,
        },
        "diagnostics": {
            "application": "READY",
            "backend": "READY",
            "dataset": "VERIFIED" if dataset_verified else "MISSING",
            "frontend_config": "READY",
            "gemini_provider": "CONFIGURED" if gemini_configured else "NOT_CONFIGURED",
            "groq_provider": "CONFIGURED" if groq_configured else "NOT_CONFIGURED",
            "deterministic_fallback": "READY",
            "overall_status": "READY",
        },
    }


@router.post(
    "/follow-up",
    response_model=AIAnalystResponse,
    summary="Conversational follow-up Q&A endpoint (Phase 11)",
    description="Ask a conversational follow-up question strictly grounded in the active transaction VEO.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid question or identifier"},
        404: {"model": ErrorResponse, "description": "Transaction identifier not found"},
    },
)
async def follow_up_question(
    request: FollowUpRequest,
    service: InvestigationService = Depends(get_investigation_service),
):
    try:
        return await service.ask_question(
            identifier=request.identifier,
            question=request.question,
            query_type=request.query_type,
            conversation_id=request.conversation_id,
        )
    except TransactionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "error_code": "TRANSACTION_NOT_FOUND", "message": str(e), "status_code": 404},
        )
    except UnsupportedIdentifierTypeException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "UNSUPPORTED_IDENTIFIER_TYPE", "error_code": "UNSUPPORTED_IDENTIFIER_TYPE", "message": str(e), "status_code": 400},
        )
    except InvalidQueryException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_QUERY", "error_code": "INVALID_QUERY", "message": str(e), "status_code": 400},
        )
    except AmbiguousIdentifierException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "AMBIGUOUS_IDENTIFIER", "error_code": "AMBIGUOUS_IDENTIFIER", "message": str(e), "status_code": 400},
        )


@router.post(
    "/conversation/reset",
    response_model=ResetConversationResponse,
    summary="Reset active conversation thread",
    description="Clears conversational messages for a session while maintaining safe isolation.",
)
async def reset_conversation_endpoint(
    request: ResetConversationRequest,
    service: InvestigationService = Depends(get_investigation_service),
):
    success = service.reset_conversation(request.conversation_id)
    return ResetConversationResponse(
        conversation_id=request.conversation_id,
        success=success,
        message="Conversation session thread reset." if success else "Conversation session not found.",
    )
