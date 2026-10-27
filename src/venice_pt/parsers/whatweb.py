from __future__ import annotations

import json

from venice_pt.contracts.facts import Fact, FactKind
from venice_pt.parsers.base import ParserContext


def parse(stdout: bytes, ctx: ParserContext) -> list[Fact]:
    facts: list[Fact] = []
    text = stdout.decode("utf-8", errors="replace").strip()
    if not text:
        return facts

    try:
        data = json.loads(text)
        entries = data if isinstance(data, list) else [data]
    except Exception:
        entries = []

    for entry in entries:
        target = entry.get("target") or ctx.target or "unknown"
        plugins = entry.get("plugins", {})
        for plugin_name, details in plugins.items():
            version = None
            if isinstance(details, dict):
                version_list = details.get("version", [])
                version = version_list[0] if version_list else None

            tech_key = f"technology:{target}:{plugin_name.lower()}"
            facts.append(
                Fact(
                    kind=FactKind.TECHNOLOGY,
                    key=tech_key,
                    value={
                        "target": target,
                        "plugin": plugin_name,
                        "version": version,
                    },
                    parent_key=f"asset:{target}",
                    source_tool="whatweb",
                    source_event=ctx.event_id,
                    confidence=0.85,
                )
            )

    return facts
