from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from venice_pt.config import config
from venice_pt.contracts.tools import ToolSpec
from venice_pt.logging import logger


class FlagSchemaManager:
    def __init__(self, flags_dir: Path | None = None) -> None:
        self.flags_dir = flags_dir or (config.home_dir / "flags")
        self.flags_dir.mkdir(parents=True, exist_ok=True)

    def get_flag_schema(self, tool_name: str) -> set[str] | None:
        cache_file = self.flags_dir / f"{tool_name}.json"
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return set(data.get("flags", []))
        except Exception:
            return None

    def cache_flag_schema(self, tool_name: str, flags: set[str]) -> None:
        cache_file = self.flags_dir / f"{tool_name}.json"
        data = {"tool": tool_name, "flags": sorted(flags)}
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def extract_flags_from_help(self, help_text: str) -> set[str]:
        """Extracts flag patterns like -sV, --script, -p from help text."""
        flags: set[str] = set()
        # Regex matching -a, --long-flag, -sV, etc.
        pattern = re.compile(r"(?<!\w)(-[a-zA-Z0-9_\-]+|--[a-zA-Z0-9_\-]+)")
        for line in help_text.splitlines():
            # Only look in lines that appear to document flags (leading spaces followed by dash)
            if re.match(r"^\s*-[a-zA-Z0-9\-]", line):
                matches = pattern.findall(line)
                for m in matches:
                    flags.add(m)
        return flags

    def ensure_flags(self, spec: ToolSpec) -> set[str]:
        cached = self.get_flag_schema(spec.name)
        if cached is not None:
            return cached

        # Execute --help / -h
        help_flag = "-h" if "-h" in spec.check else "--help"
        try:
            res = subprocess.run(
                [spec.binary, help_flag],
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = res.stdout or res.stderr or ""
            flags = self.extract_flags_from_help(out)
            if not flags:
                # Fallback common flags if help parsing returned empty
                flags = {"-h", "--help", "-v", "--version"}
            self.cache_flag_schema(spec.name, flags)
            return flags
        except Exception as e:
            logger.warning("Failed to extract flags from tool --help", tool=spec.name, error=str(e))
            fallback = {"-h", "--help", "-v", "--version"}
            self.cache_flag_schema(spec.name, fallback)
            return fallback

    def validate_args(self, spec: ToolSpec, args: list[str]) -> list[str]:
        """Validates args against flag schema, dropping unknown flags with a warning."""
        valid_flags = self.ensure_flags(spec)
        cleaned_args: list[str] = []

        skip_next = False
        for i, arg in enumerate(args):
            if skip_next:
                skip_next = False
                cleaned_args.append(arg)
                continue

            if arg.startswith("-"):
                flag_name = arg.split("=")[0]
                if flag_name in valid_flags:
                    cleaned_args.append(arg)
                else:
                    logger.warning("Dropping unknown flag", tool=spec.name, flag=arg)
            else:
                cleaned_args.append(arg)

        return cleaned_args
