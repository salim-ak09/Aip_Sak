from __future__ import annotations

import html

import httpx

from venice_pt.contracts.findings import Finding, Verdict


class XSSVerifier:
    async def verify(self, finding: Finding, client: httpx.AsyncClient | None = None) -> Verdict:
        """Independent re-production using unescaped reflection context oracle."""
        if not finding.endpoint:
            return Verdict(
                finding_id=finding.id,
                confirmed=False,
                method="xss_reflection_check",
                confidence_delta=-0.4,
                notes="Missing target endpoint",
            )

        target_url = finding.endpoint
        param = finding.param or "q"
        # Unique canary probe
        canary = "vptxss<script>/*canary*/</script>"

        async with httpx.AsyncClient(timeout=10.0) as http_client:
            cli = client or http_client
            try:
                resp = await cli.get(target_url, params={param: canary})
                body = resp.text

                # Confirm exact unescaped reflection (not html-encoded)
                if canary in body and html.escape(canary) not in body:
                    return Verdict(
                        finding_id=finding.id,
                        confirmed=True,
                        method="raw_reflection_oracle",
                        confidence_delta=0.2,
                        evidence=[f"Unescaped canary observed in response ({len(body)} bytes)"],
                        notes="Direct unescaped script reflection confirmed",
                    )
            except Exception as e:
                return Verdict(
                    finding_id=finding.id,
                    confirmed=False,
                    method="xss_reflection_check",
                    confidence_delta=-0.4,
                    notes=f"Verification request error: {e}",
                )

        return Verdict(
            finding_id=finding.id,
            confirmed=False,
            method="xss_reflection_check",
            confidence_delta=-0.4,
            notes="Payload was properly escaped or not reflected in response",
        )
