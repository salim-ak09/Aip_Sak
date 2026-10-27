from __future__ import annotations

from pathlib import Path

import yaml

from venice_pt.contracts.tools import ToolSpec
from venice_pt.registry.schema import validate_manifest_dict

DEFAULT_TOOLS_DIR = Path(__file__).resolve().parent / "tools"


class ToolRegistry:
    def __init__(self, tools_dir: Path | str = DEFAULT_TOOLS_DIR) -> None:
        self.tools_dir = Path(tools_dir)
        self._tools: dict[str, ToolSpec] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not self.tools_dir.exists():
            return

        for manifest_file in sorted(self.tools_dir.glob("*.yaml")):
            raw = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                continue
            validated = validate_manifest_dict(raw)
            self._tools[validated.name] = validated

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def find_by_capability(self, capability: str) -> list[ToolSpec]:
        return [t for t in self._tools.values() if capability in t.capabilities]

    def find_by_phase(self, phase: str) -> list[ToolSpec]:
        return [t for t in self._tools.values() if any(p.value == phase for p in t.phases)]
