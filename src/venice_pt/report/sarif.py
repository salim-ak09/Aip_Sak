from __future__ import annotations

from typing import Any


def export_sarif(
    findings: list[dict[str, Any]],
    tool_name: str = "aip_Sak",
    version: str = "0.1.0",
) -> dict[str, Any]:
    """Generates an OASIS SARIF v2.1.0 compliant dictionary for findings."""
    rules = []
    results = []
    seen_rule_ids = set()

    for idx, f in enumerate(findings):
        rule_id = str(f.get("cls", f"RULE-{idx}"))
        rule_name = str(f.get("title", rule_id))
        severity = str(f.get("severity", "medium")).lower()

        sarif_level = "warning"
        if severity in ("critical", "high"):
            sarif_level = "error"
        elif severity == "low":
            sarif_level = "note"
        elif severity == "info":
            sarif_level = "none"

        if rule_id not in seen_rule_ids:
            seen_rule_ids.add(rule_id)
            rules.append(
                {
                    "id": rule_id,
                    "name": rule_name,
                    "shortDescription": {"text": rule_name},
                    "fullDescription": {"text": str(f.get("description", rule_name))},
                    "defaultConfiguration": {"level": sarif_level},
                }
            )

        target = str(f.get("target", "target"))
        results.append(
            {
                "ruleId": rule_id,
                "level": sarif_level,
                "message": {
                    "text": (
                        f"{rule_name} identified at {target}. "
                        f"Verified: {f.get('verified', False)}"
                    )
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": target,
                            }
                        }
                    }
                ],
                "properties": {
                    "confidence": f.get("confidence", 1.0),
                    "verified": f.get("verified", False),
                    "cvss_v3": f.get("cvss_v3", ""),
                },
            }
        )

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": tool_name,
                        "version": version,
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }
