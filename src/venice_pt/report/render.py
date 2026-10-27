from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jinja2

from venice_pt.report.scoring import compute_risk_matrix

TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_html_report(
    engagement_name: str,
    target: str,
    findings: list[dict[str, Any]],
    duration_minutes: int = 0,
) -> str:
    """Renders HTML report using Jinja2 template and computes risk metrics."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html.jinja")

    risk_matrix = compute_risk_matrix(findings)
    verified = [f for f in findings if f.get("verified", False)]
    unverified = [f for f in findings if not f.get("verified", False)]

    return template.render(
        engagement_name=engagement_name,
        target=target,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        duration_minutes=duration_minutes,
        risk_matrix=risk_matrix,
        verified_findings=verified,
        unverified_findings=unverified,
    )
