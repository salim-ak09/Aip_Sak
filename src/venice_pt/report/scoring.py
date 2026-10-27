from __future__ import annotations

import math
from typing import Any


class CVSSCalculator:
    """Computes CVSS v3.1 base score from metric vector components."""

    AV_MAP = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20}
    AC_MAP = {"L": 0.77, "H": 0.44}
    PR_MAP_UNCHANGED = {"N": 0.85, "L": 0.62, "H": 0.27}
    PR_MAP_CHANGED = {"N": 0.85, "L": 0.68, "H": 0.50}
    UI_MAP = {"N": 0.85, "R": 0.62}
    IMPACT_MAP = {"N": 0.0, "L": 0.22, "H": 0.56}

    @classmethod
    def calculate_base_score(cls, vector: str) -> float:
        """Parses CVSS:3.1 vector string (e.g. CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)
        and computes the base score.
        """
        parts = vector.strip().split("/")
        metrics: dict[str, str] = {}
        for part in parts:
            if ":" in part:
                k, v = part.split(":", 1)
                metrics[k.upper()] = v.upper()

        s = metrics.get("S", "U")
        av = cls.AV_MAP.get(metrics.get("AV", "N"), 0.85)
        ac = cls.AC_MAP.get(metrics.get("AC", "L"), 0.77)
        if s == "C":
            pr = cls.PR_MAP_CHANGED.get(metrics.get("PR", "N"), 0.85)
        else:
            pr = cls.PR_MAP_UNCHANGED.get(metrics.get("PR", "N"), 0.85)
        ui = cls.UI_MAP.get(metrics.get("UI", "N"), 0.85)

        c = cls.IMPACT_MAP.get(metrics.get("C", "N"), 0.0)
        i = cls.IMPACT_MAP.get(metrics.get("I", "N"), 0.0)
        a = cls.IMPACT_MAP.get(metrics.get("A", "N"), 0.0)

        # ISS = 1 - [ (1 - ImpactConf) * (1 - ImpactInteg) * (1 - ImpactAvail) ]
        iss = 1.0 - ((1.0 - c) * (1.0 - i) * (1.0 - a))
        if iss <= 0:
            return 0.0

        if s == "U":
            impact = 6.42 * iss
        else:
            impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)

        exploitability = 8.22 * av * ac * pr * ui

        if impact <= 0:
            return 0.0

        if s == "U":
            raw_score = min(impact + exploitability, 10.0)
        else:
            raw_score = min(1.08 * (impact + exploitability), 10.0)

        # Round up to one decimal place (CVSS v3.1 round up rule)
        return math.ceil(raw_score * 10.0) / 10.0

    @classmethod
    def get_severity(cls, score: float) -> str:
        if score == 0.0:
            return "None"
        elif score < 4.0:
            return "Low"
        elif score < 7.0:
            return "Medium"
        elif score < 9.0:
            return "High"
        else:
            return "Critical"


def compute_risk_matrix(findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Generates counts and distribution matrix by severity and status."""
    matrix: dict[str, int] = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
    }
    verified_count = 0
    total = len(findings)

    for f in findings:
        sev = str(f.get("severity", "info")).lower()
        if sev in matrix:
            matrix[sev] += 1
        if f.get("verified", False):
            verified_count += 1

    return {
        "total": total,
        "verified": verified_count,
        "unverified": total - verified_count,
        "severity_counts": matrix,
    }
