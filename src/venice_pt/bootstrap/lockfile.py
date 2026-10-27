from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

DEFAULT_LOCKFILE = Path.home() / ".venicept" / "toolchain.lock"


class ToolLockEntry(BaseModel):
    tool: str
    version: str | None = None
    method: str
    path: str | None = None
    sha256: str | None = None


class ToolchainLock(BaseModel):
    tools: dict[str, ToolLockEntry] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = DEFAULT_LOCKFILE) -> ToolchainLock:
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls.model_validate(data)
        except Exception:
            return cls()

    def save(self, path: Path = DEFAULT_LOCKFILE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    def record(
        self,
        tool: str,
        method: str,
        version: str | None = None,
        path: str | None = None,
        sha256: str | None = None,
    ) -> None:
        self.tools[tool] = ToolLockEntry(
            tool=tool, version=version, method=method, path=path, sha256=sha256
        )
