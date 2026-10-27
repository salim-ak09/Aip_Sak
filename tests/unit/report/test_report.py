from __future__ import annotations

from pathlib import Path

from venice_pt.report.render import render_html_report
from venice_pt.report.sarif import export_sarif
from venice_pt.report.scoring import CVSSCalculator, compute_risk_matrix


def test_cvss_calculation() -> None:
    # Standard vector: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H should be 9.8 (Critical)
    vector_critical = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    score = CVSSCalculator.calculate_base_score(vector_critical)
    assert score == 9.8
    assert CVSSCalculator.get_severity(score) == "Critical"

    # Low severity vector
    vector_low = "CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N"
    score_low = CVSSCalculator.calculate_base_score(vector_low)
    assert score_low < 4.0
    assert CVSSCalculator.get_severity(score_low) in ("Low", "None")


def test_risk_matrix() -> None:
    findings = [
        {"severity": "critical", "verified": True},
        {"severity": "high", "verified": False},
        {"severity": "medium", "verified": True},
    ]
    matrix = compute_risk_matrix(findings)
    assert matrix["total"] == 3
    assert matrix["verified"] == 2
    assert matrix["unverified"] == 1
    assert matrix["severity_counts"]["critical"] == 1
    assert matrix["severity_counts"]["high"] == 1


def test_sarif_export() -> None:
    findings = [
        {
            "id": "find-1",
            "cls": "sqli",
            "title": "SQL Injection in /api/users",
            "description": "Unsanitized user input in query parameter",
            "target": "http://127.0.0.1:3000/api/users",
            "severity": "critical",
            "confidence": 0.95,
            "verified": True,
            "cvss_v3": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        }
    ]
    sarif = export_sarif(findings)
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"]) == 1
    driver = sarif["runs"][0]["tool"]["driver"]
    assert driver["name"] == "venice-pt"
    assert len(driver["rules"]) == 1
    assert driver["rules"][0]["id"] == "sqli"

    results = sarif["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["level"] == "error"
    assert results[0]["properties"]["verified"] is True


def test_html_render(tmp_path: Path) -> None:
    findings = [
        {
            "id": "f-1",
            "cls": "xss",
            "title": "Reflected XSS",
            "description": "Reflected script payload in search parameter",
            "target": "http://127.0.0.1:3000/search",
            "severity": "medium",
            "confidence": 0.9,
            "verified": True,
            "cvss_score": 6.1,
            "evidence": ["<script>alert(1)</script> reflected in body"],
            "remediation": "Sanitize and HTML-encode user input",
        },
        {
            "id": "f-2",
            "cls": "info_leak",
            "title": "Swagger UI Docs",
            "description": "Swagger endpoint exposed",
            "target": "http://127.0.0.1:3000/api-docs",
            "severity": "info",
            "confidence": 0.36,
            "verified": False,
        },
    ]

    html = render_html_report(
        engagement_name="test-assessment",
        target="http://127.0.0.1:3000",
        findings=findings,
        duration_minutes=12,
    )

    assert "Autonomous Penetration Test Report" in html
    assert "test-assessment" in html
    assert "Reflected XSS" in html
    assert "Swagger UI Docs" in html
    assert "Appendix: Unconfirmed / Demoted Findings" in html

    out_file = tmp_path / "report.html"
    out_file.write_text(html, encoding="utf-8")
    assert out_file.stat().st_size > 500
