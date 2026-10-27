from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import IntEnum, StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.0.0"


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(UTC)


class Phase(StrEnum):
    SCOPE = "scope"
    RECON = "recon"
    ENUM = "enum"
    VULN_SCAN = "vuln_scan"
    NOVEL_FUZZ = "novel_fuzz"
    VALIDATE = "validate"
    CHAIN = "chain"
    REPORT = "report"


class Risk(IntEnum):
    PASSIVE = 0
    SAFE = 1
    INTRUSIVE = 2
    DESTRUCTIVE = 3


class EventKind(StrEnum):
    ENGAGEMENT_START = "engagement_start"
    PHASE_ENTER = "phase_enter"
    THOUGHT = "thought"
    PLAN = "plan"
    CMD = "cmd"
    STDOUT = "stdout"
    STDERR = "stderr"
    FACT = "fact"
    FINDING = "finding"
    VERDICT = "verdict"
    APPROVAL_REQ = "approval_req"
    APPROVAL_RES = "approval_res"
    ERROR = "error"
    ARTIFACT = "artifact"
    METRIC = "metric"
    PHASE_EXIT = "phase_exit"
    ENGAGEMENT_END = "engagement_end"


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_id)
    engagement_id: str
    ts: datetime = Field(default_factory=utcnow)
    phase: Phase
    actor: Literal["planner", "runner", "parser", "verifier", "reporter", "human", "system"]
    kind: EventKind
    tool: str | None = None
    cmd: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    parent_id: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
