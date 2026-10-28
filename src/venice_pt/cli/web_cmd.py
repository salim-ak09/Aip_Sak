from __future__ import annotations

import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()


def run_web(
    host: str = "127.0.0.1",
    api_port: int = 8000,
    ui_port: int = 5173,
    no_browser: bool = False,
) -> None:
    """Launches both the FastAPI backend and React Vite UI, then opens the browser."""
    root_dir = Path(__file__).resolve().parents[3]
    ui_dir = root_dir / "ui"

    banner_msg = (
        f"[bold cyan]🛡️ AIP_SAK Command Center Launching...[/bold cyan]\n"
        f"[dim]• Backend API:[/dim] [green]http://{host}:{api_port}[/green]\n"
        f"[dim]• Web UI:[/dim]      [bold yellow]http://localhost:{ui_port}[/bold yellow]\n"
        f"[dim]Press [bold red]Ctrl+C[/bold red] to stop all services.[/dim]"
    )
    console.print(Panel.fit(banner_msg, border_style="cyan"))

    # 1. Start FastAPI backend server in subprocess
    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "venice_pt.server.app:app",
        "--host",
        host,
        "--port",
        str(api_port),
    ]

    api_proc = subprocess.Popen(
        api_cmd,
        cwd=str(root_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 2. Check if Vite UI dev server or build exists
    ui_proc = None
    if ui_dir.exists():
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        ui_proc = subprocess.Popen(
            [npm_cmd, "run", "dev", "--", "--port", str(ui_port)],
            cwd=str(ui_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # Allow servers to start
    time.sleep(2)

    ui_url = f"http://localhost:{ui_port}"
    if not no_browser:
        console.print(f"[bold green]Opening browser at {ui_url}...[/bold green]")
        try:
            webbrowser.open(ui_url)
        except Exception:
            pass

    console.print("[green]✔ Command Center running. Watching active engagements live...[/green]")

    def handle_shutdown(signum: int | None = None, frame: object | None = None) -> None:
        console.print("\n[yellow]Stopping AIP_SAK services...[/yellow]")
        if api_proc and api_proc.poll() is None:
            api_proc.terminate()
        if ui_proc and ui_proc.poll() is None:
            ui_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        while True:
            time.sleep(1)
            if api_proc.poll() is not None:
                console.print("[red]API server terminated unexpectedly.[/red]")
                break
    except KeyboardInterrupt:
        handle_shutdown()
