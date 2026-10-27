from __future__ import annotations

import httpx

from venice_pt.contracts.findings import Finding, FindingOrigin, Severity


class IDORProbe:
    """Probes object reference identifier endpoints across dual test credentials."""

    @classmethod
    async def probe(
        cls,
        target_url: str,
        auth_header_a: dict[str, str],
        auth_header_b: dict[str, str],
        client: httpx.AsyncClient | None = None,
    ) -> Finding | None:
        async with (client or httpx.AsyncClient(timeout=10.0)) as cli:
            try:
                # Request resource as User A
                resp_a = await cli.get(target_url, headers=auth_header_a)
                if resp_a.status_code != 200:
                    return None

                # Request same private resource as User B
                resp_b = await cli.get(target_url, headers=auth_header_b)

                # If User B successfully reads User A's resource without restriction
                if resp_b.status_code == 200 and resp_b.text == resp_a.text:
                    return Finding(
                        engagement_id="default",
                        title=f"Insecure Direct Object Reference on {target_url}",
                        cls="idor",
                        asset_key=target_url,
                        endpoint=target_url,
                        severity=Severity.HIGH,
                        origin=FindingOrigin.NOVEL_ORACLE,
                        confidence=0.95,
                        verified=True,
                        evidence=[
                            f"status_user_a={resp_a.status_code}",
                            f"status_user_b={resp_b.status_code}",
                            f"length={len(resp_a.text)}",
                        ],
                    )
            except Exception:
                return None
        return None
