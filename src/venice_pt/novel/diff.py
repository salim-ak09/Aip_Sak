from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, Field


class ResponseBaseline(BaseModel):
    status_code: int
    content_length: int
    body_hash: str
    elapsed_seconds: float
    headers_keys: list[str] = Field(default_factory=list)


class ResponseDiff(BaseModel):
    status_changed: bool
    length_delta: int
    timing_delta: float
    hash_changed: bool
    anomaly_score: float
    reasons: list[str] = Field(default_factory=list)


def capture_baseline(
    status_code: int,
    body: str | bytes,
    elapsed_seconds: float,
    headers: dict[str, Any] | None = None,
) -> ResponseBaseline:
    """Captures a structured response baseline for an endpoint."""
    if isinstance(body, str):
        body_bytes = body.encode("utf-8", errors="replace")
    else:
        body_bytes = body

    b_hash = hashlib.sha256(body_bytes).hexdigest()
    hdr_keys = sorted(list(headers.keys())) if headers else []

    return ResponseBaseline(
        status_code=status_code,
        content_length=len(body_bytes),
        body_hash=b_hash,
        elapsed_seconds=elapsed_seconds,
        headers_keys=hdr_keys,
    )


def compute_diff(
    baseline: ResponseBaseline,
    status_code: int,
    body: str | bytes,
    elapsed_seconds: float,
) -> ResponseDiff:
    """Computes anomalous delta between candidate probe response and the baseline."""
    if isinstance(body, str):
        body_bytes = body.encode("utf-8", errors="replace")
    else:
        body_bytes = body

    b_hash = hashlib.sha256(body_bytes).hexdigest()
    curr_len = len(body_bytes)
    status_changed = status_code != baseline.status_code
    hash_changed = b_hash != baseline.body_hash
    len_delta = abs(curr_len - baseline.content_length)
    timing_delta = elapsed_seconds - baseline.elapsed_seconds

    score = 0.0
    reasons: list[str] = []

    if status_changed:
        score += 0.4
        reasons.append(f"Status changed from {baseline.status_code} to {status_code}")

    # Significant content difference
    if hash_changed and len_delta > 50:
        score += 0.3
        reasons.append(f"Content length delta of {len_delta} bytes")

    # Timing anomaly (>= 2.5 seconds differential)
    if timing_delta >= 2.5:
        score += 0.5
        reasons.append(f"Timing differential anomaly: +{timing_delta:.2f}s")

    return ResponseDiff(
        status_changed=status_changed,
        length_delta=len_delta,
        timing_delta=timing_delta,
        hash_changed=hash_changed,
        anomaly_score=min(round(score, 2), 1.0),
        reasons=reasons,
    )
