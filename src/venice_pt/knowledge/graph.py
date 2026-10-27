from __future__ import annotations

from dataclasses import dataclass, field

from venice_pt.contracts.facts import Fact, FactKind


@dataclass
class GraphNode:
    fact: Fact
    children_keys: set[str] = field(default_factory=set)
    sources: list[str] = field(default_factory=list)


class KnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        self._by_kind: dict[FactKind, set[str]] = {k: set() for k in FactKind}

    def add_fact(self, fact: Fact) -> None:
        """Adds or merges a fact node with deduplication and confidence combination."""
        if fact.key in self.nodes:
            # Deduplicate node: merge confidence and sources
            existing = self.nodes[fact.key]
            # Probabilistic union of confidence: 1 - (1 - c1)*(1 - c2)
            merged_conf = 1.0 - (1.0 - existing.fact.confidence) * (1.0 - fact.confidence)
            existing.fact.confidence = min(1.0, round(merged_conf, 3))
            if fact.source_tool not in existing.sources:
                existing.sources.append(fact.source_tool)
            # Update tags
            existing.fact.tags = list(set(existing.fact.tags + fact.tags))
            return

        node = GraphNode(fact=fact, sources=[fact.source_tool])
        self.nodes[fact.key] = node
        self._by_kind[fact.kind].add(fact.key)

        # Connect parent edge
        if fact.parent_key and fact.parent_key in self.nodes:
            self.nodes[fact.parent_key].children_keys.add(fact.key)

    def add_facts(self, facts: list[Fact]) -> None:
        for f in facts:
            self.add_fact(f)

    def children(self, key: str) -> list[Fact]:
        node = self.nodes.get(key)
        if not node:
            return []
        return [self.nodes[child_k].fact for child_k in node.children_keys if child_k in self.nodes]

    def subtree(self, root_key: str) -> list[Fact]:
        result: list[Fact] = []
        stack = [root_key]
        visited: set[str] = set()

        while stack:
            curr = stack.pop()
            if curr in visited or curr not in self.nodes:
                continue
            visited.add(curr)
            node = self.nodes[curr]
            result.append(node.fact)
            stack.extend(node.children_keys)

        return result

    def by_kind(self, kind: FactKind) -> list[Fact]:
        return [self.nodes[k].fact for k in self._by_kind.get(kind, set()) if k in self.nodes]

    def count(self) -> int:
        return len(self.nodes)
