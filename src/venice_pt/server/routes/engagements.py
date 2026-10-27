from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from venice_pt.server.auth import verify_token

router = APIRouter(prefix="/api/engagements", tags=["engagements"])


class EngagementCreate(BaseModel):
    name: str = Field(..., description="Unique engagement name or slug")
    target: str = Field(..., description="Primary domain, URL, or IP")
    profile: str = Field("standard", description="Scan profile")
    risk_level: int = Field(
        0, description="Authorized risk level: 0=passive, 1=active, 2=destructive"
    )


@router.get("", dependencies=[Depends(verify_token)])
def list_engagements() -> list[dict[str, Any]]:
    engagements_dir = Path("engagements")
    if not engagements_dir.exists():
        return []

    results = []
    for p in engagements_dir.iterdir():
        if p.is_dir():
            state_file = p / "state.json"
            target = "unknown"
            phase = "unknown"
            if state_file.exists():
                try:
                    data = json.loads(state_file.read_text(encoding="utf-8"))
                    target = data.get("target", target)
                    phase = data.get("phase", phase)
                except Exception:
                    pass
            results.append(
                {
                    "name": p.name,
                    "target": target,
                    "phase": phase,
                    "path": str(p),
                }
            )
    return results


@router.post("", dependencies=[Depends(verify_token)], status_code=201)
def create_engagement(payload: EngagementCreate) -> dict[str, Any]:
    from venice_pt.cli.init_cmd import init_engagement
    eng_dir = Path("engagements") / payload.name
    if eng_dir.exists():
        raise HTTPException(status_code=400, detail="Engagement already exists")

    init_engagement(name=payload.name, target=payload.target)
    state_file = eng_dir / "state.json"
    initial_state = {
        "engagement": payload.name,
        "target": payload.target,
        "profile": payload.profile,
        "risk_level": payload.risk_level,
        "phase": "scope",
        "status": "ready",
        "findings": [],
        "operator_instructions": [],
        "chat_history": [
            {
                "sender": "ai_agent",
                "message": (
                    f"AIP_SAK Agent online. Engagement initialized for {payload.target}. "
                    "Ready to execute autonomous assessment or receive operator instructions."
                ),
            }
        ],
    }
    state_file.write_text(json.dumps(initial_state, indent=2), encoding="utf-8")

    return {
        "status": "created",
        "engagement": payload.name,
        "target": payload.target,
    }


@router.post("/{name}/launch", dependencies=[Depends(verify_token)])
async def launch_engagement(name: str) -> dict[str, Any]:
    """Starts the autonomous penetration test engine for an engagement in background."""
    import asyncio

    from venice_pt.cli.run_cmd import run_engagement

    eng_dir = Path("engagements") / name
    if not eng_dir.exists():
        raise HTTPException(status_code=404, detail="Engagement not found")

    state_file = eng_dir / "state.json"
    target = "http://127.0.0.1:3000"
    risk_str = "safe"
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            target = data.get("target", target)
            risk_int = data.get("risk_level", 1)
            risk_map = {0: "passive", 1: "safe", 2: "intrusive", 3: "destructive"}
            risk_str = risk_map.get(risk_int, "safe")
            data["status"] = "running"
            state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    # Launch autonomous agent asynchronously in background task
    asyncio.create_task(
        run_engagement(
            target=target,
            engagement_name=name,
            risk=risk_str,
            budget=5.0,
        )
    )

    return {"status": "launched", "engagement": name, "target": target}


@router.get("/{name}", dependencies=[Depends(verify_token)])
def get_engagement(name: str) -> dict[str, Any]:
    eng_dir = Path("engagements") / name
    if not eng_dir.exists():
        raise HTTPException(status_code=404, detail="Engagement not found")

    state_file = eng_dir / "state.json"
    if not state_file.exists():
        return {"name": name, "state": "initialized"}

    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return dict(data)
        return {"name": name, "state": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read state: {e}")
