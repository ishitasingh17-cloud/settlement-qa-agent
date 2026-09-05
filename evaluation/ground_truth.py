"""
evaluation/ground_truth.py

Loader for the independently generated frozen benchmark ground truth dataset.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from evaluation.models import BenchmarkCase


def get_ground_truth_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "benchmark_ground_truth.json"


def load_benchmark_ground_truth() -> Dict[str, Any]:
    path = get_ground_truth_path()
    if not path.exists():
        raise FileNotFoundError(f"Benchmark ground truth file missing: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_benchmark_cases() -> List[BenchmarkCase]:
    data = load_benchmark_ground_truth()
    cases = []
    for c in data["cases"]:
        cases.append(BenchmarkCase.model_validate(c))
    return cases
