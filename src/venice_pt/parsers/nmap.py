from __future__ import annotations

import xml.etree.ElementTree as ET

from venice_pt.contracts.facts import Fact, FactKind
from venice_pt.parsers.base import ParserContext


def parse(stdout: bytes, ctx: ParserContext) -> list[Fact]:
    facts: list[Fact] = []
    text = stdout.decode("utf-8", errors="replace").strip()
    if not text:
        return facts

    # Parse XML if possible
    try:
        root = ET.fromstring(text)
        for host in root.findall("host"):
            status_elem = host.find("status")
            if status_elem is not None and status_elem.get("state") != "up":
                continue

            # Extract IP address
            addr_elem = host.find("address")
            ip = addr_elem.get("addr") if addr_elem is not None else ctx.target
            asset_key = f"asset:{ip}"

            facts.append(
                Fact(
                    kind=FactKind.ASSET,
                    key=asset_key,
                    value={"ip": ip, "status": "up"},
                    source_tool="nmap",
                    source_event=ctx.event_id,
                    confidence=1.0,
                )
            )

            # Ports and services
            ports_elem = host.find("ports")
            if ports_elem is not None:
                for p in ports_elem.findall("port"):
                    portid = p.get("portid")
                    proto = p.get("protocol", "tcp")
                    state_elem = p.find("state")
                    if state_elem is not None and state_elem.get("state") != "open":
                        continue

                    port_key = f"port:{ip}:{portid}/{proto}"
                    service_elem = p.find("service")
                    svc_name = service_elem.get("name") if service_elem is not None else "unknown"
                    product = service_elem.get("product") if service_elem is not None else None
                    version = service_elem.get("version") if service_elem is not None else None

                    facts.append(
                        Fact(
                            kind=FactKind.PORT,
                            key=port_key,
                            value={"port": int(portid or 0), "proto": proto, "state": "open"},
                            parent_key=asset_key,
                            source_tool="nmap",
                            source_event=ctx.event_id,
                            confidence=1.0,
                            tags=[proto],
                        )
                    )

                    svc_key = f"service:{ip}:{portid}/{proto}/{svc_name}"
                    facts.append(
                        Fact(
                            kind=FactKind.SERVICE,
                            key=svc_key,
                            value={
                                "service": svc_name,
                                "product": product,
                                "version": version,
                                "port": int(portid or 0),
                            },
                            parent_key=port_key,
                            source_tool="nmap",
                            source_event=ctx.event_id,
                            confidence=0.9,
                        )
                    )
        return facts
    except Exception:
        # Fallback minimal plain text parse if stdout is not XML
        for line in text.splitlines():
            if "/tcp" in line and "open" in line:
                parts = line.split()
                port_proto = parts[0]
                port_num = port_proto.split("/")[0]
                ip = ctx.target or "127.0.0.1"
                asset_key = f"asset:{ip}"
                port_key = f"port:{ip}:{port_num}/tcp"
                facts.append(
                    Fact(
                        kind=FactKind.PORT,
                        key=port_key,
                        value={"port": int(port_num), "proto": "tcp", "state": "open"},
                        parent_key=asset_key,
                        source_tool="nmap",
                        source_event=ctx.event_id,
                        confidence=0.8,
                    )
                )
        return facts
