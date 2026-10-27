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

        url = data.get("url") or data.get("input")
        if not url:
            continue

        parsed = urlparse(url)
        host = parsed.hostname or ctx.target or "unknown"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        asset_key = f"asset:{host}"
        port_key = f"port:{host}:{port}/tcp"

        facts.append(
            Fact(
                kind=FactKind.PORT,
                key=port_key,
                value={"port": port, "proto": "tcp", "state": "open"},
                parent_key=asset_key,
                source_tool="httpx",
                source_event=ctx.event_id,
                confidence=0.95,
            )
        )

        svc_key = f"service:{host}:{port}/tcp/http"
        title = data.get("title")
        status_code = data.get("status_code")
        webserver = data.get("webserver")

        facts.append(
            Fact(
                kind=FactKind.SERVICE,
                key=svc_key,
                value={
                    "service": "http",
                    "title": title,
                    "status_code": status_code,
                    "webserver": webserver,
                    "url": url,
                },
                parent_key=port_key,
                source_tool="httpx",
                source_event=ctx.event_id,
                confidence=0.95,
            )
        )

        # Technologies
        techs = data.get("tech", [])
        if isinstance(techs, list):
            for t in techs:
                tech_key = f"technology:{host}:{t.lower()}"
                facts.append(
                    Fact(
                        kind=FactKind.TECHNOLOGY,
                        key=tech_key,
                        value={"name": t, "host": host},
                        parent_key=svc_key,
                        source_tool="httpx",
                        source_event=ctx.event_id,
                        confidence=0.9,
                    )
                )

    return facts
