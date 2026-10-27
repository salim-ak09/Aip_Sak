from __future__ import annotations

from pydantic import BaseModel


class CVEMatch(BaseModel):
    cve_id: str
    product: str
    version_range: str
    severity: str
    description: str


class CVEMatcher:
    """Matches identified software components and versions against known CVE advisories."""

    # Local embedded database of common advisories
    ADVISORY_DB = [
        {
            "cve_id": "CVE-2021-41773",
            "product": "apache",
            "versions": ["2.4.49"],
            "severity": "critical",
            "description": "Path traversal and remote code execution in Apache HTTP Server 2.4.49.",
        },
        {
            "cve_id": "CVE-2021-42013",
            "product": "apache",
            "versions": ["2.4.50"],
            "severity": "critical",
            "description": "Incomplete fix for CVE-2021-41773 in Apache HTTP Server 2.4.50.",
        },
        {
            "cve_id": "CVE-2018-13379",
            "product": "fortios",
            "versions": ["5.6.7", "6.0.4"],
            "severity": "critical",
            "description": "Path traversal in Fortinet FortiOS SSL VPN portal.",
        },
        {
            "cve_id": "CVE-2023-38606",
            "product": "openssh",
            "versions": ["9.3p1"],
            "severity": "high",
            "description": "OpenSSH PKCS#11 provider memory corruption vulnerability.",
        },
    ]

    @classmethod
    def match(cls, product_name: str, version: str) -> list[CVEMatch]:
        matches: list[CVEMatch] = []
        p_name = product_name.lower().strip()
        v_str = version.strip()

        for adv in cls.ADVISORY_DB:
            adv_product = str(adv["product"])
            if adv_product in p_name:
                versions = [str(x) for x in adv.get("versions", [])]
                if any(v in v_str for v in versions):
                    matches.append(
                        CVEMatch(
                            cve_id=str(adv["cve_id"]),
                            product=str(adv["product"]),
                            version_range=",".join(versions),
                            severity=str(adv["severity"]),
                            description=str(adv["description"]),
                        )
                    )
        return matches
