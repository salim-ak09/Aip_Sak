from __future__ import annotations

import json
from urllib.parse import urlparse

from venice_pt.contracts.facts import Fact, FactKind
from venice_pt.parsers.base import ParserContext


def parse(stdout: bytes, ctx: ParserContext) -> list[Fact]:
    facts: list[Fact] = []
    text = stdout.decode("utf-8", errors="replace").strip()
    if not text:
        return facts

    for line in text.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except Exception:
            continue

        template_id = data.get("template-id") or data.get("info", {}).get("name", "vulnerability")
        matched = data.get("matched-at") or data.get("host", ctx.target)
        info = data.get("info", {})
        severity = info.get("severity", "info")

        parsed = urlparse(matched if "://" in matched else f"http://{matched}")
        host = parsed.hostname or matched
        asset_key = f"asset:{host}"

        finding_key = f"interesting:nuclei:{template_id}:{host}"
        facts.append(
            Fact(
                kind=FactKind.INTERESTING,
                key=finding_key,
                value={
                    "template_id": template_id,
                    "matched_at": matched,
                    "severity": severity,
                    "description": info.get("description"),
                    "tags": info.get("tags", []),
                },
                parent_key=asset_key,
                source_tool="nuclei",
                source_event=ctx.event_id,
                confidence=0.85,
                tags=["vuln", severity],
            )
        )

    return facts
