from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from venice_pt.contracts.events import Risk


class Action(StrEnum):
    RUN_TOOL = "run_tool"
    RUN_COMMAND = "run_command"
    QUERY_GRAPH = "query_graph"
    ASK_HUMAN = "ask_human"
    ADVANCE_PHASE = "advance_phase"
    FINISH = "finish"


class Decision(BaseModel):
    action: Action
    tool: str | None = None
    args: list[str] = Field(default_factory=list)
    target: str | None = None
    rationale: str
    hypothesis_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    risk: Risk
    expects: list[str] = Field(default_factory=list)
    budget_hint_usd: float = 0.05
