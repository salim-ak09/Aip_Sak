from __future__ import annotations

from pydantic import BaseModel, Field

from venice_pt.contracts.findings import Finding


class AttackStep(BaseModel):
    step_id: int
    primitive: str
    target: str
    action: str
    outcome: str


class AttackChain(BaseModel):
    chain_id: str
    title: str
    initial_severity: str
    composite_severity: str
    steps: list[AttackStep] = Field(default_factory=list)
    impact: str


class ChainPlanner:
    """Synthesizes high-impact exploit chains from isolated atomic primitives."""

    @classmethod
    def synthesize_chains(cls, findings: list[Finding]) -> list[AttackChain]:
        chains: list[AttackChain] = []
        classes = {f.cls.lower(): f for f in findings}

        # Pattern 1: Auth Bypass / Info Leak + IDOR -> Account Takeover (ATO)
        if ("swagger" in classes or "info_leak" in classes) and "idor" in classes:
            leak_finding = classes.get("swagger") or classes.get("info_leak")
            idor_finding = classes["idor"]
            leak_target = (
                (leak_finding.endpoint or leak_finding.asset_key)
                if leak_finding
                else "api"
            )
            idor_target = idor_finding.endpoint or idor_finding.asset_key
            chains.append(
                AttackChain(
                    chain_id="CHAIN-ATO-01",
                    title="Account Takeover via API Info Leak and IDOR",
                    initial_severity="Medium",
                    composite_severity="Critical",
                    steps=[
                        AttackStep(
                            step_id=1,
                            primitive=leak_finding.cls if leak_finding else "info_leak",
                            target=leak_target,
                            action="Enumerate unprotected administrative endpoints and object IDs",
                            outcome="Disclosed internal schema and user ID format",
                        ),
                        AttackStep(
                            step_id=2,
                            primitive="idor",
                            target=idor_target,
                            action="Replay object ID in authorization context of unprivileged user",
                            outcome=(
                                "Unauthorized access and modification of administrative profile"
                            ),
                        ),
                    ],
                    impact=(
                        "Full Account Takeover and privilege escalation to platform administrator."
                    ),
                )
            )

        # Pattern 2: SSRF + Internal Metadata / Cloud API
        if "ssrf" in classes:
            ssrf_finding = classes["ssrf"]
            ssrf_target = ssrf_finding.endpoint or ssrf_finding.asset_key
            chains.append(
                AttackChain(
                    chain_id="CHAIN-CLOUD-01",
                    title="Cloud Credential Exfiltration via SSRF",
                    initial_severity="High",
                    composite_severity="Critical",
                    steps=[
                        AttackStep(
                            step_id=1,
                            primitive="ssrf",
                            target=ssrf_target,
                            action="Inject link-local metadata address (169.254.169.254)",
                            outcome="Server fetches internal IAM instance security credentials",
                        )
                    ],
                    impact="Compromise of backend cloud IAM role and lateral movement.",
                )
            )

        return chains
