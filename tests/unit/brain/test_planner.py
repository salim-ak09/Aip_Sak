from __future__ import annotations

from pathlib import Path

import pytest

from venice_pt.brain.budget import BudgetExceeded, BudgetGovernor
from venice_pt.brain.interpreter import Interpreter
from venice_pt.brain.planner import PlannerEngine
from venice_pt.brain.router import StaticPolicyRouter
from venice_pt.contracts.decisions import Action, Decision
from venice_pt.contracts.events import Phase, Risk
from venice_pt.contracts.llm import LLMClient, LLMResult, LLMRole, Msg
from venice_pt.exec.runner import ToolResult
from venice_pt.knowledge.graph import KnowledgeGraph


class MockLLMClient(LLMClient):
    def __init__(self, response_text: str = "", parsed_obj: Decision | None = None) -> None:
        self.response_text = response_text
        self.parsed_obj = parsed_obj
        self.call_count = 0

    async def complete(
        self,
        role: LLMRole,
        messages: list[Msg],
        schema: type[Decision] | None = None,
        max_tokens: int = 2048,
    ) -> LLMResult:
        self.call_count += 1
        return LLMResult(
            text=self.response_text,
            parsed=self.parsed_obj,
            model="mock-llm",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.001,
            latency_ms=10,
        )


def test_budget_governor_threshold_and_cap() -> None:
    """SPEC requirement: model downgrade triggers at threshold; budget cap halts."""
    gov = BudgetGovernor(max_budget_usd=1.0)
    assert gov.should_downgrade() is False
    assert gov.is_exceeded() is False

    # 1. Spend 0.81 (exceeds 80% threshold)
    gov.record_spend(LLMRole.PLANNER, 0.81)
    assert gov.should_downgrade() is True
    assert gov.is_exceeded() is False

    # 2. Spend beyond 1.0 (triggers BudgetExceeded)
    with pytest.raises(BudgetExceeded):
        gov.record_spend(LLMRole.PLANNER, 0.20)
    assert gov.is_exceeded() is True


@pytest.mark.asyncio
async def test_planner_output_validates_against_schema() -> None:
    """SPEC requirement: planner output validates against schema with mocked LLM."""
    expected_decision = Decision(
        action=Action.RUN_TOOL,
        tool="httpx",
        args=["-u", "http://127.0.0.1:3000"],
        rationale="Probe HTTP services",
        confidence=0.9,
        risk=Risk.SAFE,
        expects=["service"],
    )
    mock_client = MockLLMClient(
        response_text=expected_decision.model_dump_json(),
        parsed_obj=expected_decision,
    )
    planner = PlannerEngine(llm_client=mock_client)

    graph = KnowledgeGraph()
    decision = await planner.plan(
        phase=Phase.RECON,
        target="http://127.0.0.1:3000",
        graph=graph,
        available_tools=[],
        already_run_tools=set(),
    )
    assert decision.action == Action.RUN_TOOL
    assert decision.tool == "httpx"
    assert decision.confidence == 0.9


@pytest.mark.asyncio
async def test_malformed_json_fallback_to_static_router() -> None:
    """SPEC requirement: malformed JSON -> repair retry then fallback to static router."""
    mock_client = MockLLMClient(response_text="INVALID NOT JSON", parsed_obj=None)
    router = StaticPolicyRouter()
    planner = PlannerEngine(llm_client=mock_client, router=router)

    graph = KnowledgeGraph()
    decision = await planner.plan(
        phase=Phase.RECON,
        target="http://127.0.0.1:3000",
        graph=graph,
        available_tools=router.registry.list_tools(),
        already_run_tools=set(),
    )
    # Failed both initial and repair prompt -> fell back to router decision
    assert decision.action == Action.RUN_TOOL
    assert decision.tool in ("nmap", "httpx", "subfinder")
    assert "Static policy" in decision.rationale


@pytest.mark.asyncio
async def test_interpreter_summarizes_output() -> None:
    interpreter = Interpreter()
    dummy_res = ToolResult(
        event_id="e-dummy",
        tool="nmap",
        argv=["-sV"],
        exit_code=0,
        duration_s=1.0,
        stdout_path=Path("dummy.out"),
        stderr_path=Path("dummy.err"),
        parsed=None,
        facts=[],
    )
    interp = await interpreter.interpret(dummy_res, [])
    assert "nmap" in interp.summary
