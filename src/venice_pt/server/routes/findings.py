from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from venice_pt.server.auth import verify_token

router = APIRouter(prefix="/api/findings", tags=["findings"])


@router.get("", dependencies=[Depends(verify_token)])
def list_findings(engagement: str | None = None) -> list[dict[str, Any]]:
    """List findings, optionally filtered by engagement name."""
    engagements_dir = Path("engagements")
    if not engagements_dir.exists():
        return []

    targets = [engagements_dir / engagement] if engagement else list(engagements_dir.iterdir())
    all_findings: list[dict[str, Any]] = []

    for d in targets:
        if d.is_dir():
            state_file = d / "state.json"
            if state_file.exists():
                try:
                    data = json.loads(state_file.read_text(encoding="utf-8"))
                    findings = data.get("findings", [])
                    for f in findings:
                        f["engagement"] = d.name
                        all_findings.append(f)
                except Exception:
                    pass

    return all_findings


@router.get("/{finding_id}", dependencies=[Depends(verify_token)])
def get_finding(finding_id: str) -> dict[str, Any]:
    """Finds a specific finding by ID across engagements."""
    engagements_dir = Path("engagements")
    if not engagements_dir.exists():
        raise HTTPException(status_code=404, detail="Finding not found")

    for d in engagements_dir.iterdir():
        if d.is_dir():
            state_file = d / "state.json"
            if state_file.exists():
                try:
                    data = json.loads(state_file.read_text(encoding="utf-8"))
                    findings = data.get("findings", [])
                    for f in findings:
                        if isinstance(f, dict) and str(f.get("id")) == str(finding_id):
                            res = dict(f)
                            res["engagement"] = d.name
                            return res
                except Exception:
                    pass

    raise HTTPException(status_code=404, detail="Finding not found")
