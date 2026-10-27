from __future__ import annotations

from enum import StrEnum
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMRole(StrEnum):
    TRIAGE = "triage"
    PLANNER = "planner"
    ANALYST = "analyst"
    REPORTER = "reporter"


class Msg(BaseModel):
    role: str
    content: str


class LLMResult(BaseModel):
    text: str
    parsed: BaseModel | None = None
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int


class LLMClient(Protocol):
    async def complete(
        self,
        role: LLMRole,
        messages: list[Msg],
        schema: type[T] | None = None,
        max_tokens: int = 2048,
    ) -> LLMResult: ...
