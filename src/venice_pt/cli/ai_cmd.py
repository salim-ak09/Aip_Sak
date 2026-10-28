from __future__ import annotations

import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from venice_pt.brain.budget import BudgetGovernor
from venice_pt.brain.llm_client import OpenAICompatibleLLMClient
from venice_pt.config import config
from venice_pt.contracts.llm import LLMRole, Msg

console = Console()


async def check_ai_health(
    prompt: str = "Respond with 'AIP_SAK AI online' and 1 short sentence.",
) -> None:
    console.print("[bold cyan]>>> AIP_SAK AI Agent Diagnostics[/bold cyan]\n")

    table = Table(title="AI Agent Configuration", header_style="bold magenta")
    table.add_column("Setting", style="cyan", width=25)
    table.add_column("Current Value", style="white")

    if config.gemini_api_key:
        key_display = config.gemini_api_key[:6] + "..." + config.gemini_api_key[-4:]
    elif config.llm_api_key:
        key_display = config.llm_api_key[:6] + "..."
    else:
        key_display = "[red]Not configured[/red]"

    table.add_row("Provider", config.llm_provider.upper())
    table.add_row("Configured Key", key_display)
    table.add_row("Endpoint (API Base)", config.llm_api_base)
    table.add_row("Default Model", config.default_model)
    table.add_row("Max Budget USD", f"${config.default_budget_usd:.2f}")

    console.print(table)
    console.print("\n[yellow]Testing live connection to AI model...[/yellow]")

    governor = BudgetGovernor(max_budget_usd=config.default_budget_usd)
    client = OpenAICompatibleLLMClient(budget_governor=governor)

    t0 = time.perf_counter()
    try:
        res = await client.complete(
            role=LLMRole.PLANNER,
            messages=[Msg(role="user", content=prompt)],
            max_tokens=100,
        )
        latency = (time.perf_counter() - t0) * 1000

        result_table = Table(title="Connectivity & Performance Test", header_style="bold green")
        result_table.add_column("Metric", style="cyan", width=25)
        result_table.add_column("Result", style="green")

        result_table.add_row("Connection Status", "[bold green]ONLINE (200 OK)[/bold green]")
        result_table.add_row("Active Model Used", res.model)
        result_table.add_row(
            "Latency / Response Time",
            f"{latency:.0f} ms ({latency/1000:.2f} s)",
        )
        result_table.add_row("Tokens In / Out", f"{res.tokens_in} in / {res.tokens_out} out")
        result_table.add_row("Estimated Call Cost", f"${res.cost_usd:.6f}")

        console.print(result_table)
        console.print()
        console.print(
            Panel(
                res.text.strip(),
                title="[bold green]AI Agent Sample Output[/bold green]",
                border_style="green",
            )
        )

    except Exception as e:
        latency = (time.perf_counter() - t0) * 1000
        console.print(f"[bold red]Connection FAILED after {latency:.0f} ms:[/bold red] {e}")
        console.print("\n[yellow]Tips:[/yellow]")
        console.print("- Verify VENICEPT_GEMINI_API_KEY in your .env file")
        console.print("- Check your network connectivity to Google APIs")
        console.print("- Run 'aip-sak run --no-llm' to operate without AI dependencies")
