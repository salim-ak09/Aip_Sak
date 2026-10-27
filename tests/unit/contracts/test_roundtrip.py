from __future__ import annotations

from venice_pt.contracts import (
    Action,
    Decision,
    Event,
    EventKind,
    Fact,
    FactKind,
    Finding,
    FindingOrigin,
    InstallStep,
    LLMRole,
    Msg,
    OutputSpec,
    Phase,
    Risk,
    Severity,
    ToolSpec,
    Verdict,
)


def test_event_roundtrip() -> None:
    event = Event(
        engagement_id="eng-123",
        phase=Phase.RECON,
        actor="runner",
        kind=EventKind.CMD,
        tool="nmap",
        cmd="nmap -sV 10.0.0.1",
        payload={"target": "10.0.0.1"},
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.001,
        duration_ms=1500,
    )
    json_data = event.model_dump_json()
    recovered = Event.model_validate_json(json_data)
    assert recovered == event


def test_tools_roundtrip() -> None:
    spec = ToolSpec(
        name="nmap",
        binary="nmap",
        version_pin="7.94",
        capabilities=["port_scan", "service_detection"],
        phases=[Phase.RECON, Phase.ENUM],
        risk=Risk.SAFE,
        timeout_s=120,
        needs=["cap_net_raw"],
        install=[InstallStep(method="apt", pkg="nmap")],
        check="--version",
        output=OutputSpec(
            format="xml",
            parser="venice_pt.parsers.nmap:parse",
            normalizes_to=["port", "service"],
        ),
        cost_class="cheap",
    )
    json_data = spec.model_dump_json()
    recovered = ToolSpec.model_validate_json(json_data)
    assert recovered == spec


def test_facts_roundtrip() -> None:
    fact = Fact(
        kind=FactKind.PORT,
        key="port:10.0.0.1:443/tcp",
        value={"port": 443, "proto": "tcp", "state": "open"},
        parent_key="asset:10.0.0.1",
        source_tool="nmap",
        source_event="evt-001",
        confidence=0.95,
        tags=["web", "ssl"],
    )
    json_data = fact.model_dump_json()
    recovered = Fact.model_validate_json(json_data)
    assert recovered == fact


def test_decisions_roundtrip() -> None:
    decision = Decision(
        action=Action.RUN_TOOL,
        tool="httpx",
        args=["-title", "-status-code"],
        target="10.0.0.1:443",
        rationale="Identify web service title on exposed port 443",
        confidence=0.88,
        risk=Risk.SAFE,
        expects=["service", "technology"],
        budget_hint_usd=0.02,
    )
    json_data = decision.model_dump_json()
    recovered = Decision.model_validate_json(json_data)
    assert recovered == decision


def test_findings_and_verdict_roundtrip() -> None:
    finding = Finding(
        engagement_id="eng-123",
        title="SQL Injection in /api/search",
        cls="sqli",
        asset_key="asset:example.com",
        endpoint="/api/search",
        param="q",
        severity=Severity.HIGH,
        cvss=8.5,
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
        cwe="CWE-89",
        owasp="A03:2021-Injection",
        origin=FindingOrigin.KNOWN_TOOL,
        confidence=0.9,
        verified=True,
        evidence=["artifacts/evt-10.out"],
        repro="curl 'http://example.com/api/search?q=1%27+OR+1=1--'",
        impact="Unauthorized access to user database",
        remediation="Use parameterized queries",
    )
    json_data = finding.model_dump_json()
    recovered = Finding.model_validate_json(json_data)
    assert recovered == finding

    verdict = Verdict(
        finding_id=finding.id,
        confirmed=True,
        method="timing_differential",
        evidence=["artifacts/verdict-1.out"],
        confidence_delta=0.1,
        notes="5 second sleep confirmed boolean timing difference",
    )
    verdict_json = verdict.model_dump_json()
    verdict_recovered = Verdict.model_validate_json(verdict_json)
    assert verdict_recovered == verdict


def test_llm_models_roundtrip() -> None:
    msg = Msg(role="user", content="Analyze exposed ports.")
    json_data = msg.model_dump_json()
    assert Msg.model_validate_json(json_data) == msg


def test_enum_stability() -> None:
    assert Phase.SCOPE == "scope"
    assert Phase.RECON == "recon"
    assert Phase.REPORT == "report"

    assert Risk.PASSIVE == 0
    assert Risk.SAFE == 1
    assert Risk.DESTRUCTIVE == 3

    assert EventKind.CMD == "cmd"
    assert EventKind.FACT == "fact"
    assert EventKind.FINDING == "finding"

    assert FactKind.PORT == "port"
    assert FactKind.CREDENTIAL == "credential"

    assert Action.RUN_TOOL == "run_tool"
    assert Action.FINISH == "finish"

    assert Severity.CRITICAL == "critical"
    assert FindingOrigin.NOVEL_ORACLE == "novel_oracle"
    assert LLMRole.PLANNER == "planner"
