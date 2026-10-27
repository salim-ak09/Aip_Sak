from __future__ import annotations

import asyncio
from typing import Any

import httpx

from venice_pt.contracts.findings import Finding, FindingOrigin, Severity


class RaceConditionProbe:
    """Sends burst concurrent requests to detect TOCTOU race conditions."""

    @classmethod
    async def probe(
        cls,
        target_url: str,
        method: str = "POST",
        payload: dict[str, Any] | None = None,
        concurrency: int = 10,
        headers: dict[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> Finding | None:
        async with (client or httpx.AsyncClient(timeout=10.0)) as cli:
            async def send_req() -> httpx.Response:
                if method.upper() == "POST":
                    return await cli.post(target_url, json=payload, headers=headers)
                return await cli.get(target_url, headers=headers)

            tasks = [send_req() for _ in range(concurrency)]
            try:
                responses = await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                return None

        success_count = sum(
            1
            for r in responses
            if isinstance(r, httpx.Response) and r.status_code in (200, 201)
        )

        # In transactional actions (coupons, transfers), >1 success in single burst
        # signals race vulnerability
        if success_count > 1:
            return Finding(
                engagement_id="default",
                title=f"Potential Race Condition on {target_url}",
                cls="race_condition",
                asset_key=target_url,
                endpoint=target_url,
                severity=Severity.HIGH,
                origin=FindingOrigin.NOVEL_ORACLE,
                confidence=0.85,
                verified=True,
                evidence=[
                    f"concurrency={concurrency}",
                    f"success_count={success_count}",
                ],
            )

        return None
