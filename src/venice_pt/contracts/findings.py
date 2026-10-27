from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


def new_id() -> str:
    return uuid.uuid4().hex


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingOrigin(StrEnum):
    KNOWN_TOOL = "known_tool"
    CVE_MATCH = "cve_match"
    NOVEL_ORACLE = "novel_oracle"
    LLM_HYPOTHESIS = "llm_hypothesis"


class Finding(BaseModel):
    id: str = Field(default_factory=new_id)
    engagement_id: str
    title: str
    cls: str
    asset_key: str
    endpoint: str | None = None
    param: str | None = None
    severity: Severity
    cvss: float | None = None
    cvss_vector: str | None = None
    cwe: str | None = None
    owasp: str | None = None
    origin: FindingOrigin
    confidence: float = Field(ge=0.0, le=1.0)
    verified: bool = False
    evidence: list[str] = Field(default_factory=list)
    repro: str | None = None
    impact: str | None = None
    remediation: str | None = None
    chains_with: list[str] = Field(default_factory=list)


class Verdict(BaseModel):
    finding_id: str
    confirmed: bool
    method: str
    evidence: list[str] = Field(default_factory=list)
    confidence_delta: float = 0.0
    notes: str | None = None
