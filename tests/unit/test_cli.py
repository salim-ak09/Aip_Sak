from __future__ import annotations

from typer.testing import CliRunner

from venice_pt import __version__
from venice_pt.cli import app
from venice_pt.config import VeniceConfig

runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "AIP_SAK" in result.stdout
    assert "init" in result.stdout
    assert "doctor" in result.stdout
    assert "run" in result.stdout
    assert "replay" in result.stdout
    assert "report" in result.stdout
    assert "serve" in result.stdout
    assert "watch" in result.stdout


def test_config_defaults() -> None:
    cfg = VeniceConfig()
    assert cfg.default_risk_ceiling == 1
    assert cfg.default_budget_usd == 5.0
    assert cfg.engagements_dir.name == "engagements"
