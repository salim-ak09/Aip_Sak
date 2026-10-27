from __future__ import annotations

import hashlib
from pathlib import Path

CONTRACTS_DIR = Path(__file__).resolve().parent

CORE_SCHEMAS = [
    "decisions.py",
    "events.py",
    "facts.py",
    "findings.py",
    "llm.py",
    "tools.py",
]


def compute_contracts_hash() -> str:
    """Computes a deterministic SHA256 hash over all core contract Python files."""
    hasher = hashlib.sha256()
    for name in sorted(CORE_SCHEMAS):
        file_path = CONTRACTS_DIR / name
        hasher.update(name.encode("utf-8"))
        hasher.update(file_path.read_bytes())
    return hasher.hexdigest()
