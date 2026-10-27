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
        host = ""
        ips: list[str] = []
        if line.startswith("{"):
            try:
                data = json.loads(line)
                host = data.get("host") or ""
                a_records = data.get("a", [])
                ips = a_records if isinstance(a_records, list) else [str(a_records)]
            except Exception:
                continue
        else:
            host = line

        if host:
            facts.append(
                Fact(
                    kind=FactKind.DNSRECORD,
                    key=f"dns_record:{host}",
                    value={"host": host, "ips": ips},
                    source_tool="dnsx",
                    source_event=ctx.event_id,
                    confidence=1.0,
                )
            )

    return facts
