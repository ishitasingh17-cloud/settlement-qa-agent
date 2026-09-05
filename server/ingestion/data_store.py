"""
server/ingestion/data_store.py

In-memory indexed data store for normalized financial records.
Provides deterministic O(1) hash map lookups by all relevant identifiers:
- gateway_transaction_id
- order_id
- settlement_id
- bank_reference_number (UTR)
- ledger_entry_id

Follows Phase 2 boundary rules:
- Does NOT implement multi-hop chaining (Phase 3)
- Does NOT implement reconciliation or amount mismatch checks (Phase 4)
- Does NOT implement state diagnosis (Phase 5)
- Only indexes and provides safe access to canonical domain models.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set

from server.models.domain import GatewayRecord, BankRecord, LedgerRecord
from server.ingestion.csv_loader import (
    parse_gateway_csv,
    parse_bank_csv,
    parse_ledger_csv,
)


class DataStore:
    """In-memory indexed store for normalized financial domain entities."""

    def __init__(self):
        # Gateway indexes
        self._gateway_by_txn_id: Dict[str, GatewayRecord] = {}
        self._gateway_by_order_id: Dict[str, GatewayRecord] = {}

        # Bank indexes
        self._bank_by_txn_id: Dict[str, BankRecord] = {}
        self._bank_by_settlement_id: Dict[str, BankRecord] = {}
        self._bank_by_utr: Dict[str, BankRecord] = {}

        # Ledger indexes
        self._ledger_by_txn_id: Dict[str, LedgerRecord] = {}
        self._ledger_by_entry_id: Dict[str, LedgerRecord] = {}

        # Global distinct transaction ID registry
        self._all_transaction_ids: Set[str] = set()

    def load(
        self,
        gateway_records: List[GatewayRecord],
        bank_records: List[BankRecord],
        ledger_records: List[LedgerRecord],
    ) -> None:
        """Loads and indexes collections of normalized domain entities."""
        self.clear()

        for g in gateway_records:
            self._gateway_by_txn_id[g.gateway_transaction_id] = g
            self._gateway_by_order_id[g.order_id] = g
            self._all_transaction_ids.add(g.gateway_transaction_id)

        for b in bank_records:
            self._bank_by_txn_id[b.gateway_transaction_id] = b
            self._bank_by_settlement_id[b.settlement_id] = b
            self._bank_by_utr[b.bank_reference_number] = b
            self._all_transaction_ids.add(b.gateway_transaction_id)

        for l in ledger_records:
            self._ledger_by_txn_id[l.gateway_transaction_id] = l
            self._ledger_by_entry_id[l.ledger_entry_id] = l
            self._all_transaction_ids.add(l.gateway_transaction_id)

    def load_from_directory(self, data_dir: Path) -> None:
        """Loads and parses raw CSV files from the given data directory."""
        gw = parse_gateway_csv(data_dir / "gateway.csv")
        bnk = parse_bank_csv(data_dir / "bank.csv")
        led = parse_ledger_csv(data_dir / "ledger.csv")
        self.load(gw, bnk, led)

    def clear(self) -> None:
        """Clears all indexed records."""
        self._gateway_by_txn_id.clear()
        self._gateway_by_order_id.clear()
        self._bank_by_txn_id.clear()
        self._bank_by_settlement_id.clear()
        self._bank_by_utr.clear()
        self._ledger_by_txn_id.clear()
        self._ledger_by_entry_id.clear()
        self._all_transaction_ids.clear()

    # --- Gateway Getters ---
    def get_gateway_by_txn_id(self, txn_id: str) -> Optional[GatewayRecord]:
        return self._gateway_by_txn_id.get(txn_id)

    def get_gateway_by_order_id(self, order_id: str) -> Optional[GatewayRecord]:
        return self._gateway_by_order_id.get(order_id)

    # --- Bank Getters ---
    def get_bank_by_txn_id(self, txn_id: str) -> Optional[BankRecord]:
        return self._bank_by_txn_id.get(txn_id)

    def get_bank_by_settlement_id(self, settlement_id: str) -> Optional[BankRecord]:
        return self._bank_by_settlement_id.get(settlement_id)

    def get_bank_by_utr(self, utr: str) -> Optional[BankRecord]:
        return self._bank_by_utr.get(utr)

    # --- Ledger Getters ---
    def get_ledger_by_txn_id(self, txn_id: str) -> Optional[LedgerRecord]:
        return self._ledger_by_txn_id.get(txn_id)

    def get_ledger_by_entry_id(self, entry_id: str) -> Optional[LedgerRecord]:
        return self._ledger_by_entry_id.get(entry_id)

    # --- Global Queries ---
    def get_all_transaction_ids(self) -> Set[str]:
        return set(self._all_transaction_ids)

    @property
    def total_gateway_records(self) -> int:
        return len(self._gateway_by_txn_id)

    @property
    def total_bank_records(self) -> int:
        return len(self._bank_by_txn_id)

    @property
    def total_ledger_records(self) -> int:
        return len(self._ledger_by_txn_id)

    def get_gateway_count(self) -> int:
        return len(self._gateway_by_txn_id)

    def get_bank_count(self) -> int:
        return len(self._bank_by_txn_id)

    def get_ledger_count(self) -> int:
        return len(self._ledger_by_txn_id)


# Global singleton instance for application lifecycle
data_store = DataStore()
