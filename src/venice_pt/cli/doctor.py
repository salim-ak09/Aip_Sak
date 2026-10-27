from __future__ import annotations

import typer

from venice_pt.bootstrap.doctor import run_doctor


def doctor_command(
    json_output: bool = typer.Option(
        False, "--json", help="Output diagnostic results in JSON format."
    ),
    install: bool = typer.Option(
        False, "--install", help="Attempt automatic installation for missing tools."
    ),
) -> None:
    """Verify system requirements and toolchain readiness."""
    code = run_doctor(json_output=json_output, install_missing=install)
    if code != 0:
        raise typer.Exit(code)
