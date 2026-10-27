from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from venice_pt.contracts.events import Phase, Risk


class OutputSpec(BaseModel):
    format: Literal["json", "xml", "csv", "text", "sarif"]
    parser: str
    normalizes_to: list[str] = Field(default_factory=list)


class InstallStep(BaseModel):
    method: Literal[
        "apt",
        "dnf",
        "pacman",
        "brew",
        "pipx",
        "go",
        "cargo",
        "github_release",
        "docker",
        "script",
    ]
    pkg: str | None = None
    image: str | None = None
    entrypoint: str | None = None
    url: str | None = None
    script: str | None = None


class ToolSpec(BaseModel):
    name: str
    binary: str
    version_pin: str | None = None
    capabilities: list[str]
    phases: list[Phase]
    risk: Risk
    timeout_s: int = 300
    needs: list[str] = Field(default_factory=list)
    install: list[InstallStep]
    check: str
    output: OutputSpec
    cost_class: Literal["cheap", "medium", "heavy"] = "cheap"
    notes: str | None = None
