from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from venice_pt.brain.budget import BudgetGovernor
from venice_pt.brain.llm_client import OpenAICompatibleLLMClient
from venice_pt.brain.router import StaticPolicyRouter
from venice_pt.contracts.decisions import Action, Decision
from venice_pt.contracts.events import Phase, Risk
from venice_pt.contracts.llm import LLMClient, LLMRole, Msg
from venice_pt.contracts.tools import ToolSpec
from venice_pt.knowledge.graph import KnowledgeGraph
from venice_pt.knowledge.render import render_graph_for_llm, unexplored_surface
from venice_pt.logging import logger

PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "planner.jinja"


class PlannerEngine:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        router: StaticPolicyRouter | None = None,
        budget: BudgetGovernor | None = None,
    ) -> None:
        self.budget = budget or BudgetGovernor()
        self.llm_client = llm_client or OpenAICompatibleLLMClient(budget_governor=self.budget)
        self.router = router or StaticPolicyRouter()
        self.template = Template(PROMPT_FILE.read_text(encoding="utf-8"))

    async def plan(
        self,
        phase: Phase,
        target: str,
        graph: KnowledgeGraph,
        available_tools: list[ToolSpec],
        already_run_tools: set[str],
        risk_ceiling: Risk = Risk.SAFE,
        operator_instructions: list[str] | None = None,
    ) -> Decision:
        # Check budget governor first
        if self.budget.is_exceeded():
            logger.warning("Budget cap exceeded. Advancing directly to REPORT.")
            return Decision(
                action=Action.ADVANCE_PHASE,
                rationale="Budget exceeded; forcing phase advance to report.",
                confidence=1.0,
                risk=Risk.SAFE,
            )

        # 1. Render compact graph (strictly <= 4KB)
        graph_text = render_graph_for_llm(graph, max_bytes=4096)
        unexplored = unexplored_surface(graph)

        prompt_text = self.template.render(
            target=target,
            phase=phase.value,
            risk_ceiling=risk_ceiling.value,
            remaining_budget=self.budget.remaining_budget(),
            tools=[t for t in available_tools if t.name not in already_run_tools],
            graph_render=graph_text,
            unexplored=unexplored,
            operator_instructions=operator_instructions or [],
        )

        messages = [
            Msg(role="system", content="You are an autonomous AI pentest planner."),
            Msg(role="user", content=prompt_text),
        ]

        try:
            res = await self.llm_client.complete(
                role=LLMRole.PLANNER,
                messages=messages,
                schema=Decision,
                max_tokens=2048,
            )

            if isinstance(res.parsed, Decision):
                return res.parsed

            # Malformed JSON: attempt single repair prompt
            repair_messages = messages + [
                Msg(role="assistant", content=res.text),
                Msg(
                    role="user",
                    content="Output did not validate against Decision schema. "
                    "Output ONLY the valid JSON Decision object.",
                ),
            ]
            repair_res = await self.llm_client.complete(
                role=LLMRole.PLANNER,
                messages=repair_messages,
                schema=Decision,
                max_tokens=2048,
            )
            if isinstance(repair_res.parsed, Decision):
                return repair_res.parsed

        except Exception as e:
            logger.warning("LLM planner error, falling back to static router", error=str(e))

        # Fallback to deterministic static policy router
        logger.info("Falling back to static policy router")
        return self.router.make_decision(
            phase=phase,
            target=target,
            already_run_tools=already_run_tools,
            risk_ceiling=risk_ceiling,
        )
