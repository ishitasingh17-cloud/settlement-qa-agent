"""
server/models/domain.py

Canonical Pydantic domain models for PS-8 Settlement Q&A Agent (Phase 2).
Represents normalized financial entity models for Gateway, Bank, and Ledger records.
Adheres strictly to docs/rules.md:
- No floating-point financial arithmetic (uses Decimal and integer minor units)
- Preserves source identifiers distinctly (gateway_transaction_id, order_id, settlement_id, UTR, ledger_entry_id)
- Tracks source provenance (file, row index, system, raw timestamp)
- Preserves raw source values alongside normalized representations for epistemic integrity
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class SourceProvenance(BaseModel):
    """Tracks the exact physical source and location of ingested evidence."""
    source_system: Literal["GATEWAY", "BANK", "LEDGER"]
    source_file: str
    source_row_index: int = Field(
        ...,
        description="1-based physical CSV line number, including header (line 1 = header, line 2 = first data row)",
        ge=2,
    )
    raw_timestamp: Optional[str] = None
    timezone_note: str = Field(
        default="Source timestamp provides no timezone metadata; timezone is unspecified.",
        description="Explicit documentation of timezone handling per source"
    )

    model_config = ConfigDict(frozen=True)


class GatewayRecord(BaseModel):
    """Canonical model for a payment gateway transaction capture log."""
    gateway_transaction_id: str = Field(..., description="Unique transaction ID in gateway (e.g. pay_Gz8x1000)")
    order_id: str = Field(..., description="Merchant order ID (e.g. order_Odx1000)")
    gross_amount: Decimal = Field(..., description="Gross transaction amount represented as Decimal")
    raw_amount: int = Field(..., description="Raw integer amount from source (amount_in_cents)")
    currency: str = Field(default="INR", description="Three-letter ISO currency code")
    status: Literal["captured", "failed"] = Field(..., description="Normalized gateway payment status")
    source_status: str = Field(..., description="Original raw status string from CSV")
    method: str = Field(..., description="Payment instrument (e.g. netbanking, card, wallet, upi)")
    email: Optional[str] = Field(default=None, description="Customer contact email")
    contact: Optional[str] = Field(default=None, description="Customer phone number")
    error_code: Optional[str] = Field(default=None, description="Failure reason code if failed")
    error_description: Optional[str] = Field(default=None, description="Detailed failure description if failed")
    created_at: datetime = Field(..., description="Canonical transaction creation timestamp")
    provenance: SourceProvenance = Field(..., description="Source file provenance metadata")

    model_config = ConfigDict(frozen=True)


class BankRecord(BaseModel):
    """Canonical model for a bank clearing network settlement record."""
    settlement_id: str = Field(..., description="Unique settlement batch ID (e.g. set_Bnk9x2001)")
    gateway_transaction_id: str = Field(..., description="Cross-system transaction reference")
    net_settlement_amount: Decimal = Field(..., description="Disbursed settlement amount to merchant as Decimal")
    raw_amount: int = Field(..., description="Raw integer amount from source (net_settled_amount)")
    bank_reference_number: str = Field(..., description="Bank UTR / clearing reference (e.g. UTR721609600)")
    settlement_status: Literal["processed", "failed", "pending"] = Field(..., description="Normalized bank settlement status")
    source_status: str = Field(..., description="Original raw status string from CSV")
    settled_at: Optional[datetime] = Field(default=None, description="Settlement clearing timestamp (None if failed)")
    provenance: SourceProvenance = Field(..., description="Source file provenance metadata")

    model_config = ConfigDict(frozen=True)


class LedgerRecord(BaseModel):
    """Canonical model for an internal double-entry accounting ledger entry."""
    ledger_entry_id: str = Field(..., description="Unique journal entry ID (e.g. led_Lgr1x3001)")
    gateway_transaction_id: str = Field(..., description="Cross-system transaction reference")
    account_type: str = Field(..., description="Target ledger account (e.g. merchant_payout_pool)")
    entry_type: Literal["credit", "debit"] = Field(..., description="Accounting entry direction")
    ledger_amount: Decimal = Field(..., description="Amount booked to the ledger account as Decimal")
    raw_amount: int = Field(..., description="Raw integer amount from source (amount)")
    booked_at: datetime = Field(..., description="Ledger posting/booking timestamp")
    provenance: SourceProvenance = Field(..., description="Source file provenance metadata")

    model_config = ConfigDict(frozen=True)
