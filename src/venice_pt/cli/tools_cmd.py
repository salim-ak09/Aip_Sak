from __future__ import annotations

from rich.console import Console
from rich.table import Table

from venice_pt.bootstrap.resolver import Resolver
from venice_pt.registry.loader import ToolRegistry

console = Console()


def list_tools_command() -> None:
    registry = ToolRegistry()
    resolver = Resolver()
    tools = registry.list_tools()

    table = Table(title="aip_Sak Available Tool Catalogue")
    table.add_column("Tool", style="bold cyan")
    table.add_column("Binary", style="magenta")
    table.add_column("Phases", style="green")
    table.add_column("Installed", justify="center")
    table.add_column("Capabilities")

    for t in tools:
        installed = resolver.is_installed(t)
        inst_styled = (
            "[bold green]YES[/bold green]" if installed else "[bold red]NO[/bold red]"
        )
        phases_str = ", ".join(p.value for p in t.phases)
        caps_str = ", ".join(t.capabilities)
        table.add_row(t.name, t.binary, phases_str, inst_styled, caps_str)

    console.print(table)
