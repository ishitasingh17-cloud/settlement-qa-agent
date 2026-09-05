"""
server/api/dependencies.py

FastAPI dependency injection wiring for PS-8 Backend Investigation API.
Loads DataStore at startup and provisions singleton instances of TraceEngine,
EvidencePackBuilder, and InvestigationService without mutating global state.
"""

from functools import lru_cache
from pathlib import Path

from server.ingestion.data_store import DataStore
from server.tracing.trace_engine import TraceEngine
from server.evidence.builder import EvidencePackBuilder

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@lru_cache()
def get_data_store() -> DataStore:
    """Provides a singleton in-memory DataStore loaded with canonical CSV datasets."""
    store = DataStore()
    store.load_from_directory(DATA_DIR)
    return store


@lru_cache()
def get_trace_engine() -> TraceEngine:
    """Provides a singleton TraceEngine connected to the loaded DataStore."""
    return TraceEngine(data_store=get_data_store())


@lru_cache()
def get_evidence_builder() -> EvidencePackBuilder:
    """Provides a singleton EvidencePackBuilder."""
    return EvidencePackBuilder()


@lru_cache()
def get_settlement_analyst():
    """Provides a singleton SettlementAnalyst instance."""
    from server.agent.analyst import SettlementAnalyst
    return SettlementAnalyst()


@lru_cache()
def get_conversation_manager():
    """Provides a singleton ConversationManager for multi-turn sessions."""
    from server.agent.conversation import ConversationManager
    return ConversationManager()


from fastapi import Depends

def get_investigation_service(
    data_store: DataStore = Depends(get_data_store),
    trace_engine: TraceEngine = Depends(get_trace_engine),
    evidence_builder: EvidencePackBuilder = Depends(get_evidence_builder),
    settlement_analyst = Depends(get_settlement_analyst),
    conversation_manager = Depends(get_conversation_manager),
):
    """Provides the InvestigationService instance with injectable sub-dependencies."""
    from server.api.service import InvestigationService
    return InvestigationService(
        data_store=data_store,
        trace_engine=trace_engine,
        evidence_builder=evidence_builder,
        settlement_analyst=settlement_analyst,
        conversation_manager=conversation_manager,
    )
