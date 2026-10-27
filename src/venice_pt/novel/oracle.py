from __future__ import annotations

import time

import httpx

from venice_pt.contracts.findings import Finding, FindingOrigin, Severity
from venice_pt.novel.diff import capture_baseline, compute_diff
from venice_pt.novel.payloads import PayloadGenerator


class NovelOracle:
    """Coordinates differential fuzzing probes against target parameters."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client

    async def probe_parameter(
        self,
        target_url: str,
        param_name: str,
        base_value: str = "1",
    ) -> list[Finding]:
        """Runs differential probes against a parameter and surfaces anomalous findings."""
        findings: list[Finding] = []

        async with (self.client or httpx.AsyncClient(timeout=10.0)) as cli:
            # Step 1: Capture baseline
            t0 = time.perf_counter()
            try:
                base_resp = await cli.get(target_url, params={param_name: base_value})
                base_time = time.perf_counter() - t0
            except Exception:
                return []

            baseline = capture_baseline(
                status_code=base_resp.status_code,
                body=base_resp.text,
                elapsed_seconds=base_time,
                headers=dict(base_resp.headers),
            )

            # Step 2: Test SQLi time-based probes
            for probe_type, payload in PayloadGenerator.generate_sqli_payloads():
                t1 = time.perf_counter()
                try:
                    resp = await cli.get(target_url, params={param_name: payload})
                    elapsed = time.perf_counter() - t1
                except Exception:
                    continue

                diff = compute_diff(baseline, resp.status_code, resp.text, elapsed)
                if diff.anomaly_score >= 0.5:
                    finding = Finding(
                        engagement_id="default",
                        title=f"Potential SQL Injection on {param_name}",
                        cls="sqli_differential",
                        asset_key=target_url,
                        endpoint=target_url,
                        param=param_name,
                        severity=Severity.HIGH,
                        origin=FindingOrigin.NOVEL_ORACLE,
                        confidence=diff.anomaly_score,
                        verified=False,
                        evidence=[
                            f"param={param_name}",
                            f"probe_type={probe_type}",
                            f"baseline_time={round(baseline.elapsed_seconds, 2)}",
                            f"probe_time={round(elapsed, 2)}",
                        ] + diff.reasons,
                    )
                    findings.append(finding)
                    break

        return findings
