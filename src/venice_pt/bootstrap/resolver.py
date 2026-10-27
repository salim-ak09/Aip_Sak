from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from venice_pt.bootstrap.distro import detect_package_manager
from venice_pt.bootstrap.docker import is_docker_available
from venice_pt.bootstrap.lockfile import ToolchainLock
from venice_pt.config import config
from venice_pt.contracts.tools import ToolSpec
from venice_pt.logging import logger


class ToolResolutionError(Exception):
    pass


class Resolver:
    def __init__(
        self,
        toolchain_bin: Path | None = None,
        lockfile_path: Path | None = None,
    ) -> None:
        self.toolchain_bin = toolchain_bin or (config.toolchain_dir / "bin")
        self.toolchain_bin.mkdir(parents=True, exist_ok=True)
        self.lockfile_path = lockfile_path or (config.home_dir / "toolchain.lock")
        self.lockfile = ToolchainLock.load(self.lockfile_path)

        # Prepend toolchain_bin to PATH
        bin_str = str(self.toolchain_bin)
        if bin_str not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{bin_str}{os.pathsep}{os.environ.get('PATH', '')}"

    def is_installed(self, spec: ToolSpec) -> bool:
        """Checks if tool binary exists on PATH or was locked via Docker."""
        if shutil.which(spec.binary):
            return True
        entry = self.lockfile.tools.get(spec.name)
        if entry and entry.method == "docker" and is_docker_available():
            return True
        return False

    def get_tool_version(self, spec: ToolSpec) -> str | None:
        if not self.is_installed(spec):
            return None
        try:
            res = subprocess.run(
                [spec.binary] + spec.check.split(),
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = (res.stdout or res.stderr).strip()
            first_line = out.splitlines()[0] if out else "installed"
            return first_line
        except Exception:
            return "unknown"

    def ensure(self, spec: ToolSpec) -> str:
        """Walks install fallback chain to ensure tool is present."""
        if self.is_installed(spec):
            return "already_installed"

        pkg_mgr = detect_package_manager()
        docker_ok = is_docker_available()

        for step in spec.install:
            method = step.method
            if method in ("apt", "dnf", "pacman", "brew") and method == pkg_mgr:
                if self._install_via_pkg_mgr(method, step.pkg):
                    self.lockfile.record(tool=spec.name, method=method, version=spec.version_pin)
                    self.lockfile.save(self.lockfile_path)
                    return f"installed_via_{method}"

            elif method == "go" and shutil.which("go") and step.pkg:
                if self._install_via_go(step.pkg):
                    self.lockfile.record(tool=spec.name, method="go", version=spec.version_pin)
                    self.lockfile.save(self.lockfile_path)
                    return "installed_via_go"

            elif method == "docker" and docker_ok and step.image:
                if self._pull_docker_image(step.image):
                    self.lockfile.record(
                        tool=spec.name, method="docker", version=spec.version_pin, path=step.image
                    )
                    self.lockfile.save(self.lockfile_path)
                    return "installed_via_docker"

        raise ToolResolutionError(
            f"Failed to install tool {spec.name}. None of the install methods succeeded."
        )

    def _install_via_pkg_mgr(self, mgr: str, pkg: str | None) -> bool:
        if not pkg:
            return False
        cmd: list[str] = []
        if mgr == "apt":
            cmd = ["sudo", "apt-get", "update", "-y"]
            subprocess.run(cmd, capture_output=True)
            cmd = ["sudo", "apt-get", "install", "-y", pkg]
        elif mgr == "dnf":
            cmd = ["sudo", "dnf", "install", "-y", pkg]
        elif mgr == "pacman":
            cmd = ["sudo", "pacman", "-S", "--noconfirm", pkg]
        elif mgr == "brew":
            cmd = ["brew", "install", pkg]

        logger.info("Executing package manager install", cmd=" ".join(cmd))
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0

    def _install_via_go(self, pkg: str) -> bool:
        env = os.environ.copy()
        env["GOBIN"] = str(self.toolchain_bin)
        cmd = ["go", "install", pkg]
        logger.info("Executing go install", cmd=" ".join(cmd), gobin=str(self.toolchain_bin))
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        return res.returncode == 0

    def _pull_docker_image(self, image: str) -> bool:
        cmd = ["docker", "pull", image]
        logger.info("Pulling docker fallback image", image=image)
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0
