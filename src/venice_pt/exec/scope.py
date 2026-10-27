from __future__ import annotations

import ipaddress
from pathlib import Path
from urllib.parse import urlparse

import yaml


class ScopeViolation(Exception):
    pass


class ScopeDefinition:
    def __init__(
        self,
        included_cidrs: list[ipaddress.IPv4Network | ipaddress.IPv6Network] | None = None,
        included_domains: list[str] | None = None,
        excluded_cidrs: list[ipaddress.IPv4Network | ipaddress.IPv6Network] | None = None,
        excluded_domains: list[str] | None = None,
    ) -> None:
        self.included_cidrs = included_cidrs or []
        self.included_domains = [d.lower() for d in (included_domains or [])]
        self.excluded_cidrs = excluded_cidrs or []
        self.excluded_domains = [d.lower() for d in (excluded_domains or [])]

    @classmethod
    def from_yaml(cls, content_or_path: str | Path) -> ScopeDefinition:
        if isinstance(content_or_path, Path):
            text = content_or_path.read_text(encoding="utf-8")
        elif "\n" in content_or_path or ":" in content_or_path:
            text = content_or_path
        else:
            p = Path(content_or_path)
            text = p.read_text(encoding="utf-8") if p.exists() else content_or_path

        data = yaml.safe_load(text) or {}
        inc = data.get("include", {})
        exc = data.get("exclude", {})

        inc_cidrs: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for item in inc.get("cidrs", []):
            inc_cidrs.append(ipaddress.ip_network(item, strict=False))

        exc_cidrs: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for item in exc.get("cidrs", []):
            exc_cidrs.append(ipaddress.ip_network(item, strict=False))

        return cls(
            included_cidrs=inc_cidrs,
            included_domains=inc.get("domains", []),
            excluded_cidrs=exc_cidrs,
            excluded_domains=exc.get("domains", []),
        )

    def extract_host(self, target: str) -> str:
        t = target.strip()
        if "://" in t:
            parsed = urlparse(t)
            host = parsed.hostname or ""
            return host.lower()
        if ":" in t and not t.endswith(":"):
            # Could be host:port or IPv6
            parts = t.split(":")
            if len(parts) == 2 and parts[1].isdigit():
                return parts[0].lower()
        return t.lower()

    def is_in_scope(self, target: str) -> bool:
        host = self.extract_host(target)
        if not host:
            return False

        # Check if IP
        try:
            ip = ipaddress.ip_address(host)
            # Check exclusions first
            for exc in self.excluded_cidrs:
                if ip in exc:
                    return False
            # Check inclusions
            for inc in self.included_cidrs:
                if ip in inc:
                    return True
            # Special case: allow loopback when no inclusions are specified
            if ip.is_loopback and not self.included_cidrs and not self.included_domains:
                return True
            return False
        except ValueError:
            pass

        # Check domain matches
        # Exclusions first
        for exc_d in self.excluded_domains:
            if self._domain_matches(host, exc_d):
                return False

        # Inclusions
        if not self.included_domains and not self.included_cidrs:
            # If no inclusions are specified, loopback/localhost is permitted
            return host in ("localhost", "127.0.0.1")

        for inc_d in self.included_domains:
            if self._domain_matches(host, inc_d):
                return True

        return False

    def validate_target(self, target: str) -> None:
        if not self.is_in_scope(target):
            raise ScopeViolation(f"Target '{target}' is out of engagement scope.")

    @staticmethod
    def _domain_matches(host: str, pattern: str) -> bool:
        pattern = pattern.lower()
        if pattern.startswith("*."):
            base = pattern[2:]
            return host == base or host.endswith(f".{base}")
        return host == pattern
