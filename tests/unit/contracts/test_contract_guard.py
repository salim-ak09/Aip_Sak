from __future__ import annotations

from pathlib import Path

from venice_pt.contracts._hash import compute_contracts_hash
from venice_pt.contracts.events import CONTRACT_VERSION

CONTRACT_HASH_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "src"
    / "venice_pt"
    / "contracts"
    / "CONTRACT_HASH"
)


def test_contracts_hash_guard() -> None:
    """Fails if contract modules change without bumping CONTRACT_VERSION and updating hash."""
    assert CONTRACT_HASH_FILE.exists(), "CONTRACT_HASH file is missing!"
    expected_hash = CONTRACT_HASH_FILE.read_text(encoding="utf-8").strip()
    actual_hash = compute_contracts_hash()

    assert actual_hash == expected_hash, (
        f"Contract hash mismatch! Core contracts have been modified.\n"
        f"Actual hash:   {actual_hash}\n"
        f"Expected hash: {expected_hash}\n"
        f"Rules mandate: Never modify contracts/ without bumping CONTRACT_VERSION "
        f"(currently {CONTRACT_VERSION}) and updating docs/CONTRACTS.md."
    )
