from __future__ import annotations

from typing import Protocol

import httpx

from venice_pt.contracts.findings import Finding, Verdict


class VerificationRule(Protocol):
    async def verify(
        self,
        finding: Finding,
        client: httpx.AsyncClient | None = None,
    ) -> Verdict: ...
