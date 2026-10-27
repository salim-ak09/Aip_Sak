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
        ip = None
        if line.startswith("{"):
            try:
                data = json.loads(line)
                host = data.get("host") or ""
                ip = data.get("ip")
            except Exception:
                continue
        else:
            host = line

        if host:
            dns_key = f"dns_record:{host}"
            facts.append(
                Fact(
                    kind=FactKind.DNSRECORD,
                    key=dns_key,
                    value={"host": host, "ip": ip},
                    source_tool="subfinder",
                    source_event=ctx.event_id,
                    confidence=1.0,
                )
            )
            facts.append(
                Fact(
                    kind=FactKind.ASSET,
                    key=f"asset:{host}",
                    value={"domain": host, "source": "subdomain_enum"},
                    parent_key=dns_key,
                    source_tool="subfinder",
                    source_event=ctx.event_id,
                    confidence=0.9,
                )
            )

    return facts
