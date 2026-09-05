from pathlib import Path
import ast
import os
import pytest


def test_server_does_not_import_evaluation():
    server_dir = Path("server")
    evaluation_terms = ["evaluation", "benchmark_ground_truth"]
    
    violating_files = []
    
    for root, _, files in os.walk(server_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                content = file_path.read_text(encoding="utf-8")
                
                # Check AST imports
                tree = ast.parse(content, filename=str(file_path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if "evaluation" in alias.name:
                                violating_files.append((str(file_path), f"import {alias.name}"))
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and "evaluation" in node.module:
                            violating_files.append((str(file_path), f"from {node.module}"))
                            
    assert len(violating_files) == 0, f"Anti-cheating violation: server files reference evaluation: {violating_files}"


def test_ground_truth_not_imported_by_domain_engines():
    import server.tracing as tr
    import server.reconciliation as rec
    import server.diagnosis as diag
    import server.evidence as ev
    import server.api as api
    
    for module in [tr, rec, diag, ev, api]:
        mod_dict = module.__dict__
        for key, val in mod_dict.items():
            val_str = str(val)
            assert "benchmark_ground_truth" not in val_str, f"Found benchmark_ground_truth reference in {module.__name__}.{key}"
            assert "evaluation" not in getattr(val, "__module__", ""), f"Found evaluation module import in {module.__name__}.{key}"
