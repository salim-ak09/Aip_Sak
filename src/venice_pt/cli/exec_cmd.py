from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from venice_pt.contracts.events import Phase
from venice_pt.exec.runner import SubprocessRunner
from venice_pt.registry.loader import ToolRegistry

console = Console()


def exec_command(
    tool: str = typer.Option(..., "--tool", help="Tool name to execute (e.g. nmap, httpx)"),
    args: str = typer.Option("", "--args", help="Arguments to pass to tool"),
    target: str = typer.Option(..., "--target", help="Target domain, URL or IP"),
    engagement: str = typer.Option("default", "--engagement", help="Engagement ID"),
) -> None:
    registry = ToolRegistry()
    spec = registry.get(tool)
    if not spec:
        console.print(f"[bold red]Tool '{tool}' not found in registry.[/bold red]")
        raise typer.Exit(1)

    runner = SubprocessRunner()
    arg_list = args.split() if args else []
    # If target is provided and not already in args, append it
    if target and target not in arg_list:
        arg_list.append(target)

    console.print(f"[bold blue]Executing tool:[/bold blue] {tool} on {target}")
    result = asyncio.run(
        runner.execute(
            spec,
            arg_list,
            engagement_id=engagement,
            phase=Phase.RECON,
            target=target,
        )
    )

    console.print(f"Exit code: {result.exit_code} | Duration: {result.duration_s}s")
    console.print(f"Stdout artifact: {result.stdout_path}")
    console.print(f"Stderr artifact: {result.stderr_path}")
    if result.exit_code != 0 and result.error:
        console.print(f"[bold yellow]Execution note: {result.error}[/bold yellow]")
