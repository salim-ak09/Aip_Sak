from __future__ import annotations

import platform
import shutil
from typing import Literal

PackageManager = Literal["apt", "dnf", "pacman", "brew", "unknown"]


def detect_package_manager() -> PackageManager:
    """Detects available system package manager."""
    if shutil.which("apt-get") or shutil.which("apt"):
        return "apt"
    if shutil.which("dnf"):
        return "dnf"
    if shutil.which("pacman"):
        return "pacman"
    if shutil.which("brew"):
        return "brew"
    return "unknown"


def detect_system_info() -> dict[str, str]:
    return {
        "os": platform.system().lower(),
        "arch": platform.machine().lower(),
        "package_manager": detect_package_manager(),
    }
