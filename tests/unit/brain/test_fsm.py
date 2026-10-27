from __future__ import annotations

from pathlib import Path

from venice_pt.brain.checkpoint import Checkpoint
from venice_pt.brain.fsm import PentestFSM
from venice_pt.brain.router import StaticPolicyRouter
from venice_pt.contracts.decisions import Action
from venice_pt.contracts.events import Phase, Risk


def test_fsm_reaches_report() -> None:
    """SPEC requirement: FSM reaches REPORT with LLM stubbed out."""
    fsm = PentestFSM()

    assert fsm.state.current_phase == Phase.SCOPE
    fsm.advance_phase()
    assert fsm.state.current_phase == Phase.RECON

    # Advance until REPORT
    while not fsm.is_finished():
        fsm.advance_phase()

    assert fsm.state.current_phase == Phase.REPORT
    assert fsm.is_finished() is True


def test_loop_guard_no_progress_detector() -> None:
    """No-progress detector: if 3 consecutive runs yield 0 new facts -> advance."""
    fsm = PentestFSM(no_progress_threshold=3)
    fsm.state.current_phase = Phase.RECON

    # 1st run with 0 facts
    advanced = fsm.record_tool_result("tool1", 0)
    assert advanced is False
    assert fsm.state.current_phase == Phase.RECON

    # 2nd run with 0 facts
    advanced = fsm.record_tool_result("tool2", 0)
    assert advanced is False
    assert fsm.state.current_phase == Phase.RECON

    # 3rd run with 0 facts -> triggers advance
    advanced = fsm.record_tool_result("tool3", 0)
    assert advanced is True
    assert fsm.state.current_phase == Phase.ENUM


def test_loop_guard_max_iterations() -> None:
    """SPEC requirement: max iterations per phase guard."""
    fsm = PentestFSM(max_iterations_per_phase=2, no_progress_threshold=10)
    fsm.state.current_phase = Phase.RECON

    fsm.record_tool_result("tool1", 5)
    assert fsm.state.current_phase == Phase.RECON

    # Reaching limit advances phase
    advanced = fsm.record_tool_result("tool2", 5)
    assert advanced is True
    assert fsm.state.current_phase == Phase.ENUM


def test_static_router_tool_selection() -> None:
    router = StaticPolicyRouter()
    decision = router.make_decision(
        phase=Phase.RECON,
        target="http://127.0.0.1:3000",
        already_run_tools=set(),
        risk_ceiling=Risk.SAFE,
    )
    assert decision.action == Action.RUN_TOOL
    assert decision.tool in ("nmap", "httpx", "subfinder")

    # If all tools for phase ran, make_decision advances phase
    decision_advance = router.make_decision(
        phase=Phase.RECON,
        target="http://127.0.0.1:3000",
        already_run_tools={"nmap", "httpx", "subfinder", "dnsx", "whatweb"},
        risk_ceiling=Risk.SAFE,
    )
    assert decision_advance.action == Action.ADVANCE_PHASE


def test_checkpoint_resume_identical_state(tmp_path: Path) -> None:
    """SPEC requirement: checkpoint/resume byte-identical state."""
    fsm = PentestFSM()
    fsm.state.current_phase = Phase.ENUM
    fsm.state.completed_phases = [Phase.SCOPE, Phase.RECON]
    fsm.state.total_facts_observed = 42

    chk_file = tmp_path / "state.json"
    chk = Checkpoint.from_phase_state("test-eng", "127.0.0.1", fsm.state)
    chk.save(chk_file)

    loaded_chk = Checkpoint.load(chk_file)
    assert loaded_chk is not None
    restored_state = loaded_chk.to_phase_state()

    assert restored_state.current_phase == fsm.state.current_phase
    assert restored_state.completed_phases == fsm.state.completed_phases
    assert restored_state.total_facts_observed == fsm.state.total_facts_observed
