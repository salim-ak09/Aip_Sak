from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from venice_pt.contracts.events import Event, EventKind, Phase
from venice_pt.store.bus import EventBus
from venice_pt.store.eventlog import EventLog
from venice_pt.store.projections import (
    cost_meter,
    engagement_summary,
    findings_table,
    phase_progress,
)


def test_append_10k_events_performance(tmp_path: Path) -> None:
    """SPEC requirement: append 10k events in < 1 second."""
    db_file = tmp_path / "perf_test.db"
    log = EventLog(db_file)

    events = [
        Event(
            engagement_id="perf-eng",
            phase=Phase.RECON,
            actor="runner",
            kind=EventKind.CMD,
            tool="nmap",
            tokens_in=10,
            tokens_out=20,
            cost_usd=0.0001,
        )
        for _ in range(10_000)
    ]

    t0 = time.perf_counter()
    log.append_many(events)
    elapsed = time.perf_counter() - t0

    assert elapsed < 1.0, f"Appending 10k events took {elapsed:.3f}s, expected < 1.0s"
    saved = log.get_events("perf-eng")
    assert len(saved) == 10_000


def test_provenance_chain_walk(tmp_path: Path) -> None:
    """SPEC requirement: chain walk correctness."""
    db_file = tmp_path / "chain_test.db"
    log = EventLog(db_file)

    # Build a 5-event provenance tree
    e0 = log.append(
        Event(
            engagement_id="c-eng",
            phase=Phase.SCOPE,
            actor="system",
            kind=EventKind.ENGAGEMENT_START,
        )
    )
    e1 = log.append(
        Event(
            engagement_id="c-eng",
            phase=Phase.RECON,
            actor="planner",
            kind=EventKind.PLAN,
            parent_id=e0.id,
        )
    )
    e2 = log.append(
        Event(
            engagement_id="c-eng",
            phase=Phase.RECON,
            actor="runner",
            kind=EventKind.CMD,
            parent_id=e1.id,
        )
    )
    e3 = log.append(
        Event(
            engagement_id="c-eng",
            phase=Phase.RECON,
            actor="parser",
            kind=EventKind.FACT,
            parent_id=e2.id,
        )
    )
    e4 = log.append(
        Event(
            engagement_id="c-eng",
            phase=Phase.VULN_SCAN,
            actor="verifier",
            kind=EventKind.FINDING,
            parent_id=e3.id,
        )
    )

    chain = log.walk_chain(e4.id)
    assert len(chain) == 5
    assert [e.id for e in chain] == [e0.id, e1.id, e2.id, e3.id, e4.id]


def test_projection_determinism() -> None:
    """SPEC requirement: projection determinism (same log -> same output)."""
    events = [
        Event(
            engagement_id="proj-eng",
            phase=Phase.SCOPE,
            actor="system",
            kind=EventKind.ENGAGEMENT_START,
        ),
        Event(
            engagement_id="proj-eng",
            phase=Phase.RECON,
            actor="runner",
            kind=EventKind.CMD,
            tool="nmap",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.005,
            duration_ms=1000,
        ),
        Event(
            engagement_id="proj-eng",
            phase=Phase.VULN_SCAN,
            actor="runner",
            kind=EventKind.FINDING,
            payload={
                "id": "f-1",
                "title": "Exposure",
                "severity": "medium",
                "confidence": 0.7,
            },
        ),
        Event(
            engagement_id="proj-eng",
            phase=Phase.VALIDATE,
            actor="verifier",
            kind=EventKind.VERDICT,
            payload={"finding_id": "f-1", "confirmed": True, "confidence_delta": 0.2},
        ),
    ]

    s1, s2 = engagement_summary(events), engagement_summary(events)
    p1, p2 = phase_progress(events), phase_progress(events)
    f1, f2 = findings_table(events), findings_table(events)
    c1, c2 = cost_meter(events), cost_meter(events)

    assert s1 == s2
    assert p1 == p2
    assert f1 == f2
    assert c1 == c2

    assert f1[0]["verified"] is True
    assert f1[0]["confidence"] == pytest.approx(0.9)
    assert c1["total_tokens"] == 150
    assert c1["total_cost_usd"] == 0.005


@pytest.mark.asyncio
async def test_bus_fanout_three_subscribers() -> None:
    """SPEC requirement: bus fan-out to 3 subscribers receiving all events in order."""
    bus = EventBus()
    received_lists: list[list[Event]] = [[], [], []]

    async def subscriber(index: int) -> None:
        async for event in bus.subscribe("fanout-eng"):
            received_lists[index].append(event)
            if len(received_lists[index]) == 10:
                break

    tasks = [asyncio.create_task(subscriber(i)) for i in range(3)]
    await asyncio.sleep(0.01)

    for i in range(10):
        await bus.publish(
            Event(
                engagement_id="fanout-eng",
                phase=Phase.RECON,
                actor="runner",
                kind=EventKind.CMD,
                payload={"index": i},
            )
        )

    await asyncio.gather(*tasks)

    for i in range(3):
        assert len(received_lists[i]) == 10
        assert [e.payload["index"] for e in received_lists[i]] == list(range(10))
