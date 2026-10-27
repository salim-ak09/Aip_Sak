from __future__ import annotations

from rich.console import Console
from rich.table import Table

from venice_pt.config import config
from venice_pt.exec.scope import ScopeDefinition

console = Console()


def show_scope(engagement_slug: str) -> None:
    scope_path = config.engagements_dir / engagement_slug / "scope.yaml"
    if not scope_path.exists():
        console.print(f"[bold red]Scope file not found at: {scope_path}[/bold red]")
        return

    scope = ScopeDefinition.from_yaml(scope_path)
    console.print(f"[bold cyan]Scope configuration for: {engagement_slug}[/bold cyan]")

    table = Table(title="Target Scope Rules")
    table.add_column("Type", style="cyan")
    table.add_column("Rules", style="green")

    inc_rules = [str(c) for c in scope.included_cidrs] + scope.included_domains
    exc_rules = [str(c) for c in scope.excluded_cidrs] + scope.excluded_domains

    table.add_row("Included", ", ".join(inc_rules) or "[italic]None specified[/italic]")
    table.add_row("Excluded", ", ".join(exc_rules) or "[italic]None specified[/italic]")

    console.print(table)
