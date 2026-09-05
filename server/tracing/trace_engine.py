"""
server/tracing/trace_engine.py

Trace Engine for PS-8 Settlement Q&A Agent (Phase 3).
Orchestrates reference resolution and transaction tracing across Gateway, Bank, and Ledger records.
Adheres strictly to docs/rules.md:
- Deterministic O(1) lookups via DataStore
- Strict separation of concerns (no reconciliation, no diagnosis, no LLM)
- Factual presence and missing record classification
- Explicit orphan record detection
- Full provenance preservation
"""

from typing import List, Optional, Union, Literal
from server.ingestion.data_store import DataStore, data_store as default_data_store
from server.models.domain import GatewayRecord, BankRecord, LedgerRecord
from server.tracing.models import (
    IdentifierType,
    TraceQuery,
    ResolutionStep,
    ResolutionPath,
    TraceResult,
)
from server.tracing.exceptions import (
    TransactionNotFoundError,
    AmbiguousIdentifierError,
)
from server.tracing.resolver import validate_and_normalize_query


class TraceEngine:
    """Deterministic trace engine operating on the in-memory DataStore."""

    def __init__(self, data_store: Optional[DataStore] = None):
        self._data_store = data_store or default_data_store

    @property
    def data_store(self) -> DataStore:
        return self._data_store

    def trace(
        self,
        query_value: str,
        identifier_type: Optional[Union[IdentifierType, str]] = None,
    ) -> TraceResult:
        """
        Traces a transaction across Gateway, Bank, and Ledger given any supported identifier.
        """
        cleaned_value, resolved_type, auto_detected = validate_and_normalize_query(
            query_value=query_value,
            identifier_type=identifier_type,
        )

        query = TraceQuery(
            identifier_value=cleaned_value,
            identifier_type=resolved_type,
            auto_detected=auto_detected,
        )

        steps: List[ResolutionStep] = []
        target_txn_id: Optional[str] = None
        gateway_rec: Optional[GatewayRecord] = None
        bank_rec: Optional[BankRecord] = None
        ledger_rec: Optional[LedgerRecord] = None

        # Execute resolution based on identifier type
        if resolved_type == IdentifierType.GATEWAY_TRANSACTION_ID:
            target_txn_id = cleaned_value
            gateway_rec = self._data_store.get_gateway_by_txn_id(target_txn_id)
            bank_rec = self._data_store.get_bank_by_txn_id(target_txn_id)
            ledger_rec = self._data_store.get_ledger_by_txn_id(target_txn_id)

            if gateway_rec is None and bank_rec is None and ledger_rec is None:
                raise TransactionNotFoundError(
                    f"No records found for gateway_transaction_id '{cleaned_value}' across Gateway, Bank, or Ledger.",
                    query_value=cleaned_value,
                    identifier_type=resolved_type.value,
                )

            steps.append(
                ResolutionStep(
                    step_number=1,
                    from_entity="QUERY",
                    to_entity="GATEWAY",
                    lookup_key="gateway_transaction_id",
                    lookup_value=cleaned_value,
                    matched=gateway_rec is not None,
                    description=f"Direct lookup of Gateway record via gateway_transaction_id '{cleaned_value}' ({'found' if gateway_rec else 'absent'}).",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=2,
                    from_entity="GATEWAY_TRANSACTION_ID",
                    to_entity="BANK",
                    lookup_key="gateway_transaction_id",
                    lookup_value=cleaned_value,
                    matched=bank_rec is not None,
                    description=f"Direct lookup of Bank record via gateway_transaction_id '{cleaned_value}' ({'found' if bank_rec else 'absent'}).",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=3,
                    from_entity="GATEWAY_TRANSACTION_ID",
                    to_entity="LEDGER",
                    lookup_key="gateway_transaction_id",
                    lookup_value=cleaned_value,
                    matched=ledger_rec is not None,
                    description=f"Direct lookup of Ledger record via gateway_transaction_id '{cleaned_value}' ({'found' if ledger_rec else 'absent'}).",
                )
            )
            summary = "gateway_transaction_id -> Gateway, Bank, Ledger"

        elif resolved_type == IdentifierType.ORDER_ID:
            gateway_rec = self._data_store.get_gateway_by_order_id(cleaned_value)
            if gateway_rec is None:
                raise TransactionNotFoundError(
                    f"No Gateway record found for order_id '{cleaned_value}'.",
                    query_value=cleaned_value,
                    identifier_type=resolved_type.value,
                )

            target_txn_id = gateway_rec.gateway_transaction_id
            bank_rec = self._data_store.get_bank_by_txn_id(target_txn_id)
            ledger_rec = self._data_store.get_ledger_by_txn_id(target_txn_id)

            steps.append(
                ResolutionStep(
                    step_number=1,
                    from_entity="QUERY",
                    to_entity="GATEWAY",
                    lookup_key="order_id",
                    lookup_value=cleaned_value,
                    matched=True,
                    description=f"Resolved Gateway record from order_id '{cleaned_value}'.",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=2,
                    from_entity="GATEWAY",
                    to_entity="PRIMARY_KEY",
                    lookup_key="gateway_transaction_id",
                    lookup_value=target_txn_id,
                    matched=True,
                    description=f"Extracted cross-system key '{target_txn_id}' from Gateway record.",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=3,
                    from_entity="PRIMARY_KEY",
                    to_entity="BANK",
                    lookup_key="gateway_transaction_id",
                    lookup_value=target_txn_id,
                    matched=bank_rec is not None,
                    description=f"Cross-system lookup of Bank record via '{target_txn_id}' ({'found' if bank_rec else 'absent'}).",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=4,
                    from_entity="PRIMARY_KEY",
                    to_entity="LEDGER",
                    lookup_key="gateway_transaction_id",
                    lookup_value=target_txn_id,
                    matched=ledger_rec is not None,
                    description=f"Cross-system lookup of Ledger record via '{target_txn_id}' ({'found' if ledger_rec else 'absent'}).",
                )
            )
            summary = "order_id -> Gateway -> gateway_transaction_id -> Bank, Ledger"

        elif resolved_type == IdentifierType.SETTLEMENT_ID:
            bank_rec = self._data_store.get_bank_by_settlement_id(cleaned_value)
            if bank_rec is None:
                raise TransactionNotFoundError(
                    f"No Bank record found for settlement_id '{cleaned_value}'.",
                    query_value=cleaned_value,
                    identifier_type=resolved_type.value,
                )

            target_txn_id = bank_rec.gateway_transaction_id
            gateway_rec = self._data_store.get_gateway_by_txn_id(target_txn_id)
            ledger_rec = self._data_store.get_ledger_by_txn_id(target_txn_id)

            steps.append(
                ResolutionStep(
                    step_number=1,
                    from_entity="QUERY",
                    to_entity="BANK",
                    lookup_key="settlement_id",
                    lookup_value=cleaned_value,
                    matched=True,
                    description=f"Resolved Bank record from settlement_id '{cleaned_value}'.",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=2,
                    from_entity="BANK",
                    to_entity="PRIMARY_KEY",
                    lookup_key="gateway_transaction_id",
                    lookup_value=target_txn_id,
                    matched=True,
                    description=f"Extracted cross-system key '{target_txn_id}' from Bank record.",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=3,
                    from_entity="PRIMARY_KEY",
                    to_entity="GATEWAY",
                    lookup_key="gateway_transaction_id",
                    lookup_value=target_txn_id,
                    matched=gateway_rec is not None,
                    description=f"Cross-system lookup of Gateway record via '{target_txn_id}' ({'found' if gateway_rec else 'absent'}).",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=4,
                    from_entity="PRIMARY_KEY",
                    to_entity="LEDGER",
                    lookup_key="gateway_transaction_id",
                    lookup_value=target_txn_id,
                    matched=ledger_rec is not None,
                    description=f"Cross-system lookup of Ledger record via '{target_txn_id}' ({'found' if ledger_rec else 'absent'}).",
                )
            )
            summary = "settlement_id -> Bank -> gateway_transaction_id -> Gateway, Ledger"

        elif resolved_type == IdentifierType.BANK_REFERENCE_NUMBER:
            bank_rec = self._data_store.get_bank_by_utr(cleaned_value)
            if bank_rec is None:
                raise TransactionNotFoundError(
                    f"No Bank record found for bank_reference_number (UTR) '{cleaned_value}'.",
                    query_value=cleaned_value,
                    identifier_type=resolved_type.value,
                )

            target_txn_id = bank_rec.gateway_transaction_id
            gateway_rec = self._data_store.get_gateway_by_txn_id(target_txn_id)
            ledger_rec = self._data_store.get_ledger_by_txn_id(target_txn_id)

            steps.append(
                ResolutionStep(
                    step_number=1,
                    from_entity="QUERY",
                    to_entity="BANK",
                    lookup_key="bank_reference_number",
                    lookup_value=cleaned_value,
                    matched=True,
                    description=f"Resolved Bank record from bank_reference_number '{cleaned_value}'.",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=2,
                    from_entity="BANK",
                    to_entity="PRIMARY_KEY",
                    lookup_key="gateway_transaction_id",
                    lookup_value=target_txn_id,
                    matched=True,
                    description=f"Extracted cross-system key '{target_txn_id}' from Bank record.",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=3,
                    from_entity="PRIMARY_KEY",
                    to_entity="GATEWAY",
                    lookup_key="gateway_transaction_id",
                    lookup_value=target_txn_id,
                    matched=gateway_rec is not None,
                    description=f"Cross-system lookup of Gateway record via '{target_txn_id}' ({'found' if gateway_rec else 'absent'}).",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=4,
                    from_entity="PRIMARY_KEY",
                    to_entity="LEDGER",
                    lookup_key="gateway_transaction_id",
                    lookup_value=target_txn_id,
                    matched=ledger_rec is not None,
                    description=f"Cross-system lookup of Ledger record via '{target_txn_id}' ({'found' if ledger_rec else 'absent'}).",
                )
            )
            summary = "bank_reference_number -> Bank -> gateway_transaction_id -> Gateway, Ledger"

        elif resolved_type == IdentifierType.LEDGER_ENTRY_ID:
            ledger_rec = self._data_store.get_ledger_by_entry_id(cleaned_value)
            if ledger_rec is None:
                raise TransactionNotFoundError(
                    f"No Ledger record found for ledger_entry_id '{cleaned_value}'.",
                    query_value=cleaned_value,
                    identifier_type=resolved_type.value,
                )

            target_txn_id = ledger_rec.gateway_transaction_id
            gateway_rec = self._data_store.get_gateway_by_txn_id(target_txn_id)
            bank_rec = self._data_store.get_bank_by_txn_id(target_txn_id)

            steps.append(
                ResolutionStep(
                    step_number=1,
                    from_entity="QUERY",
                    to_entity="LEDGER",
                    lookup_key="ledger_entry_id",
                    lookup_value=cleaned_value,
                    matched=True,
                    description=f"Resolved Ledger record from ledger_entry_id '{cleaned_value}'.",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=2,
                    from_entity="LEDGER",
                    to_entity="PRIMARY_KEY",
                    lookup_key="gateway_transaction_id",
                    lookup_value=target_txn_id,
                    matched=True,
                    description=f"Extracted cross-system key '{target_txn_id}' from Ledger record.",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=3,
                    from_entity="PRIMARY_KEY",
                    to_entity="GATEWAY",
                    lookup_key="gateway_transaction_id",
                    lookup_value=target_txn_id,
                    matched=gateway_rec is not None,
                    description=f"Cross-system lookup of Gateway record via '{target_txn_id}' ({'found' if gateway_rec else 'absent'}).",
                )
            )
            steps.append(
                ResolutionStep(
                    step_number=4,
                    from_entity="PRIMARY_KEY",
                    to_entity="BANK",
                    lookup_key="gateway_transaction_id",
                    lookup_value=target_txn_id,
                    matched=bank_rec is not None,
                    description=f"Cross-system lookup of Bank record via '{target_txn_id}' ({'found' if bank_rec else 'absent'}).",
                )
            )
            summary = "ledger_entry_id -> Ledger -> gateway_transaction_id -> Gateway, Bank"

        # Compute presence and missing records
        records_found: List[Literal["GATEWAY", "BANK", "LEDGER"]] = []
        missing_records: List[Literal["GATEWAY", "BANK", "LEDGER"]] = []

        if gateway_rec is not None:
            records_found.append("GATEWAY")
        else:
            missing_records.append("GATEWAY")

        if bank_rec is not None:
            records_found.append("BANK")
        else:
            missing_records.append("BANK")

        if ledger_rec is not None:
            records_found.append("LEDGER")
        else:
            missing_records.append("LEDGER")

        is_complete_chain = len(records_found) == 3
        # Orphan: Bank or Ledger exists while Gateway is absent
        is_orphan = (gateway_rec is None) and (bank_rec is not None or ledger_rec is not None)

        # Factual check for conflicting source statuses (e.g. Gateway failed but Bank processed)
        has_conflicts = False
        if gateway_rec is not None and bank_rec is not None:
            if gateway_rec.status == "failed" and bank_rec.settlement_status == "processed":
                has_conflicts = True

        resolution_path = ResolutionPath(
            steps=steps,
            resolved_gateway_transaction_id=target_txn_id,
            path_summary=summary,
        )

        return TraceResult(
            query=query,
            resolution=resolution_path,
            resolved_gateway_transaction_id=target_txn_id,
            gateway_record=gateway_rec,
            bank_record=bank_rec,
            ledger_record=ledger_rec,
            records_found=records_found,
            missing_records=missing_records,
            is_complete_chain=is_complete_chain,
            is_orphan=is_orphan,
            has_conflicting_statuses=has_conflicts,
        )


def trace_transaction(
    query_value: str,
    identifier_type: Optional[Union[IdentifierType, str]] = None,
    data_store: Optional[DataStore] = None,
) -> TraceResult:
    """Convenience functional interface for tracing a transaction."""
    engine = TraceEngine(data_store=data_store)
    return engine.trace(query_value=query_value, identifier_type=identifier_type)
