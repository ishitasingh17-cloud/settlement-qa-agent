#!/usr/bin/env python3
"""
scripts/profile_dataset.py

Dataset profiling script for PS-8 Settlement Q&A Agent (Phase 1).
Inspects structural integrity, column schemas, identifier uniqueness,
cross-dataset key linkages, and scenario representations without modifying source CSVs.
"""

import csv
import sys
from pathlib import Path
from collections import Counter, defaultdict

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

GATEWAY_FILE = DATA_DIR / "gateway.csv"
BANK_FILE = DATA_DIR / "bank.csv"
LEDGER_FILE = DATA_DIR / "ledger.csv"


def load_csv_data(filepath: Path):
    if not filepath.exists():
        raise FileNotFoundError(f"Missing required dataset: {filepath}")
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    return fieldnames, rows


def profile_file(name: str, filepath: Path):
    fieldnames, rows = load_csv_data(filepath)
    total_rows = len(rows)
    null_counts = defaultdict(int)

    for row in rows:
        for col in fieldnames:
            val = row.get(col, "")
            if val is None or val.strip() == "":
                null_counts[col] += 1

    return {
        "name": name,
        "path": str(filepath),
        "total_rows": total_rows,
        "columns": fieldnames,
        "column_count": len(fieldnames),
        "null_counts": dict(null_counts),
        "rows": rows,
    }


def main():
    print("=" * 70)
    print("PS-8 Settlement Q&A Agent — Mock Financial Dataset Profile")
    print("=" * 70)

    gw_prof = profile_file("Gateway Capture Logs", GATEWAY_FILE)
    bnk_prof = profile_file("Bank Clearing Records", BANK_FILE)
    led_prof = profile_file("Internal Accounting Ledger", LEDGER_FILE)

    for prof in [gw_prof, bnk_prof, led_prof]:
        print(f"\n[{prof['name']}] -> {Path(prof['path']).name}")
        print(f"  Row Count: {prof['total_rows']}")
        print(f"  Column Count: {prof['column_count']}")
        print(f"  Columns: {', '.join(prof['columns'])}")
        print("  Missing Values:")
        for col in prof["columns"]:
            cnt = prof["null_counts"].get(col, 0)
            pct = (cnt / prof["total_rows"] * 100) if prof["total_rows"] > 0 else 0
            print(f"    - {col}: {cnt} ({pct:.1f}%)")

    # Cross-dataset linkage audit
    gw_txns = {r["gateway_transaction_id"]: r for r in gw_prof["rows"]}
    bnk_txns = {r["gateway_transaction_id"]: r for r in bnk_prof["rows"]}
    led_txns = {r["gateway_transaction_id"]: r for r in led_prof["rows"]}

    all_txns = set(gw_txns.keys()) | set(bnk_txns.keys()) | set(led_txns.keys())
    print("\n" + "=" * 70)
    print("Cross-Dataset Linkage Analysis")
    print("=" * 70)
    print(f"Total Unique Transaction IDs across all files: {len(all_txns)}")
    print(f"  - In Gateway: {len(gw_txns)}")
    print(f"  - In Bank:    {len(bnk_txns)}")
    print(f"  - In Ledger:  {len(led_txns)}")

    in_all_three = set(gw_txns.keys()) & set(bnk_txns.keys()) & set(led_txns.keys())
    gw_only = set(gw_txns.keys()) - set(bnk_txns.keys()) - set(led_txns.keys())
    gw_bnk_no_led = (set(gw_txns.keys()) & set(bnk_txns.keys())) - set(led_txns.keys())
    bnk_led_no_gw = (set(bnk_txns.keys()) & set(led_txns.keys())) - set(gw_txns.keys())

    print(f"  - In all 3 datasets: {len(in_all_three)}")
    print(f"  - In Gateway only (Missing Bank & Ledger): {len(gw_only)} -> {sorted(list(gw_only))}")
    print(f"  - In Gateway & Bank, missing Ledger: {len(gw_bnk_no_led)} -> {sorted(list(gw_bnk_no_led))}")
    print(f"  - In Bank & Ledger, missing Gateway: {len(bnk_led_no_gw)} -> {sorted(list(bnk_led_no_gw))}")

    # Status distribution
    print("\n" + "=" * 70)
    print("Status Distributions")
    print("=" * 70)
    print("Gateway statuses:", Counter(r["status"] for r in gw_prof["rows"]))
    print("Bank statuses:   ", Counter(r["settlement_status"] for r in bnk_prof["rows"]))
    print("Ledger types:    ", Counter(r["entry_type"] for r in led_prof["rows"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
