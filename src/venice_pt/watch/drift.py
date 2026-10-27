from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DriftDelta(BaseModel):
    new_assets: list[str] = Field(default_factory=list)
    removed_assets: list[str] = Field(default_factory=list)
    new_ports: list[dict[str, Any]] = Field(default_factory=list)
    closed_ports: list[dict[str, Any]] = Field(default_factory=list)
    has_drift: bool = False


class SurfaceDriftDetector:
    """Compares current attack surface facts against previous snapshot."""

    @classmethod
    def detect_drift(
        cls,
        previous_snapshot: dict[str, Any],
        current_snapshot: dict[str, Any],
    ) -> DriftDelta:
        prev_assets = set(previous_snapshot.get("assets", []))
        curr_assets = set(current_snapshot.get("assets", []))

        new_assets = sorted(list(curr_assets - prev_assets))
        removed_assets = sorted(list(prev_assets - curr_assets))

        prev_ports = {
            f"{p.get('host')}:{p.get('port')}"
            for p in previous_snapshot.get("ports", [])
        }
        curr_ports = {
            f"{p.get('host')}:{p.get('port')}": p
            for p in current_snapshot.get("ports", [])
        }

        new_ports = [
            curr_ports[k]
            for k in sorted(curr_ports.keys())
            if k not in prev_ports
        ]
        closed_ports = [
            {"host": k.split(":")[0], "port": int(k.split(":")[1])}
            for k in sorted(prev_ports)
            if k not in curr_ports
        ]

        has_drift = bool(new_assets or removed_assets or new_ports or closed_ports)

        return DriftDelta(
            new_assets=new_assets,
            removed_assets=removed_assets,
            new_ports=new_ports,
            closed_ports=closed_ports,
            has_drift=has_drift,
        )
