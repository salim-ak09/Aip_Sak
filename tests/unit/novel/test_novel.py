from __future__ import annotations

import pytest

from venice_pt.contracts.findings import Finding, FindingOrigin, Severity
from venice_pt.novel.callbacks import global_callback_listener
from venice_pt.novel.chains import ChainPlanner
from venice_pt.novel.diff import capture_baseline, compute_diff
from venice_pt.novel.payloads import PayloadGenerator


def test_differential_detection() -> None:
    # Capture standard baseline
    baseline = capture_baseline(
        status_code=200,
        body="<html><body>Normal response</body></html>",
        elapsed_seconds=0.15,
    )

    # Identical response -> anomaly score 0.0
    same_diff = compute_diff(
        baseline,
        status_code=200,
        body="<html><body>Normal response</body></html>",
        elapsed_seconds=0.16,
    )
    assert same_diff.anomaly_score == 0.0
    assert not same_diff.status_changed

    # Time-delayed response (e.g. SQLi sleep payload) -> anomalous delta >= 0.5
    anomaly_diff = compute_diff(
        baseline,
        status_code=200,
        body="<html><body>Normal response</body></html>",
        elapsed_seconds=3.2,
    )
    assert anomaly_diff.anomaly_score >= 0.5
    assert any("Timing differential" in r for r in anomaly_diff.reasons)


@pytest.mark.asyncio
async def test_callback_correlation() -> None:
    nonce, url = PayloadGenerator.generate_callback_url("oob.venice.internal", probe_tag="ssrf")
    assert "ssrf_" in nonce
    assert nonce in url

    # Initially no callback
    assert not await global_callback_listener.check_nonce(nonce)

    # Simulate OOB interaction trigger
    await global_callback_listener.register_interaction(
        nonce=nonce,
        source_ip="10.0.0.42",
        protocol="HTTP",
        raw_data="GET / HTTP/1.1",
    )

    events = await global_callback_listener.check_nonce(nonce)
    assert len(events) == 1
    assert events[0].source_ip == "10.0.0.42"
    assert events[0].protocol == "HTTP"


def test_attack_chain_synthesis() -> None:
    findings = [
        Finding(
            engagement_id="test",
            cls="info_leak",
            title="Swagger API Docs Exposed",
            asset_key="http://127.0.0.1:3000/api-docs",
            endpoint="http://127.0.0.1:3000/api-docs",
            severity=Severity.LOW,
            origin=FindingOrigin.KNOWN_TOOL,
            confidence=0.9,
            verified=True,
        ),
        Finding(
            engagement_id="test",
            cls="idor",
            title="IDOR in User Profile",
            asset_key="http://127.0.0.1:3000/api/users/profile",
            endpoint="http://127.0.0.1:3000/api/users/profile",
            severity=Severity.MEDIUM,
            origin=FindingOrigin.NOVEL_ORACLE,
            confidence=0.95,
            verified=True,
        ),
    ]

    chains = ChainPlanner.synthesize_chains(findings)
    assert len(chains) == 1
    chain = chains[0]
    assert chain.chain_id == "CHAIN-ATO-01"
    assert chain.composite_severity == "Critical"
    assert len(chain.steps) == 2
