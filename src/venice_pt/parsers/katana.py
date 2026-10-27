from __future__ import annotations

import json

from venice_pt.contracts.facts import Fact, FactKind
from venice_pt.parsers.base import ParserContext


def parse(stdout: bytes, ctx: ParserContext) -> list[Fact]:
    facts: list[Fact] = []
    text = stdout.decode("utf-8", errors="replace").strip()
    if not text:
        return facts

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        endpoint = ""
        method = "GET"
        if line.startswith("{"):
            try:
                data = json.loads(line)
                req = data.get("request", {})
                endpoint = req.get("endpoint") or data.get("url") or ""
                method = req.get("method", "GET")
            except Exception:
                continue
        else:
            endpoint = line

        if endpoint:
            facts.append(
                Fact(
                    kind=FactKind.ENDPOINT,
                    key=f"endpoint:{endpoint}",
                    value={"url": endpoint, "method": method},
                    parent_key=f"asset:{ctx.target}",
                    source_tool="katana",
                    source_event=ctx.event_id,
                    confidence=1.0,
                    tags=["crawled"],
                )
            )

    return facts
