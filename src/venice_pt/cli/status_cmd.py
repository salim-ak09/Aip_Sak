from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from venice_pt.brain.checkpoint import Checkpoint
from venice_pt.config import config
from venice_pt.store.eventlog import EventLog
from venice_pt.store.projections import findings_table

console = Console()


def show_status(engagement_slug: str | None = None) -> None:
    eng_dirs: list[Path] = []
    if engagement_slug:
        target_dir = config.engagements_dir / engagement_slug
        if target_dir.exists():
            eng_dirs.append(target_dir)
    elif config.engagements_dir.exists():
        eng_dirs = [d for d in config.engagements_dir.iterdir() if d.is_dir()]

    if not eng_dirs:
        console.print("[bold yellow]No active or past engagements found.[/bold yellow]")
        return

    table = Table(title="aip_Sak Engagement Status")
    table.add_column("Engagement", style="bold cyan")
    table.add_column("Status", justify="center")
    table.add_column("Current Phase", style="magenta")
    table.add_column("Events", justify="right")
    table.add_column("Findings", justify="right", style="red")

    for eng in eng_dirs:
        chk_file = eng / "state.json"
        db_file = eng / "events.db"
        status = "unknown"
        phase = "n/a"
        events_cnt = 0
        findings_cnt = 0

        if chk_file.exists():
            chk = Checkpoint.load(chk_file)
            if chk:
                status = chk.status
                phase = chk.current_phase.value
                findings_cnt = chk.findings_count

        if db_file.exists():
            log = EventLog(db_file)
            events = log.get_events(eng.name)
            events_cnt = len(events)
            findings = findings_table(events)
            findings_cnt = len(findings)

        status_style = (
            "[bold green]completed[/bold green]"
            if status == "completed"
            else (
                "[bold yellow]running[/bold yellow]"
                if status == "running"
                else f"[bold white]{status}[/bold white]"
            )
        )
        table.add_row(eng.name, status_style, phase, str(events_cnt), str(findings_cnt))

    console.print(table)
