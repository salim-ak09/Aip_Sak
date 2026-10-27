from __future__ import annotations

import httpx

from venice_pt.contracts.findings import Finding, Verdict


class ReachabilityVerifier:
    """Verifies CVE match or misconfig findings via reachability and response validation."""

    async def verify(self, finding: Finding, client: httpx.AsyncClient | None = None) -> Verdict:
        if not finding.endpoint:
            return Verdict(
                finding_id=finding.id,
                confirmed=False,
                method="reachability_probe",
                confidence_delta=-0.4,
                notes="Endpoint unspecified for reachability verification",
            )

        target_url = finding.endpoint

        async with httpx.AsyncClient(timeout=10.0) as http_client:
            cli = client or http_client
            try:
                resp = await cli.get(target_url)
                # If endpoint responds with 200/something vulnerable rather than 404/403/500
                if resp.status_code == 200:
                    return Verdict(
                        finding_id=finding.id,
                        confirmed=True,
                        method="endpoint_reachability_oracle",
                        confidence_delta=0.1,
                        evidence=[
                            f"Endpoint {target_url} returned HTTP 200 ({len(resp.text)} bytes)"
                        ],
                        notes="Endpoint reachability confirmed with successful status code",
                    )
            except Exception as e:
                return Verdict(
                    finding_id=finding.id,
                    confirmed=False,
                    method="reachability_probe",
                    confidence_delta=-0.4,
                    notes=f"Failed to reach endpoint: {e}",
                )

        return Verdict(
            finding_id=finding.id,
            confirmed=False,
            method="reachability_probe",
            confidence_delta=-0.4,
            notes="Endpoint unreachable or returned non-vulnerable status code",
        )
