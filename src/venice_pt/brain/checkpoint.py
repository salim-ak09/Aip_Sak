from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from venice_pt.brain.fsm import PhaseState
from venice_pt.contracts.events import Phase


class Checkpoint(BaseModel):
    engagement_id: str
    target: str
    current_phase: Phase
    completed_phases: list[Phase] = Field(default_factory=list)
    last_event_id: str | None = None
    facts_count: int = 0
    findings_count: int = 0
    budget_spent_usd: float = 0.0
    status: str = "running"  # running, paused, completed, aborted
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> Checkpoint | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls.model_validate(data)
        except Exception:
            return None

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    def to_phase_state(self) -> PhaseState:
        return PhaseState(
            current_phase=self.current_phase,
            completed_phases=self.completed_phases.copy(),
            total_facts_observed=self.facts_count,
        )

    @classmethod
    def from_phase_state(
        cls,
        engagement_id: str,
        target: str,
        state: PhaseState,
        status: str = "running",
    ) -> Checkpoint:
        return cls(
            engagement_id=engagement_id,
            target=target,
            current_phase=state.current_phase,
            completed_phases=state.completed_phases.copy(),
            facts_count=state.total_facts_observed,
            status=status,
        )
