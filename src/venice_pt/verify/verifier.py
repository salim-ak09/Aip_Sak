from __future__ import annotations

import httpx

from venice_pt.contracts.findings import Finding, Verdict
from venice_pt.verify.rules.base import VerificationRule
from venice_pt.verify.rules.reachability import ReachabilityVerifier
from venice_pt.verify.rules.sqli import SQLiVerifier
from venice_pt.verify.rules.xss import XSSVerifier


class Verifier:
    def __init__(self) -> None:
        self.rules: dict[str, VerificationRule] = {
            "sqli": SQLiVerifier(),
            "xss": XSSVerifier(),
            "misconfig": ReachabilityVerifier(),
            "cve_match": ReachabilityVerifier(),
        }
        self.default_rule = ReachabilityVerifier()

    async def check(
        self,
        finding: Finding,
        client: httpx.AsyncClient | None = None,
    ) -> Verdict:
        """Dispatches finding verification and applies confidence penalty
        to unconfirmed findings.
        """
        rule = self.rules.get(finding.cls.lower(), self.default_rule)
        verdict = await rule.verify(finding, client=client)

        if not verdict.confirmed:
            # SPEC: Unconfirmed -> confidence *= 0.4
            finding.confidence = round(finding.confidence * 0.4, 3)
            finding.verified = False
        else:
            finding.verified = True
            finding.confidence = min(1.0, round(finding.confidence + verdict.confidence_delta, 3))
            finding.evidence.extend(verdict.evidence)

        return verdict
