from __future__ import annotations

import os


def prepare_sanitized_env() -> dict[str, str]:
    """Prepares an isolated, scrubbed environment for tool execution."""
    safe_keys = {
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "SHELL",
        "LANG",
        "LC_ALL",
        "TMPDIR",
        "TEMP",
        "TMP",
        "SYSTEMROOT",
        "COMSPEC",
        "WINDIR",
        "PATHEXT",
    }
    return {k: v for k, v in os.environ.items() if k.upper() in safe_keys}
