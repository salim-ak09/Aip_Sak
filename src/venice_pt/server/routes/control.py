from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from venice_pt.server.auth import verify_token
from venice_pt.server.ws import manager

router = APIRouter(prefix="/api/control", tags=["control"])


class ControlCommand(BaseModel):
    action: str = Field(..., description="Action: pause, resume, abort, approve, reject")
    engagement: str = Field(..., description="Engagement name")
    details: dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")


@router.post("", dependencies=[Depends(verify_token)])
async def execute_control(cmd: ControlCommand) -> dict[str, Any]:
    eng_dir = Path("engagements") / cmd.engagement
    if not eng_dir.exists():
        raise HTTPException(status_code=404, detail="Engagement not found")

    state_file = eng_dir / "state.json"
    state: dict[str, Any] = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    action = cmd.action.lower()
    if action == "pause":
        state["status"] = "paused"
    elif action == "resume":
        state["status"] = "running"
    elif action == "abort":
        state["status"] = "aborted"
    elif action == "chat":
        # Human agent communication: inject order/question into operator instructions queue
        message = str(cmd.details.get("message", "")).strip()
        if message:
            queue = state.setdefault("operator_instructions", [])
            queue.append(message)
            chat_history = state.setdefault("chat_history", [])
            chat_history.append({"sender": "operator", "message": message})

            # Autonomous agent acknowledged order/inquiry
            curr_phase = state.get("phase", "recon")
            agent_reply = (
                f"Order received and incorporated into planner objectives: '{message}'. "
                f"Currently optimizing attack path in phase [{curr_phase.upper()}]."
            )
            chat_history.append({"sender": "ai_agent", "message": agent_reply})
            cmd.details["agent_reply"] = agent_reply
    elif action in ("approve", "reject"):
        approvals = state.setdefault("approvals", {})
        target_item = cmd.details.get("item_id", "default")
        approvals[target_item] = (action == "approve")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported control action: {cmd.action}")

    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # Broadcast control event to connected WebSocket clients
    control_event = {
        "type": "control_action",
        "action": action,
        "engagement": cmd.engagement,
        "details": cmd.details,
    }
    await manager.record_and_broadcast(control_event)

    return {
        "status": "ok",
        "action": action,
        "engagement": cmd.engagement,
        "details": cmd.details,
    }
