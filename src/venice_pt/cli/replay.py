from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from venice_pt.contracts.events import Event, EventKind, Phase
from venice_pt.store.eventlog import EventLog
from venice_pt.store.projections import (
    cost_meter,
    engagement_summary,
    findings_table,
    phase_progress,
)

console = Console()


def create_demo_events(engagement_id: str = "eng-demo") -> list[Event]:
    e0 = Event(
        engagement_id=engagement_id,
        phase=Phase.SCOPE,
        actor="system",
        kind=EventKind.ENGAGEMENT_START,
        payload={"target": "http://127.0.0.1:3000"},
    )
    e1 = Event(
        engagement_id=engagement_id,
        phase=Phase.RECON,
        actor="runner",
        kind=EventKind.CMD,
        tool="nmap",
        cmd="nmap -sV -p 80,443 127.0.0.1",
        parent_id=e0.id,
        duration_ms=1200,
    )
    e2 = Event(
        engagement_id=engagement_id,
        phase=Phase.RECON,
        actor="parser",
        kind=EventKind.FACT,
        tool="nmap",
        payload={"kind": "port", "key": "port:127.0.0.1:80/tcp", "service": "http"},
        parent_id=e1.id,
    )
    e3 = Event(
        engagement_id=engagement_id,
        phase=Phase.VULN_SCAN,
        actor="runner",
        kind=EventKind.FINDING,
        tool="nuclei",
        payload={
            "id": "find-001",
            "title": "Open Directory Listing",
            "cls": "misconfig",
            "severity": "medium",
            "confidence": 0.8,
            "verified": False,
        },
        parent_id=e2.id,
        tokens_in=150,
        tokens_out=60,
        cost_usd=0.003,
    )
    e4 = Event(
        engagement_id=engagement_id,
        phase=Phase.VALIDATE,
        actor="verifier",
        kind=EventKind.VERDICT,
        payload={"finding_id": "find-001", "confirmed": True, "confidence_delta": 0.2},
        parent_id=e3.id,
    )
    e5 = Event(
        engagement_id=engagement_id,
        phase=Phase.REPORT,
        actor="system",
        kind=EventKind.ENGAGEMENT_END,
        parent_id=e4.id,
    )
    return [e0, e1, e2, e3, e4, e5]


def replay_engagement(db_path: Path | str, engagement_id: str) -> None:
    event_log = EventLog(db_path)
    events = event_log.get_events(engagement_id)
    if not events:
        console.print(f"[bold red]No events found for engagement: {engagement_id}[/bold red]")
        return

    summary = engagement_summary(events)
    progress = phase_progress(events)
    findings = findings_table(events)
    costs = cost_meter(events)

    console.print(f"[bold cyan]Replaying Engagement: {engagement_id}[/bold cyan]")
    status_str = summary["status"]
    evt_cnt = summary["event_count"]
    console.print(f"Status: [bold green]{status_str}[/bold green] | Total Events: {evt_cnt}")
    console.print(f"Phases Visited: {', '.join(summary['phases_visited'])}")
    console.print(f"Current Phase: [bold yellow]{progress['current_phase']}[/bold yellow]")

    # Findings Table
    if findings:
        table = Table(title="Reconstructed Findings")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="magenta")
        table.add_column("Severity", style="red")
        table.add_column("Confidence", justify="right")
        table.add_column("Verified", style="green")

        for f in findings:
            table.add_row(
                f["id"],
                f["title"],
                f["severity"],
                f"{f['confidence']:.2f}",
                str(f["verified"]),
            )
        console.print(table)

    cost_val = costs["total_cost_usd"]
    tok_val = costs["total_tokens"]
    dur_val = costs["total_duration_s"]
    console.print(f"Cost: ${cost_val} | Tokens: {tok_val} | Duration: {dur_val}s")
