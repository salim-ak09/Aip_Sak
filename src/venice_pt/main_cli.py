from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from venice_pt import __version__
from venice_pt.logging import setup_logging

app = typer.Typer(
    name="AIP_SAK",
    help="AIP_SAK — Autonomous AI Pentest Platform.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        msg = f"[bold cyan]AIP_SAK[/bold cyan] version [bold green]{__version__}[/bold green]"
        console.print(msg)
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the application version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable debug logging.",
    ),
    json_logs: bool = typer.Option(
        False,
        "--json-logs",
        help="Output structured JSON logs.",
    ),
) -> None:
    level = "DEBUG" if verbose else "INFO"
    setup_logging(level=level, json_format=json_logs)


@app.command()
def init(
    name: str | None = typer.Argument(
        None, help="Name or slug of the engagement to initialize"
    ),
    target: str = typer.Option(
        "http://127.0.0.1:3000", "--target", "-t", help="Primary target domain, URL or IP"
    ),
) -> None:
    """Initialize a new engagement workspace."""
    from venice_pt.cli.init_cmd import init_engagement

    init_engagement(name=name, target=target)


@app.command()
def doctor(
    json_output: bool = typer.Option(
        False, "--json", help="Output diagnostic results in JSON format."
    ),
    install: bool = typer.Option(
        False, "--install", help="Attempt automatic installation for missing tools."
    ),
) -> None:
    """Verify system requirements and toolchain readiness."""
    from venice_pt.cli.doctor import doctor_command

    doctor_command(json_output=json_output, install=install)


@app.command()
def run(
    target: str = typer.Option(..., "--target", "-t", help="Target URL, IP or domain"),
    engagement: str | None = typer.Option(None, "--engagement", "-e", help="Engagement name"),
    profile: str = typer.Option(
        "web", "--profile", "-p", help="Engagement profile (web, network, full)"
    ),
    risk: str = typer.Option(
        "safe", "--risk", "-r", help="Risk ceiling: passive, safe, intrusive, destructive"
    ),
    budget: float = typer.Option(5.0, "--budget", "-b", help="Max spend budget in USD"),
    phases: str | None = typer.Option(
        None, "--phases", help="Comma-separated list of phases to run (e.g. recon,enum)"
    ),
    resume: bool = typer.Option(
        False, "--resume", help="Resume an interrupted engagement from checkpoint"
    ),
    no_llm: bool = typer.Option(
        False, "--no-llm", help="Run with deterministic static rules only"
    ),
) -> None:
    """Run an automated pentest engagement."""
    from venice_pt.cli.run_cmd import run_engagement

    asyncio.run(
        run_engagement(
            target=target,
            engagement_name=engagement,
            profile=profile,
            risk=risk,
            budget=budget,
            phases_filter=phases,
            resume=resume,
            no_llm=no_llm,
        )
    )


@app.command()
def status(
    engagement: str | None = typer.Option(None, "--engagement", "-e", help="Engagement slug"),
) -> None:
    """Show live progress and statistics for active engagements."""
    from venice_pt.cli.status_cmd import show_status

    show_status(engagement_slug=engagement)


@app.command()
def scope(
    engagement: str = typer.Option(..., "--engagement", "-e", help="Engagement slug to inspect"),
) -> None:
    """Inspect engagement target scope."""
    from venice_pt.cli.scope_cmd import show_scope

    show_scope(engagement_slug=engagement)


@app.command()
def tools() -> None:
    """List available and installed pentest tools."""
    from venice_pt.cli.tools_cmd import list_tools_command

    list_tools_command()


@app.command()
def replay(
    engagement: str = typer.Option(
        "eng-demo", "--engagement", "-e", help="Engagement ID to replay"
    ),
    demo: bool = typer.Option(False, "--demo", help="Replay demo synthetic event log"),
) -> None:
    """Replay event log and reconstruct read projections."""
    from venice_pt.cli.replay import create_demo_events, replay_engagement
    from venice_pt.config import config
    from venice_pt.store.eventlog import EventLog

    if demo:
        config.ensure_directories()
        demo_db = config.engagements_dir / "demo_events.db"
        event_log = EventLog(demo_db)
        events = create_demo_events("eng-demo")
        event_log.append_many(events)
        replay_engagement(demo_db, "eng-demo")
    else:
        eng_db = config.engagements_dir / engagement / "events.db"
        replay_engagement(eng_db, engagement)


@app.command()
def report(
    engagement: str = typer.Option(
        ..., "--engagement", "-e", help="Engagement ID or slug"
    ),
    format: str = typer.Option(
        "html,sarif,csv", "--format", "-f", help="Output format: html, sarif, csv"
    ),
    output_dir: str = typer.Option("./reports", "--output-dir", "-o", help="Output directory"),
) -> None:
    """Generate final executive and technical assessment reports."""
    from pathlib import Path

    from venice_pt.cli.report_cmd import generate_report

    generate_report(engagement=engagement, output_dir=Path(output_dir), formats=format)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Server host"),
    port: int = typer.Option(8000, "--port", help="Server port"),
) -> None:
    """Start the API and WebSocket server."""
    from venice_pt.cli.serve_cmd import serve_api

    console.print(f"[bold green]Serving API and WebSockets on {host}:{port}...[/bold green]")
    serve_api(host=host, port=port)


@app.command()
def exec(
    tool: str = typer.Option(..., "--tool", help="Tool name to execute"),
    args: str = typer.Option("", "--args", help="Arguments to pass to tool"),
    target: str = typer.Option(..., "--target", help="Target domain, URL or IP"),
    engagement: str = typer.Option("default", "--engagement", help="Engagement ID"),
) -> None:
    """Execute a single tool via the execution runner choke point."""
    from venice_pt.cli.exec_cmd import exec_command

    exec_command(tool=tool, args=args, target=target, engagement=engagement)


@app.command()
def watch(
    target: str = typer.Option(..., "--target", "-t", help="Target to monitor continuously"),
    once: bool = typer.Option(False, "--once", help="Run a single check cycle and exit"),
    interval: int = typer.Option(3600, "--interval", help="Cycle interval in seconds"),
) -> None:
    """Start continuous 24/7 watch daemon."""
    from venice_pt.cli.watch_cmd import run_watch

    run_watch(target=target, once=once, interval=interval)


if __name__ == "__main__":
    app()
