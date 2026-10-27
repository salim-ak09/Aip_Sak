from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class FactKind(StrEnum):
    ASSET = "asset"
    PORT = "port"
    SERVICE = "service"
    TECHNOLOGY = "technology"
    ENDPOINT = "endpoint"
    PARAM = "param"
    CREDENTIAL = "credential"
    SECRET = "secret"
    VERSION = "version"
    HEADER = "header"
    CERT = "cert"
    DNSRECORD = "dns_record"
    INTERESTING = "interesting"


class Fact(BaseModel):
    kind: FactKind
    key: str
    value: dict[str, Any]
    parent_key: str | None = None
    source_tool: str
    source_event: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    tags: list[str] = Field(default_factory=list)
