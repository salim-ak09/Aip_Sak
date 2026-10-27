from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table

from venice_pt.bootstrap.distro import detect_system_info
from venice_pt.bootstrap.resolver import Resolver
from venice_pt.registry.loader import ToolRegistry

console = Console()


def run_doctor(json_output: bool = False, install_missing: bool = False) -> int:
    registry = ToolRegistry()
    resolver = Resolver()
    tools = registry.list_tools()
    sys_info = detect_system_info()

    results: list[dict[str, Any]] = []
    missing_count = 0

    for spec in tools:
        is_installed = resolver.is_installed(spec)
        action_taken = "none"

        if not is_installed and install_missing:
            try:
                action_taken = resolver.ensure(spec)
                is_installed = resolver.is_installed(spec)
            except Exception as e:
                action_taken = f"failed: {e}"

        if not is_installed:
            missing_count += 1

        version = resolver.get_tool_version(spec) if is_installed else None
        results.append(
            {
                "tool": spec.name,
                "binary": spec.binary,
                "capabilities": spec.capabilities,
                "status": "ready" if is_installed else "missing",
                "version": version or "n/a",
                "action": action_taken,
            }
        )

    if json_output:
        output_data = {
            "system": sys_info,
            "tools": results,
            "total_tools": len(tools),
            "missing_tools": missing_count,
        }
        console.print(json.dumps(output_data, indent=2))
        return 0 if missing_count == 0 else 1

    # Rich table output
    table = Table(title="aip_Sak Toolchain Diagnostics")
    table.add_column("Capability", style="cyan")
    table.add_column("Tool", style="bold magenta")
    table.add_column("Status", justify="center")
    table.add_column("Version", style="green")

    for r in results:
        status_styled = (
            "[bold green]READY[/bold green]"
            if r["status"] == "ready"
            else "[bold red]MISSING[/bold red]"
        )
        caps = ", ".join(r["capabilities"][:2])
        table.add_row(caps, r["tool"], status_styled, str(r["version"]))

    sys_str = (
        f"System: OS={sys_info['os']}, Arch={sys_info['arch']}, "
        f"PkgMgr={sys_info['package_manager']}"
    )
    console.print(sys_str)
    console.print(table)

    if missing_count > 0:
        console.print(
            f"[bold yellow]Found {missing_count} missing tool(s). "
            f"Run with --install to attempt automatic installation.[/bold yellow]"
        )
        return 1

    console.print("[bold green]All starter tools are verified and ready.[/bold green]")
    return 0
