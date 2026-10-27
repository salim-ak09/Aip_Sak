from __future__ import annotations

from typing import Any

from venice_pt.contracts.events import Event, EventKind, Phase
from venice_pt.contracts.findings import FindingOrigin, Severity


def engagement_summary(events: list[Event]) -> dict[str, Any]:
    """Computes a high-level summary of the engagement state."""
    if not events:
        return {
            "engagement_id": None,
            "status": "not_started",
            "event_count": 0,
            "phases_visited": [],
            "tools_run": [],
        }

    engagement_id = events[0].engagement_id
    phases_visited: list[str] = []
    tools_run: set[str] = set()
    errors_count = 0

    for e in events:
        if e.phase.value not in phases_visited:
            phases_visited.append(e.phase.value)
        if e.tool:
            tools_run.add(e.tool)
        if e.kind == EventKind.ERROR:
            errors_count += 1

    last_kind = events[-1].kind
    status = "completed" if last_kind == EventKind.ENGAGEMENT_END else "in_progress"

    return {
        "engagement_id": engagement_id,
        "status": status,
        "event_count": len(events),
        "phases_visited": phases_visited,
        "tools_run": sorted(tools_run),
        "errors_count": errors_count,
        "start_time": events[0].ts.isoformat(),
        "latest_time": events[-1].ts.isoformat(),
    }


def phase_progress(events: list[Event]) -> dict[str, Any]:
    """Computes progress through the pentest phases."""
    current_phase: Phase = Phase.SCOPE
    counts_by_phase: dict[str, int] = {p.value: 0 for p in Phase}

    for e in events:
        counts_by_phase[e.phase.value] += 1
        if e.kind == EventKind.PHASE_ENTER:
            current_phase = e.phase

    return {
        "current_phase": current_phase.value,
        "phase_event_counts": counts_by_phase,
    }


def findings_table(events: list[Event]) -> list[dict[str, Any]]:
    """Extracts confirmed and unconfirmed findings from finding and verdict events."""
    findings_map: dict[str, dict[str, Any]] = {}

    for e in events:
        if e.kind == EventKind.FINDING and e.payload:
            payload = e.payload
            f_id = payload.get("id") or e.id
            findings_map[f_id] = {
                "id": f_id,
                "engagement_id": e.engagement_id,
                "title": payload.get("title", "Untitled finding"),
                "cls": payload.get("cls", "misconfig"),
                "asset_key": payload.get("asset_key", "unknown"),
                "endpoint": payload.get("endpoint"),
                "param": payload.get("param"),
                "severity": payload.get("severity", Severity.INFO.value),
                "cvss": payload.get("cvss"),
                "origin": payload.get("origin", FindingOrigin.KNOWN_TOOL.value),
                "confidence": payload.get("confidence", 0.5),
                "verified": payload.get("verified", False),
                "evidence": payload.get("evidence", []),
            }
        elif e.kind == EventKind.VERDICT and e.payload:
            finding_id = e.payload.get("finding_id")
            if finding_id and finding_id in findings_map:
                f = findings_map[finding_id]
                f["verified"] = e.payload.get("confirmed", f["verified"])
                f["confidence"] = min(
                    1.0, max(0.0, f["confidence"] + e.payload.get("confidence_delta", 0.0))
                )
                extra_evidence = e.payload.get("evidence", [])
                f["evidence"] = list(set(f["evidence"] + extra_evidence))

    return list(findings_map.values())


def cost_meter(events: list[Event]) -> dict[str, Any]:
    """Calculates LLM token usage, duration, and financial spend."""
    total_tokens_in = 0
    total_tokens_out = 0
    total_cost_usd = 0.0
    total_duration_ms = 0
    cost_by_phase: dict[str, float] = {p.value: 0.0 for p in Phase}

    for e in events:
        total_tokens_in += e.tokens_in
        total_tokens_out += e.tokens_out
        total_cost_usd += e.cost_usd
        total_duration_ms += e.duration_ms
        cost_by_phase[e.phase.value] += e.cost_usd

    return {
        "tokens_in": total_tokens_in,
        "tokens_out": total_tokens_out,
        "total_tokens": total_tokens_in + total_tokens_out,
        "total_cost_usd": round(total_cost_usd, 5),
        "total_duration_s": round(total_duration_ms / 1000.0, 2),
        "cost_by_phase": {k: round(v, 5) for k, v in cost_by_phase.items() if v > 0},
    }
