from __future__ import annotations

from dataclasses import dataclass, field

from venice_pt.contracts.events import Phase

PHASE_SEQUENCE = [
    Phase.SCOPE,
    Phase.RECON,
    Phase.ENUM,
    Phase.VULN_SCAN,
    Phase.NOVEL_FUZZ,
    Phase.VALIDATE,
    Phase.CHAIN,
    Phase.REPORT,
]


@dataclass
class PhaseState:
    current_phase: Phase = Phase.SCOPE
    iterations_in_phase: int = 0
    total_tool_calls: int = 0
    consecutive_zero_fact_runs: int = 0
    completed_phases: list[Phase] = field(default_factory=list)
    tools_run_in_phase: set[str] = field(default_factory=set)
    total_facts_observed: int = 0


class PentestFSM:
    """Hand-rolled deterministic finite state machine with strict loop guards."""

    def __init__(
        self,
        max_iterations_per_phase: int = 10,
        max_total_tool_calls: int = 50,
        no_progress_threshold: int = 3,
    ) -> None:
        self.max_iterations_per_phase = max_iterations_per_phase
        self.max_total_tool_calls = max_total_tool_calls
        self.no_progress_threshold = no_progress_threshold
        self.state = PhaseState()

    def can_advance(self) -> bool:
        idx = PHASE_SEQUENCE.index(self.state.current_phase)
        return idx < len(PHASE_SEQUENCE) - 1

    def advance_phase(self) -> Phase:
        if not self.can_advance():
            return self.state.current_phase

        idx = PHASE_SEQUENCE.index(self.state.current_phase)
        if self.state.current_phase not in self.state.completed_phases:
            self.state.completed_phases.append(self.state.current_phase)

        next_phase = PHASE_SEQUENCE[idx + 1]
        self.state.current_phase = next_phase
        self.state.iterations_in_phase = 0
        self.state.consecutive_zero_fact_runs = 0
        self.state.tools_run_in_phase.clear()
        return next_phase

    def record_tool_result(self, tool_name: str, new_facts_count: int) -> bool:
        """Records tool execution and returns True if loop guard triggered a phase advance."""
        self.state.total_tool_calls += 1
        self.state.iterations_in_phase += 1
        self.state.tools_run_in_phase.add(tool_name)
        self.state.total_facts_observed += new_facts_count

        if new_facts_count == 0:
            self.state.consecutive_zero_fact_runs += 1
        else:
            self.state.consecutive_zero_fact_runs = 0

        # Loop guard 1: no-progress detector (3 consecutive runs yielding 0 new facts)
        if self.state.consecutive_zero_fact_runs >= self.no_progress_threshold:
            if self.can_advance():
                self.advance_phase()
                return True

        # Loop guard 2: max iterations per phase exceeded
        if self.state.iterations_in_phase >= self.max_iterations_per_phase:
            if self.can_advance():
                self.advance_phase()
                return True

        # Loop guard 3: global safety cap on total tool calls
        if self.state.total_tool_calls >= self.max_total_tool_calls:
            self.state.current_phase = Phase.REPORT
            return True

        return False

    def is_finished(self) -> bool:
        return self.state.current_phase == Phase.REPORT
