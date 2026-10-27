from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from venice_pt.bootstrap.doctor import run_doctor
from venice_pt.bootstrap.lockfile import ToolchainLock
from venice_pt.bootstrap.resolver import Resolver
from venice_pt.registry.loader import ToolRegistry
from venice_pt.registry.schema import ManifestSchemaError, validate_manifest_dict


def test_manifest_loader_and_count() -> None:
    registry = ToolRegistry()
    tools = registry.list_tools()
    # Exactly the 8 required manifests for P3
    assert len(tools) == 8
    names = {t.name for t in tools}
    assert names == {
        "nmap",
        "httpx",
        "subfinder",
        "nuclei",
        "ffuf",
        "katana",
        "dnsx",
        "whatweb",
    }


def test_strict_manifest_validation() -> None:
    """SPEC requirement: strict validation (unknown keys = error)."""
    invalid_manifest = {
        "name": "fake_tool",
        "binary": "fake",
        "capabilities": ["scan"],
        "phases": ["recon"],
        "risk": 1,
        "install": [],
        "check": "--version",
        "output": {"format": "text", "parser": "dummy", "normalizes_to": []},
        "unknown_extra_field": "disallowed",  # Should trigger error
    }
    with pytest.raises(ManifestSchemaError):
        validate_manifest_dict(invalid_manifest)


def test_resolver_fallback_ordering(tmp_path: Path) -> None:
    """SPEC requirement: fake shutil.which to simulate missing tools; assert fallback ordering."""
    registry = ToolRegistry()
    nmap_spec = registry.get("nmap")
    assert nmap_spec is not None

    lockfile_path = tmp_path / "toolchain.lock"
    resolver = Resolver(toolchain_bin=tmp_path / "bin", lockfile_path=lockfile_path)

    # Simulate: nmap binary not found on host, package manager is apt
    with (
        patch("shutil.which", return_value=None),
        patch("venice_pt.bootstrap.resolver.detect_package_manager", return_value="apt"),
        patch.object(resolver, "_install_via_pkg_mgr", return_value=True) as mock_apt,
    ):
        result = resolver.ensure(nmap_spec)
        assert result == "installed_via_apt"
        mock_apt.assert_called_once_with("apt", "nmap")

        # Verify lockfile recorded
        lock = ToolchainLock.load(lockfile_path)
        assert "nmap" in lock.tools
        assert lock.tools["nmap"].method == "apt"


def test_second_run_is_noop_under_2s(tmp_path: Path) -> None:
    """SPEC requirement: assert second run is a no-op under 2s."""
    registry = ToolRegistry()
    tools = registry.list_tools()
    lockfile_path = tmp_path / "toolchain.lock"
    resolver = Resolver(toolchain_bin=tmp_path / "bin", lockfile_path=lockfile_path)

    # When all tools are found, ensure is a no-op
    with patch("shutil.which", return_value="/usr/bin/tool"):
        t0 = time.perf_counter()
        for spec in tools:
            res = resolver.ensure(spec)
            assert res == "already_installed"
        elapsed = time.perf_counter() - t0
        assert elapsed < 2.0, f"Second run took {elapsed:.3f}s, expected < 2.0s"


def test_doctor_json_output() -> None:
    with patch("shutil.which", return_value="/usr/bin/tool"):
        code = run_doctor(json_output=True, install_missing=False)
        assert code == 0
