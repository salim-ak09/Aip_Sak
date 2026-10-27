from __future__ import annotations

from venice_pt.contracts.decisions import Action, Decision
from venice_pt.contracts.events import Phase, Risk
from venice_pt.contracts.tools import ToolSpec
from venice_pt.registry.loader import ToolRegistry

# Static capabilities required per pentest phase
PHASE_CAPABILITIES: dict[Phase, list[str]] = {
    Phase.SCOPE: [],
    Phase.RECON: ["subdomain_enum", "port_scan", "http_probe"],
    Phase.ENUM: ["web_crawling", "web_fuzzing"],
    Phase.VULN_SCAN: ["vulnerability_scan", "misconfig_scan"],
    Phase.NOVEL_FUZZ: ["web_fuzzing"],
    Phase.VALIDATE: ["http_probe"],
    Phase.CHAIN: [],
    Phase.REPORT: [],
}

COST_PRIORITY = {"cheap": 1, "medium": 2, "heavy": 3}


class StaticPolicyRouter:
    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or ToolRegistry()

    def get_required_capabilities(self, phase: Phase) -> list[str]:
        return PHASE_CAPABILITIES.get(phase, [])

    def select_tools_for_phase(
        self,
        phase: Phase,
        already_run_tools: set[str],
        risk_ceiling: Risk = Risk.SAFE,
    ) -> list[ToolSpec]:
        """Selects the cheapest tools satisfying capabilities not yet executed."""
        required_caps = self.get_required_capabilities(phase)
        if not required_caps:
            return []

        selected: list[ToolSpec] = []
        covered_caps: set[str] = set()

        # Find all tools supporting this phase within risk ceiling
        available_tools = [
            t
            for t in self.registry.list_tools()
            if any(p == phase for p in t.phases)
            and t.risk <= risk_ceiling
            and t.name not in already_run_tools
        ]

        # Sort by cost class (cheapest first)
        available_tools.sort(key=lambda t: COST_PRIORITY.get(t.cost_class, 2))

        for cap in required_caps:
            if cap in covered_caps:
                continue
            for tool in available_tools:
                if cap in tool.capabilities and tool not in selected:
                    selected.append(tool)
                    for c in tool.capabilities:
                        covered_caps.add(c)
                    break

        return selected

    def make_decision(
        self,
        phase: Phase,
        target: str,
        already_run_tools: set[str],
        risk_ceiling: Risk = Risk.SAFE,
    ) -> Decision:
        tools = self.select_tools_for_phase(phase, already_run_tools, risk_ceiling)
        if tools:
            tool = tools[0]
            args: list[str] = []
            if tool.name == "nmap":
                args = ["-sV", "-p", "80,443,3000,8080", target]
            elif tool.name == "httpx":
                args = ["-json", "-title", "-u", target]
            elif tool.name == "nuclei":
                args = ["-u", target, "-json"]
            else:
                args = [target]

            return Decision(
                action=Action.RUN_TOOL,
                tool=tool.name,
                args=args,
                target=target,
                rationale=f"Static policy selected {tool.name} for phase {phase.value}",
                confidence=0.9,
                risk=tool.risk,
                expects=tool.output.normalizes_to,
            )

        return Decision(
            action=Action.ADVANCE_PHASE,
            rationale=f"All phase {phase.value} capabilities satisfied. Advance to next phase.",
            confidence=1.0,
            risk=Risk.SAFE,
        )
