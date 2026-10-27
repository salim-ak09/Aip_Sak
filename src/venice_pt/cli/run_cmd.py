from __future__ import annotations

import asyncio

from rich.console import Console

from venice_pt.brain.budget import BudgetGovernor
from venice_pt.brain.checkpoint import Checkpoint
from venice_pt.brain.fsm import PentestFSM
from venice_pt.brain.interpreter import Interpreter
from venice_pt.brain.llm_client import OpenAICompatibleLLMClient
from venice_pt.brain.planner import PlannerEngine
from venice_pt.brain.router import StaticPolicyRouter
from venice_pt.cli.init_cmd import init_engagement, slugify
from venice_pt.config import config
from venice_pt.contracts.decisions import Action
from venice_pt.contracts.events import Event, EventKind, Phase, Risk
from venice_pt.contracts.facts import Fact, FactKind
from venice_pt.exec.runner import SubprocessRunner
from venice_pt.exec.scope import ScopeDefinition
from venice_pt.knowledge.graph import KnowledgeGraph
from venice_pt.parsers._registry import get_parser
from venice_pt.parsers.base import ParserContext
from venice_pt.registry.loader import ToolRegistry
from venice_pt.store.bus import EventBus
from venice_pt.store.eventlog import EventLog

console = Console()


async def run_engagement(
    target: str,
    engagement_name: str | None = None,
    profile: str = "web",
    risk: str = "safe",
    budget: float = 5.0,
    phases_filter: str | None = None,
    resume: bool = False,
    no_llm: bool = False,
) -> None:
    slug = slugify(engagement_name or target)
    eng_dir = config.engagements_dir / slug

    if not eng_dir.exists():
        init_engagement(name=slug, target=target)

    db_path = eng_dir / "events.db"
    chk_path = eng_dir / "state.json"
    scope_path = eng_dir / "scope.yaml"

    event_log = EventLog(db_path)
    event_bus = EventBus()
    scope = ScopeDefinition.from_yaml(scope_path)
    registry = ToolRegistry()
    graph = KnowledgeGraph()
    router = StaticPolicyRouter(registry=registry)
    budget_gov = BudgetGovernor(max_budget_usd=budget)
    fsm = PentestFSM()

    llm_client = None if no_llm else OpenAICompatibleLLMClient(budget_governor=budget_gov)
    planner = PlannerEngine(llm_client=llm_client, router=router, budget=budget_gov)
    interpreter = Interpreter(llm_client=llm_client)

    risk_map = {
        "passive": Risk.PASSIVE,
        "safe": Risk.SAFE,
        "intrusive": Risk.INTRUSIVE,
        "destructive": Risk.DESTRUCTIVE,
    }
    risk_ceiling = risk_map.get(risk.lower(), Risk.SAFE)

    runner = SubprocessRunner(
        event_log=event_log,
        event_bus=event_bus,
        scope=scope,
        risk_ceiling=risk_ceiling,
    )

    if resume and chk_path.exists():
        checkpoint = Checkpoint.load(chk_path)
        if checkpoint:
            fsm.state = checkpoint.to_phase_state()
            budget_gov.total_spent_usd = checkpoint.budget_spent_usd
            console.print(
                f"[bold green]Resuming engagement {slug} from phase:[/bold green] "
                f"{fsm.state.current_phase.value}"
            )
    else:
        # Initial engagement start event
        e_start = Event(
            engagement_id=slug,
            phase=Phase.SCOPE,
            actor="system",
            kind=EventKind.ENGAGEMENT_START,
            payload={"target": target, "profile": profile, "risk": risk, "budget": budget},
        )
        event_log.append(e_start)
        await event_bus.publish(e_start)

    # Automatically advance past SCOPE to start active exploration
    if fsm.state.current_phase == Phase.SCOPE:
        fsm.advance_phase()

    try:
        while not fsm.is_finished():
            current_phase = fsm.state.current_phase
            p_name = current_phase.value.upper()
            console.print(f"[bold cyan]>>> Entering Phase: {p_name}[/bold cyan]")
            e_phase = Event(
                engagement_id=slug,
                phase=current_phase,
                actor="planner",
                kind=EventKind.PHASE_ENTER,
                payload={"phase": current_phase.value},
            )
            event_log.append(e_phase)
            await event_bus.publish(e_phase)

            # Route decision via LLM Planner (or static policy fallback / --no-llm)
            if no_llm:
                decision = router.make_decision(
                    phase=current_phase,
                    target=target,
                    already_run_tools=fsm.state.tools_run_in_phase,
                    risk_ceiling=risk_ceiling,
                )
            else:
                decision = await planner.plan(
                    phase=current_phase,
                    target=target,
                    graph=graph,
                    available_tools=registry.list_tools(),
                    already_run_tools=fsm.state.tools_run_in_phase,
                    risk_ceiling=risk_ceiling,
                )

            # Record thought / plan events
            e_plan = Event(
                engagement_id=slug,
                phase=current_phase,
                actor="planner",
                kind=EventKind.PLAN,
                payload=decision.model_dump(),
            )
            event_log.append(e_plan)
            await event_bus.publish(e_plan)

            if decision.action == Action.ADVANCE_PHASE or not decision.tool:
                console.print(f"Advance decision: {decision.rationale}")
                fsm.advance_phase()
                chk = Checkpoint.from_phase_state(slug, target, fsm.state)
                chk.budget_spent_usd = budget_gov.total_spent_usd
                chk.save(chk_path)
                continue

            tool_spec = registry.get(decision.tool)
            if not tool_spec:
                fsm.advance_phase()
                continue

            console.print(f"Executing [bold magenta]{tool_spec.name}[/bold magenta]...")
            res = await runner.execute(
                tool_spec,
                decision.args,
                engagement_id=slug,
                phase=current_phase,
                target=target,
            )

            new_facts_count = 0
            facts: list[Fact] = []
            if res.stdout_path.exists() and res.stdout_path.stat().st_size > 0:
                try:
                    parser_func = get_parser(tool_spec.output.parser)
                    ctx = ParserContext(
                        tool=tool_spec.name,
                        event_id=res.event_id,
                        target=target,
                    )
                    facts = parser_func(res.stdout_path.read_bytes(), ctx)
                    graph.add_facts(facts)
                    new_facts_count = len(facts)

                    for f in facts:
                        f_evt = Event(
                            engagement_id=slug,
                            phase=current_phase,
                            actor="parser",
                            kind=EventKind.FACT,
                            tool=tool_spec.name,
                            parent_id=res.event_id,
                            payload=f.model_dump(),
                        )
                        event_log.append(f_evt)
                        await event_bus.publish(f_evt)

                    console.print(f"Extracted {new_facts_count} facts from {tool_spec.name}.")
                except Exception as pe:
                    console.print(f"[yellow]Parser note for {tool_spec.name}: {pe}[/yellow]")

            # Run interpreter on tool results if LLM enabled
            if not no_llm and facts:
                interp = await interpreter.interpret(res, facts)
                e_thought = Event(
                    engagement_id=slug,
                    phase=current_phase,
                    actor="planner",
                    kind=EventKind.THOUGHT,
                    parent_id=res.event_id,
                    payload=interp.model_dump(),
                )
                event_log.append(e_thought)
                await event_bus.publish(e_thought)

            # Update FSM and check loop guards
            loop_guard_fired = fsm.record_tool_result(tool_spec.name, new_facts_count)
            if loop_guard_fired:
                next_p = fsm.state.current_phase.value
                console.print(
                    f"[yellow]Loop guard triggered phase transition to {next_p}[/yellow]"
                )

            # Persist checkpoint after every step
            chk = Checkpoint.from_phase_state(slug, target, fsm.state)
            chk.findings_count = len(graph.by_kind(FactKind.INTERESTING))
            chk.budget_spent_usd = budget_gov.total_spent_usd
            chk.save(chk_path)

        # Engagement complete (reached REPORT phase)
        console.print(f"[bold cyan]>>> Entering Phase: {Phase.REPORT.value.upper()}[/bold cyan]")
        chk = Checkpoint.from_phase_state(slug, target, fsm.state, status="completed")
        chk.budget_spent_usd = budget_gov.total_spent_usd
        chk.save(chk_path)

        # Generate stub report output
        report_file = eng_dir / "report_stub.txt"
        report_content = (
            f"Venice-PT Assessment Report for {target}\n"
            f"Engagement: {slug}\n"
            f"Total Facts: {graph.count()}\n"
            f"Total Tool Calls: {fsm.state.total_tool_calls}\n"
            f"Findings: {len(graph.by_kind(FactKind.INTERESTING))}\n"
            f"Budget Spent: ${budget_gov.total_spent_usd:.4f}\n"
        )
        report_file.write_text(report_content, encoding="utf-8")

        e_end = Event(
            engagement_id=slug,
            phase=Phase.REPORT,
            actor="system",
            kind=EventKind.ENGAGEMENT_END,
            cost_usd=budget_gov.total_spent_usd,
            payload={"facts": graph.count(), "report": str(report_file)},
        )
        event_log.append(e_end)
        await event_bus.publish(e_end)

        console.print(
            f"[bold green]Engagement {slug} finished successfully. "
            f"Total spend: ${budget_gov.total_spent_usd:.4f}[/bold green]"
        )

    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print(
            "\n[bold yellow]Graceful interrupt received. Checkpointing state...[/bold yellow]"
        )
        chk = Checkpoint.from_phase_state(slug, target, fsm.state, status="paused")
        chk.budget_spent_usd = budget_gov.total_spent_usd
        chk.save(chk_path)
        console.print(
            f"[bold yellow]Engagement paused. Resume with: "
            f"venice-pt run --resume --target {target}[/bold yellow]"
        )
