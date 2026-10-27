from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from venice_pt.contracts.facts import Fact


@dataclass
class ParserContext:
    tool: str
    event_id: str
    target: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class Parser(Protocol):
    def parse(self, stdout: bytes, ctx: ParserContext) -> list[Fact]: ...
