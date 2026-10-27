from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from venice_pt.contracts.events import EventKind, Phase, Risk
from venice_pt.contracts.tools import InstallStep, OutputSpec, ToolSpec
from venice_pt.exec.flags import FlagSchemaManager
from venice_pt.exec.runner import SubprocessRunner
from venice_pt.exec.scope import ScopeDefinition
from venice_pt.store.bus import EventBus
from venice_pt.store.eventlog import EventLog


def dummy_spec(name: str = "echo_tool", binary: str = "python", timeout_s: int = 5) -> ToolSpec:
    return ToolSpec(
        name=name,
        binary=binary,
        capabilities=["test"],
        phases=[Phase.RECON],
        risk=Risk.SAFE,
        timeout_s=timeout_s,
        install=[InstallStep(method="apt", pkg=name)],
        check="--version",
        output=OutputSpec(format="text", parser="dummy", normalizes_to=[]),
    )


@pytest.mark.asyncio
async def test_runner_timeout_kills_process(tmp_path: Path) -> None:
    """SPEC requirement: timeout kills the process."""
    spec = dummy_spec(timeout_s=1)
    runner = SubprocessRunner()

    # Run a python command that sleeps for 10 seconds (exceeding 1s timeout)
    res = await runner.execute(
        spec,
        ["-c", "import time; time.sleep(10)"],
        engagement_id="timeout_test",
        phase=Phase.RECON,
    )
    assert res.exit_code == 124
    assert res.error is not None
    assert "timed out" in res.error
    assert res.stderr_path.exists()
    assert "timed out" in res.stderr_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_scope_violation_blocked(tmp_path: Path) -> None:
    """SPEC requirement: scope violation blocked without crashing."""
    scope = ScopeDefinition(
        included_domains=["example.com"],
        excluded_domains=["secret.example.com"],
    )
    runner = SubprocessRunner(scope=scope)
    spec = dummy_spec()

    # Out-of-scope domain target
    res = await runner.execute(
        spec,
        ["-c", "print('hello')"],
        engagement_id="scope_test",
        phase=Phase.RECON,
        target="malicious.org",
    )
    assert res.exit_code == 1
    assert res.error is not None
    assert "out of engagement scope" in res.error

    # Excluded domain target
    res2 = await runner.execute(
        spec,
        ["-c", "print('hello')"],
        engagement_id="scope_test",
        phase=Phase.RECON,
        target="secret.example.com",
    )
    assert res2.exit_code == 1
    assert "out of engagement scope" in str(res2.error)


def test_flag_schema_caching_and_unknown_flag_dropped(tmp_path: Path) -> None:
    """SPEC requirement: flag schema cached after one call; unknown flag dropped."""
    mgr = FlagSchemaManager(flags_dir=tmp_path / "flags")
    spec = dummy_spec()

    # Pre-cache known flags
    mgr.cache_flag_schema(spec.name, {"-c", "-v", "--help"})

    # Ensure flags loaded from cache
    cached = mgr.ensure_flags(spec)
    assert cached == {"-c", "-v", "--help"}

    # Validate args with an unknown flag
    args = ["-c", "print(1)", "--unknown-flag", "value", "-v"]
    cleaned = mgr.validate_args(spec, args)
    assert "--unknown-flag" not in cleaned
    assert "-c" in cleaned
    assert "-v" in cleaned


@pytest.mark.asyncio
async def test_streamed_events_arrive_in_order(tmp_path: Path) -> None:
    """SPEC requirement: streamed events arrive in order."""
    db_file = tmp_path / "stream_events.db"
    log = EventLog(db_file)
    bus = EventBus()

    runner = SubprocessRunner(event_log=log, event_bus=bus)
    spec = dummy_spec()

    received_events = []

    async def listener() -> None:
        async for event in bus.subscribe("stream_eng"):
            received_events.append(event)
            if event.kind == EventKind.STDOUT:
                break

    task = asyncio.create_task(listener())
    await asyncio.sleep(0.01)

    res = await runner.execute(
        spec,
        ["-c", "print('hello_venice')"],
        engagement_id="stream_eng",
        phase=Phase.RECON,
    )

    await asyncio.wait_for(task, timeout=5)

    assert res.exit_code == 0
    assert len(received_events) >= 2
    assert received_events[0].kind == EventKind.CMD
    assert received_events[1].kind == EventKind.STDOUT
