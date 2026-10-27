from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import typer

from venice_pt.report.render import render_html_report
from venice_pt.report.sarif import export_sarif
from venice_pt.report.scoring import CVSSCalculator

report_app = typer.Typer(name="report", help="Generate engagement reports (HTML, SARIF, CSV)")


def export_csv(findings: list[dict[str, Any]]) -> str:
    """Exports findings list to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "title", "class", "target", "severity", "confidence", "verified", "cvss_v3"]
    )
    for f in findings:
        writer.writerow(
            [
                f.get("id", ""),
                f.get("title", ""),
                f.get("cls", ""),
                f.get("target", ""),
                f.get("severity", ""),
                f.get("confidence", ""),
                f.get("verified", False),
                f.get("cvss_v3", ""),
            ]
        )
    return output.getvalue()


@report_app.callback(invoke_without_command=True)
def generate_report(
    engagement: str = typer.Option(..., "--engagement", "-e", help="Engagement slug or path"),
    output_dir: Path = typer.Option(
        Path("./reports"), "--output-dir", "-o", help="Output directory"
    ),
    formats: str = typer.Option("html,sarif,csv", "--format", "-f", help="Comma-separated formats"),
) -> None:
    """Compiles findings and writes reports in requested formats."""
    eng_dir = Path("engagements") / engagement
    if not eng_dir.exists() and Path(engagement).exists():
        eng_dir = Path(engagement)

    state_file = eng_dir / "state.json"
    target = "unknown"
    findings: list[dict[str, Any]] = []

    if state_file.exists():
        try:
            with open(state_file, encoding="utf-8") as fp:
                data = json.load(fp)
                target = data.get("target", target)
                findings = data.get("findings", [])
        except Exception as e:
            typer.echo(f"Warning: Failed to load state.json: {e}", err=True)

    # Compute CVSS score if missing and vector exists
    for f in findings:
        vec = f.get("cvss_v3")
        if vec and not f.get("cvss_score"):
            try:
                f["cvss_score"] = CVSSCalculator.calculate_base_score(vec)
            except Exception:
                pass

    output_dir.mkdir(parents=True, exist_ok=True)
    fmt_list = [fmt.strip().lower() for fmt in formats.split(",")]

    if "html" in fmt_list:
        html_out = render_html_report(engagement_name=engagement, target=target, findings=findings)
        html_path = output_dir / f"{engagement}_report.html"
        html_path.write_text(html_out, encoding="utf-8")
        typer.echo(f"[+] HTML Report generated: {html_path}")

    if "sarif" in fmt_list:
        sarif_data = export_sarif(findings)
        sarif_path = output_dir / f"{engagement}_findings.sarif"
        sarif_path.write_text(json.dumps(sarif_data, indent=2), encoding="utf-8")
        typer.echo(f"[+] SARIF Export generated: {sarif_path}")

    if "csv" in fmt_list:
        csv_out = export_csv(findings)
        csv_path = output_dir / f"{engagement}_findings.csv"
        csv_path.write_text(csv_out, encoding="utf-8")
        typer.echo(f"[+] CSV Export generated: {csv_path}")
