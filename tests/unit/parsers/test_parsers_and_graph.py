from __future__ import annotations

from pathlib import Path

from venice_pt.contracts.facts import FactKind
from venice_pt.knowledge.graph import KnowledgeGraph
from venice_pt.knowledge.render import render_graph_for_llm, unexplored_surface
from venice_pt.parsers import (
    dnsx,
    ffuf,
    httpx,
    katana,
    nmap,
    nuclei,
    subfinder,
    whatweb,
)
from venice_pt.parsers.base import ParserContext

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


def test_nmap_parser_with_fixture() -> None:
    fixture = (FIXTURES_DIR / "nmap" / "sample.xml").read_bytes()
    ctx = ParserContext(tool="nmap", event_id="e-nmap", target="127.0.0.1")
    facts = nmap.parse(fixture, ctx)

    assert len(facts) >= 6
    kinds = {f.kind for f in facts}
    assert FactKind.ASSET in kinds
    assert FactKind.PORT in kinds
    assert FactKind.SERVICE in kinds


def test_httpx_parser_with_fixture() -> None:
    fixture = (FIXTURES_DIR / "httpx" / "sample.json").read_bytes()
    ctx = ParserContext(tool="httpx", event_id="e-httpx", target="127.0.0.1")
    facts = httpx.parse(fixture, ctx)

    assert len(facts) >= 4
    kinds = {f.kind for f in facts}
    assert FactKind.PORT in kinds
    assert FactKind.SERVICE in kinds
    assert FactKind.TECHNOLOGY in kinds


def test_nuclei_parser_with_fixture() -> None:
    fixture = (FIXTURES_DIR / "nuclei" / "sample.json").read_bytes()
    ctx = ParserContext(tool="nuclei", event_id="e-nuclei", target="127.0.0.1")
    facts = nuclei.parse(fixture, ctx)

    assert len(facts) == 2
    assert all(f.kind == FactKind.INTERESTING for f in facts)


def test_ffuf_parser_with_fixture() -> None:
    fixture = (FIXTURES_DIR / "ffuf" / "sample.json").read_bytes()
    ctx = ParserContext(tool="ffuf", event_id="e-ffuf", target="http://127.0.0.1:3000")
    facts = ffuf.parse(fixture, ctx)

    assert len(facts) == 2
    assert all(f.kind == FactKind.ENDPOINT for f in facts)


def test_subfinder_parser_with_fixture() -> None:
    fixture = (FIXTURES_DIR / "subfinder" / "sample.json").read_bytes()
    ctx = ParserContext(tool="subfinder", event_id="e-sub", target="example.com")
    facts = subfinder.parse(fixture, ctx)

    assert len(facts) == 6
    kinds = {f.kind for f in facts}
    assert FactKind.DNSRECORD in kinds
    assert FactKind.ASSET in kinds


def test_katana_parser_with_fixture() -> None:
    fixture = (FIXTURES_DIR / "katana" / "sample.json").read_bytes()
    ctx = ParserContext(tool="katana", event_id="e-katana", target="http://127.0.0.1:3000")
    facts = katana.parse(fixture, ctx)

    assert len(facts) == 3
    assert all(f.kind == FactKind.ENDPOINT for f in facts)


def test_dnsx_parser_with_fixture() -> None:
    fixture = (FIXTURES_DIR / "dnsx" / "sample.json").read_bytes()
    ctx = ParserContext(tool="dnsx", event_id="e-dnsx", target="example.com")
    facts = dnsx.parse(fixture, ctx)

    assert len(facts) == 2
    assert all(f.kind == FactKind.DNSRECORD for f in facts)


def test_whatweb_parser_with_fixture() -> None:
    fixture = (FIXTURES_DIR / "whatweb" / "sample.json").read_bytes()
    ctx = ParserContext(tool="whatweb", event_id="e-whatweb", target="http://127.0.0.1:3000")
    facts = whatweb.parse(fixture, ctx)

    assert len(facts) >= 3
    assert all(f.kind == FactKind.TECHNOLOGY for f in facts)


def test_graph_dedup_and_merge() -> None:
    """SPEC requirement: graph dedup (same port from two tools = one node, merged confidence)."""
    graph = KnowledgeGraph()

    ctx1 = ParserContext(tool="nmap", event_id="e1", target="127.0.0.1")
    nmap_facts = nmap.parse((FIXTURES_DIR / "nmap" / "sample.xml").read_bytes(), ctx1)

    ctx2 = ParserContext(tool="httpx", event_id="e2", target="127.0.0.1")
    httpx_facts = httpx.parse((FIXTURES_DIR / "httpx" / "sample.json").read_bytes(), ctx2)

    graph.add_facts(nmap_facts)
    count_before = graph.count()

    graph.add_facts(httpx_facts)
    count_after = graph.count()

    # Some facts are newly added (technologies), but shared ports are merged
    assert count_after > count_before
    node_port_80 = graph.nodes.get("port:127.0.0.1:80/tcp")
    assert node_port_80 is not None
    assert "nmap" in node_port_80.sources
    assert "httpx" in node_port_80.sources
    assert node_port_80.fact.confidence >= 0.99


def test_render_stays_under_4kb_with_5000_facts() -> None:
    """SPEC requirement: render stays under 4KB with 5000 facts."""
    from venice_pt.contracts.facts import Fact

    graph = KnowledgeGraph()
    # Add 5,000 synthetic facts
    facts: list[Fact] = []
    for i in range(5000):
        facts.append(
            Fact(
                kind=FactKind.ENDPOINT,
                key=f"endpoint:http://example.com/path_{i}",
                value={"url": f"http://example.com/path_{i}"},
                source_tool="fuzzer",
                source_event="evt-fuzz",
            )
        )
    graph.add_facts(facts)

    rendered = render_graph_for_llm(graph, max_bytes=4096)
    assert len(rendered.encode("utf-8")) <= 4096


def test_unexplored_surface_calculation() -> None:
    """SPEC requirement: unexplored surface computes unprobed assets."""
    from venice_pt.contracts.facts import Fact

    graph = KnowledgeGraph()
    # Add open port without any service attached
    graph.add_fact(
        Fact(
            kind=FactKind.PORT,
            key="port:10.0.0.1:22/tcp",
            value={"port": 22, "proto": "tcp"},
            source_tool="nmap",
            source_event="e1",
        )
    )

    surface = unexplored_surface(graph)
    assert len(surface) == 1
    assert surface[0]["type"] == "unprobed_port"
    assert surface[0]["target"] == "22/tcp"
