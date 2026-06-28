"""Shared pytest fixtures and helpers.

These unit tests are intentionally lightweight: they avoid importing the top-level
``src`` package (which transitively imports torch/chromadb) so that ``pytest`` runs
fast in CI without the heavy model dependencies. Standalone modules are loaded directly
by file path.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def load_module(name: str, relpath: str):
    """Load a standalone module by file path, bypassing package __init__."""
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def metrics():
    return load_module("pg_metrics", "src/evaluation/metrics.py")


@pytest.fixture(scope="session")
def project_root():
    return ROOT


def _read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
