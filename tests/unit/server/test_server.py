from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from venice_pt.server.app import app

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer venice-secret-token"}


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_guard() -> None:
    os.environ["VENICE_AUTH_DISABLED"] = "false"
    # Unauthenticated request should be 401
    res_no_auth = client.get("/api/engagements")
    assert res_no_auth.status_code == 401

    # Bad token should be 403
    res_bad_auth = client.get("/api/engagements", headers={"Authorization": "Bearer invalid"})
    assert res_bad_auth.status_code == 403


def test_engagements_crud(tmp_path: Path) -> None:
    eng_name = f"api-test-engagement-{uuid.uuid4().hex[:8]}"
    # Create engagement
    payload = {
        "name": eng_name,
        "target": "http://127.0.0.1:8080",
        "profile": "fast",
        "risk_level": 1,
    }
    create_res = client.post("/api/engagements", json=payload, headers=AUTH_HEADERS)
    assert create_res.status_code == 201
    assert create_res.json()["engagement"] == eng_name

    # Get engagement
    get_res = client.get(f"/api/engagements/{eng_name}", headers=AUTH_HEADERS)
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["target"] == "http://127.0.0.1:8080"
    assert data["risk_level"] == 1


def test_control_pause_resume() -> None:
    cmd_pause = {
        "action": "pause",
        "engagement": "api-test-engagement",
        "details": {"reason": "operator review"},
    }
    res_pause = client.post("/api/control", json=cmd_pause, headers=AUTH_HEADERS)
    assert res_pause.status_code == 200
    assert res_pause.json()["action"] == "pause"

    eng_res = client.get("/api/engagements/api-test-engagement", headers=AUTH_HEADERS)
    assert eng_res.json()["status"] == "paused"

    cmd_resume = {
        "action": "resume",
        "engagement": "api-test-engagement",
    }
    res_resume = client.post("/api/control", json=cmd_resume, headers=AUTH_HEADERS)
    assert res_resume.status_code == 200
    assert res_resume.json()["action"] == "resume"

    eng_res = client.get("/api/engagements/api-test-engagement", headers=AUTH_HEADERS)
    assert eng_res.json()["status"] == "running"


def test_websocket_stream_and_resume() -> None:
    with client.websocket_connect("/ws") as ws:
        ws.send_text("ping")
        resp = ws.receive_text()
        assert resp == "pong"
