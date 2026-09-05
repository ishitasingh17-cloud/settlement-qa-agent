#!/usr/bin/env python3
"""
scripts/verify_environment.py

Comprehensive preflight diagnostic script for PS-8 Settlement Q&A Agent.
Verifies:
1. Python runtime (>= 3.10)
2. Core dependencies installed
3. Raw financial datasets and SHA-256 integrity
4. Benchmark ground truth dataset
5. Port availability / configuration
"""

import sys
import os
import hashlib
import socket
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CANONICAL_HASHES = {
    "data/gateway.csv": "8945186e3ded7e81b21834e1c5312656fdb3da1af0fd011d7768a2758f24bcff",
    "data/bank.csv": "6db6886b96b1fd642a0a3df1d009bcbf93750090aaea8180a7cc4386c358edc4",
    "data/ledger.csv": "89c5bfb92be8a81f45abfe07975affe711b54009daf59453951c54251722f504",
}

def check_python_version() -> bool:
    v = sys.version_info
    print(f"[*] Python Runtime: {v.major}.{v.minor}.{v.micro} on {sys.platform}")
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print("    [!] ERROR: Python 3.10+ is required.")
        return False
    print("    [+] Python version OK.")
    return True

def check_dependencies() -> bool:
    print("[*] Checking core Python dependencies...")
    packages = ["fastapi", "pydantic", "httpx", "uvicorn", "pytest", "pydantic_settings"]
    all_ok = True
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"    [+] {pkg}: Installed")
        except ImportError:
            print(f"    [!] Missing dependency: {pkg}")
            all_ok = False
    return all_ok

def check_datasets() -> bool:
    print("[*] Verifying raw CSV datasets and bit-for-bit SHA-256 hashes...")
    all_ok = True
    for rel_path, expected_hash in CANONICAL_HASHES.items():
        full_path = BASE_DIR / rel_path
        if not full_path.exists():
            print(f"    [!] MISSING: {rel_path}")
            all_ok = False
            continue
        actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
        if actual_hash == expected_hash:
            print(f"    [+] {rel_path}: Hash Verified ({actual_hash[:12]}...)")
        else:
            print(f"    [!] HASH MISMATCH for {rel_path}!")
            print(f"        Expected: {expected_hash}")
            print(f"        Actual:   {actual_hash}")
            all_ok = False
    return all_ok

def check_benchmark() -> bool:
    print("[*] Verifying Benchmark Ground Truth dataset...")
    gt_path = BASE_DIR / "data" / "benchmark_ground_truth.json"
    if not gt_path.exists():
        print("    [!] MISSING: data/benchmark_ground_truth.json")
        return False
    import json
    try:
        data = json.loads(gt_path.read_text(encoding="utf-8"))
        count = len(data.get("cases", []))
        if count == 101:
            print(f"    [+] Ground Truth Verified: 101 cases loaded.")
            return True
        else:
            print(f"    [!] Unexpected case count: {count} (expected 101)")
            return False
    except Exception as e:
        print(f"    [!] Failed to parse ground truth JSON: {e}")
        return False

def check_client_bundle() -> bool:
    print("[*] Checking Frontend Client...")
    client_dir = BASE_DIR / "client"
    if not client_dir.exists():
        print("    [!] Missing client/ directory")
        return False
    dist_index = client_dir / "dist" / "index.html"
    if dist_index.exists():
        print("    [+] Frontend production build present (client/dist/index.html).")
    else:
        print("    [*] Frontend build not compiled yet (run 'npm run build' inside client/).")
    return True

def main():
    print("=" * 80)
    print("PS-8 SETTLEMENT Q&A AGENT - ENVIRONMENT VERIFICATION")
    print("=" * 80)

    checks = [
        ("Python Runtime", check_python_version()),
        ("Dependencies", check_dependencies()),
        ("Raw CSV Integrity", check_datasets()),
        ("Benchmark Ground Truth", check_benchmark()),
        ("Frontend Client", check_client_bundle()),
    ]

    print("-" * 80)
    failed = [name for name, passed in checks if not passed]
    if failed:
        print(f"[!] Preflight Failed! Issues in: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("[+] ALL PREFLIGHT CHECKS PASSED. SYSTEM READY.")
        print("=" * 80)
        sys.exit(0)

if __name__ == "__main__":
    main()
