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
        results = data.get("results", [])
    except Exception:
        results = []

    for r in results:
        url = r.get("url")
        status = r.get("status")
        words = r.get("words")
        length = r.get("length")

        if not url:
            continue

        endpoint_key = f"endpoint:{url}"
        facts.append(
            Fact(
                kind=FactKind.ENDPOINT,
                key=endpoint_key,
                value={
                    "url": url,
                    "status_code": status,
                    "words": words,
                    "length": length,
                },
                parent_key=f"asset:{ctx.target}",
                source_tool="ffuf",
                source_event=ctx.event_id,
                confidence=1.0,
                tags=["fuzz", f"status:{status}"],
            )
        )

    return facts
