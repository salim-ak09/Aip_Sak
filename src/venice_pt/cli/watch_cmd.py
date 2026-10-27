from __future__ import annotations

import asyncio
from typing import Any

import typer

from venice_pt.watch.scheduler import WatchScheduler


def run_watch(target: str, once: bool = False, interval: int = 3600) -> None:
    """Executes attack surface monitoring."""
    scheduler = WatchScheduler(interval_seconds=float(interval))
    typer.echo(f"[*] Starting attack surface watch on {target}...")

    # Initial mock snapshot for target
    snapshot: dict[str, Any] = {
        "assets": [target],
        "ports": [
            {"host": target, "port": 80, "product": "apache", "version": "2.4.49"},
            {"host": target, "port": 443, "product": "nginx", "version": "1.24.0"},
        ],
    }

    drift = asyncio.run(scheduler.execute_cycle(snapshot))

    if drift.has_drift:
        typer.echo(
            f"[!] Drift detected: {len(drift.new_assets)} assets, {len(drift.new_ports)} ports"
        )
    else:
        typer.echo("[+] Surface baseline captured. No initial drift.")

    if once:
        typer.echo("[*] Single cycle completed (--once specified).")
        return

    typer.echo(f"[*] Monitoring loop active (interval={interval}s). Press Ctrl-C to terminate.")
    try:
        asyncio.run(scheduler.start())
    except KeyboardInterrupt:
        scheduler.stop()
        typer.echo("\n[*] Watch daemon halted.")
