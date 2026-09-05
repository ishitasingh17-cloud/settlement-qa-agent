"""
server/ingestion/csv_loader.py

Safe, deterministic CSV loaders for Gateway, Bank, and Ledger mock datasets.
Strictly preserves raw data immutability, validates column schemas, performs
deterministic type parsing, preserves distinct identifiers and amounts, and
constructs validated Pydantic canonical domain records.
"""

import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Optional

from server.models.domain import (
    SourceProvenance,
    GatewayRecord,
    BankRecord,
    LedgerRecord,
)
from server.ingestion.exceptions import (
    DatasetNotFoundError,
    EmptyDatasetError,
    SchemaValidationError,
    RowValidationError,
)

GATEWAY_REQUIRED_COLUMNS = [
    "gateway_transaction_id",
    "order_id",
    "amount_in_cents",
    "currency",
    "status",
    "method",
    "email",
    "contact",
    "error_code",
    "error_description",
    "created_at_timestamp",
]

BANK_REQUIRED_COLUMNS = [
    "settlement_id",
    "gateway_transaction_id",
    "net_settled_amount",
    "bank_reference_number",
    "settlement_status",
    "settled_at",
]

LEDGER_REQUIRED_COLUMNS = [
    "ledger_entry_id",
    "gateway_transaction_id",
    "account_type",
    "entry_type",
    "amount",
    "booked_at",
]


def _validate_file_and_schema(filepath: Path, required_columns: List[str]) -> List[dict]:
    """Validates existence, non-emptiness, and header schema, returning raw dict rows."""
    if not filepath.exists():
        raise DatasetNotFoundError(str(filepath))
    
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        
        missing = [col for col in required_columns if col not in fieldnames]
        if missing:
            raise SchemaValidationError(filepath.name, missing, fieldnames)
        
        rows = list(reader)
        
    if not rows:
        raise EmptyDatasetError(str(filepath))
        
    return rows


def parse_gateway_csv(filepath: Path) -> List[GatewayRecord]:
    """
    Safely parses and validates gateway.csv into GatewayRecord domain models.
    Preserves raw integer cents alongside Decimal representation.
    Parses Unix epoch timestamp into canonical UTC datetime.
    """
    rows = _validate_file_and_schema(filepath, GATEWAY_REQUIRED_COLUMNS)
    records: List[GatewayRecord] = []

    for idx, row in enumerate(rows, start=2):  # 1-based physical line number; line 1 is header
        txn_id = row.get("gateway_transaction_id", "").strip()
        if not txn_id:
            raise RowValidationError(filepath.name, idx, "gateway_transaction_id", "", "Transaction ID cannot be empty")

        order_id = row.get("order_id", "").strip()
        if not order_id:
            raise RowValidationError(filepath.name, idx, "order_id", "", "Order ID cannot be empty")

        raw_amount_str = row.get("amount_in_cents", "").strip()
        if not raw_amount_str.isdigit():
            raise RowValidationError(filepath.name, idx, "amount_in_cents", raw_amount_str, "Amount must be an integer string")
        raw_amount_int = int(raw_amount_str)
        gross_amount_dec = Decimal(raw_amount_str)

        raw_status = row.get("status", "").strip().lower()
        if raw_status not in ("captured", "failed"):
            raise RowValidationError(filepath.name, idx, "status", raw_status, "Status must be 'captured' or 'failed'")

        raw_ts_str = row.get("created_at_timestamp", "").strip()
        try:
            ts_epoch = int(raw_ts_str)
            created_at_dt = datetime.fromtimestamp(ts_epoch, tz=timezone.utc).replace(tzinfo=None)
        except (ValueError, OSError) as e:
            raise RowValidationError(filepath.name, idx, "created_at_timestamp", raw_ts_str, f"Invalid Unix timestamp: {e}")

        # Null handling: empty strings become None for optional error and contact fields
        error_code = row.get("error_code", "").strip() or None
        error_desc = row.get("error_description", "").strip() or None
        email = row.get("email", "").strip() or None
        contact = row.get("contact", "").strip() or None

        provenance = SourceProvenance(
            source_system="GATEWAY",
            source_file=str(filepath),
            source_row_index=idx,
            raw_timestamp=raw_ts_str,
            timezone_note="Source timestamp is Unix epoch seconds (UTC-referenced per Unix epoch definition).",
        )

        records.append(
            GatewayRecord(
                gateway_transaction_id=txn_id,
                order_id=order_id,
                gross_amount=gross_amount_dec,
                raw_amount=raw_amount_int,
                currency=row.get("currency", "INR").strip(),
                status=raw_status,
                source_status=row.get("status", "").strip(),
                method=row.get("method", "").strip(),
                email=email,
                contact=contact,
                error_code=error_code,
                error_description=error_desc,
                created_at=created_at_dt,
                provenance=provenance,
            )
        )

    return records


def parse_bank_csv(filepath: Path) -> List[BankRecord]:
    """
    Safely parses and validates bank.csv into BankRecord domain models.
    Preserves raw integer amount alongside Decimal representation.
    Parses 'DD-MM-YYYY HH:MM' timestamp. If settlement failed and settled_at is empty,
    preserves None without fabricating a timestamp.
    """
    rows = _validate_file_and_schema(filepath, BANK_REQUIRED_COLUMNS)
    records: List[BankRecord] = []

    for idx, row in enumerate(rows, start=2):  # 1-based physical line number; line 1 is header
        settlement_id = row.get("settlement_id", "").strip()
        if not settlement_id:
            raise RowValidationError(filepath.name, idx, "settlement_id", "", "Settlement ID cannot be empty")

        txn_id = row.get("gateway_transaction_id", "").strip()
        if not txn_id:
            raise RowValidationError(filepath.name, idx, "gateway_transaction_id", "", "Transaction ID cannot be empty")

        raw_amount_str = row.get("net_settled_amount", "").strip()
        if not raw_amount_str.isdigit():
            raise RowValidationError(filepath.name, idx, "net_settled_amount", raw_amount_str, "Amount must be an integer string")
        raw_amount_int = int(raw_amount_str)
        net_amount_dec = Decimal(raw_amount_str)

        raw_status = row.get("settlement_status", "").strip().lower()
        if raw_status not in ("processed", "failed", "pending"):
            raise RowValidationError(filepath.name, idx, "settlement_status", raw_status, "Status must be 'processed', 'failed', or 'pending'")

        utr = row.get("bank_reference_number", "").strip()
        if not utr:
            raise RowValidationError(filepath.name, idx, "bank_reference_number", "", "Bank reference number cannot be empty")

        raw_ts_str = row.get("settled_at", "").strip()
        settled_at_dt: Optional[datetime] = None
        if raw_ts_str:
            try:
                settled_at_dt = datetime.strptime(raw_ts_str, "%d-%m-%Y %H:%M")
            except ValueError as e:
                raise RowValidationError(filepath.name, idx, "settled_at", raw_ts_str, f"Invalid date format (expected DD-MM-YYYY HH:MM): {e}")
        else:
            # Explicit epistemic rule: settled_at may only be empty if settlement failed or pending
            if raw_status not in ("failed", "pending"):
                raise RowValidationError(filepath.name, idx, "settled_at", "", "Processed settlement cannot have empty settled_at timestamp")

        provenance = SourceProvenance(
            source_system="BANK",
            source_file=str(filepath),
            source_row_index=idx,
            raw_timestamp=raw_ts_str or None,
            timezone_note="Source timestamp provides no timezone metadata; parsed as naive clock time. Timezone is unspecified.",
        )

        records.append(
            BankRecord(
                settlement_id=settlement_id,
                gateway_transaction_id=txn_id,
                net_settlement_amount=net_amount_dec,
                raw_amount=raw_amount_int,
                bank_reference_number=utr,
                settlement_status=raw_status,
                source_status=row.get("settlement_status", "").strip(),
                settled_at=settled_at_dt,
                provenance=provenance,
            )
        )

    return records


def parse_ledger_csv(filepath: Path) -> List[LedgerRecord]:
    """
    Safely parses and validates ledger.csv into LedgerRecord domain models.
    Preserves raw integer amount alongside Decimal representation.
    Parses 'DD-MM-YYYY HH:MM' booking timestamp.
    """
    rows = _validate_file_and_schema(filepath, LEDGER_REQUIRED_COLUMNS)
    records: List[LedgerRecord] = []

    for idx, row in enumerate(rows, start=2):  # 1-based physical line number; line 1 is header
        ledger_id = row.get("ledger_entry_id", "").strip()
        if not ledger_id:
            raise RowValidationError(filepath.name, idx, "ledger_entry_id", "", "Ledger entry ID cannot be empty")

        txn_id = row.get("gateway_transaction_id", "").strip()
        if not txn_id:
            raise RowValidationError(filepath.name, idx, "gateway_transaction_id", "", "Transaction ID cannot be empty")

        raw_amount_str = row.get("amount", "").strip()
        if not raw_amount_str.isdigit():
            raise RowValidationError(filepath.name, idx, "amount", raw_amount_str, "Amount must be an integer string")
        raw_amount_int = int(raw_amount_str)
        ledger_amount_dec = Decimal(raw_amount_str)

        entry_type = row.get("entry_type", "").strip().lower()
        if entry_type not in ("credit", "debit"):
            raise RowValidationError(filepath.name, idx, "entry_type", entry_type, "Entry type must be 'credit' or 'debit'")

        raw_ts_str = row.get("booked_at", "").strip()
        try:
            booked_at_dt = datetime.strptime(raw_ts_str, "%d-%m-%Y %H:%M")
        except ValueError as e:
            raise RowValidationError(filepath.name, idx, "booked_at", raw_ts_str, f"Invalid date format (expected DD-MM-YYYY HH:MM): {e}")

        provenance = SourceProvenance(
            source_system="LEDGER",
            source_file=str(filepath),
            source_row_index=idx,
            raw_timestamp=raw_ts_str,
            timezone_note="Source timestamp provides no timezone metadata; parsed as naive clock time. Timezone is unspecified.",
        )

        records.append(
            LedgerRecord(
                ledger_entry_id=ledger_id,
                gateway_transaction_id=txn_id,
                account_type=row.get("account_type", "").strip(),
                entry_type=entry_type,
                ledger_amount=ledger_amount_dec,
                raw_amount=raw_amount_int,
                booked_at=booked_at_dt,
                provenance=provenance,
            )
        )

    return records
