from __future__ import annotations

import pytest

from venice_pt.watch.alerts import AlertDispatcher
from venice_pt.watch.cve_match import CVEMatcher
from venice_pt.watch.drift import SurfaceDriftDetector
from venice_pt.watch.scheduler import WatchScheduler


def test_surface_drift_detection() -> None:
    prev_snapshot = {
        "assets": ["app.local"],
        "ports": [{"host": "app.local", "port": 80}],
    }
    # New asset and new port added
    curr_snapshot = {
        "assets": ["app.local", "admin.local"],
        "ports": [
            {"host": "app.local", "port": 80},
            {"host": "app.local", "port": 8080},
        ],
    }

    drift = SurfaceDriftDetector.detect_drift(prev_snapshot, curr_snapshot)
    assert drift.has_drift is True
    assert drift.new_assets == ["admin.local"]
    assert len(drift.new_ports) == 1
    assert drift.new_ports[0]["port"] == 8080


def test_cve_version_matcher() -> None:
    # Apache 2.4.49 has known RCE (CVE-2021-41773)
    matches = CVEMatcher.match("Apache HTTP Server", "2.4.49")
    assert len(matches) >= 1
    assert any(m.cve_id == "CVE-2021-41773" for m in matches)
    assert matches[0].severity == "critical"

    # Patched Apache version has no matches in this list
    clean_matches = CVEMatcher.match("Apache HTTP Server", "2.4.58")
    assert len(clean_matches) == 0


@pytest.mark.asyncio
async def test_alert_deduplication() -> None:
    dispatcher = AlertDispatcher(suppression_seconds=10.0)

    # First dispatch succeeds
    res1 = await dispatcher.dispatch("Alert 1", "Message 1", "key-1")
    assert res1 is True

    # Immediate second dispatch with same key is suppressed
    res2 = await dispatcher.dispatch("Alert 1", "Message 1", "key-1")
    assert res2 is False

    # Dispatch with different key succeeds
    res3 = await dispatcher.dispatch("Alert 2", "Message 2", "key-2")
    assert res3 is True


@pytest.mark.asyncio
async def test_watch_scheduler_cycle() -> None:
    scheduler = WatchScheduler(interval_seconds=60.0)
    snapshot = {
        "assets": ["127.0.0.1"],
        "ports": [
            {"host": "127.0.0.1", "port": 80, "product": "apache", "version": "2.4.49"}
        ],
    }
    # First cycle establishes baseline
    drift = await scheduler.execute_cycle(snapshot)
    assert drift.has_drift is True
    assert drift.new_assets == ["127.0.0.1"]
