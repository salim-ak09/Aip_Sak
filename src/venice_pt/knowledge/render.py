from __future__ import annotations

from typing import Any

from venice_pt.contracts.facts import FactKind
from venice_pt.knowledge.graph import KnowledgeGraph


def render_graph_for_llm(graph: KnowledgeGraph, max_bytes: int = 4096) -> str:
    """Renders a compact summary of the knowledge graph strictly under max_bytes."""
    lines: list[str] = ["# ATTACK SURFACE GRAPH SUMMARY\n"]

    # 1. Assets and Open Services (Highest priority)
    assets = graph.by_kind(FactKind.ASSET)
    ports = graph.by_kind(FactKind.PORT)

    lines.append(f"## Discovered Hosts ({len(assets)}):")
    for a in assets[:10]:
        lines.append(f"- {a.value.get('ip') or a.value.get('domain') or a.key}")

    lines.append(f"\n## Open Ports & Services ({len(ports)}):")
    for p in ports[:30]:
        lines.append(f"- {p.key}: {p.value.get('port')}/{p.value.get('proto')}")

    # 2. Technologies and Versions
    techs = graph.by_kind(FactKind.TECHNOLOGY)
    if techs:
        lines.append(f"\n## Technologies ({len(techs)}):")
        for t in techs[:25]:
            v_str = f" v{t.value.get('version')}" if t.value.get("version") else ""
            lines.append(f"- {t.value.get('name') or t.value.get('plugin')}{v_str}")

    # 3. High Value Findings / Interesting
    findings = graph.by_kind(FactKind.INTERESTING)
    if findings:
        lines.append(f"\n## Findings & Anomalies ({len(findings)}):")
        for f in findings[:15]:
            sev = f.value.get("severity", "info").upper()
            tpl = f.value.get("template_id")
            target = f.value.get("matched_at")
            lines.append(f"- [{sev}] {tpl}: {target}")

    # 4. Endpoints summary
    endpoints = graph.by_kind(FactKind.ENDPOINT)
    lines.append(f"\n## Endpoints: {len(endpoints)} discovered.")
    if endpoints:
        lines.append("Top Endpoints:")
        for ep in endpoints[:20]:
            lines.append(f"- {ep.value.get('url')}")

    full_text = "\n".join(lines)
    encoded = full_text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return full_text

    # Truncate while keeping header and critical services
    truncated = encoded[: max_bytes - 32].decode("utf-8", errors="ignore")
    return truncated + "\n...[truncated to 4KB]"


def unexplored_surface(graph: KnowledgeGraph) -> list[dict[str, Any]]:
    """Identifies unexplored attack surface (e.g. unprobed ports or endpoints)."""
    unexplored: list[dict[str, Any]] = []

    # Ports that don't have associated service facts
    for p in graph.by_kind(FactKind.PORT):
        children = graph.children(p.key)
        if not any(c.kind == FactKind.SERVICE for c in children):
            unexplored.append({
                "type": "unprobed_port",
                "key": p.key,
                "target": f"{p.value.get('port')}/{p.value.get('proto')}",
            })

    # HTTP services that haven't been fuzzed or crawled
    for s in graph.by_kind(FactKind.SERVICE):
        children = graph.children(s.key)
        has_endpoints = any(c.kind == FactKind.ENDPOINT for c in children)
        if not has_endpoints:
            unexplored.append({
                "type": "uncrawled_service",
                "key": s.key,
                "target": s.value.get("url") or s.key,
            })

    return unexplored
