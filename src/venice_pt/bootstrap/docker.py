from __future__ import annotations

import shutil
import subprocess

from venice_pt.logging import logger


def is_docker_available() -> bool:
    return shutil.which("docker") is not None


def run_in_docker(
    image: str,
    args: list[str],
    network: str = "host",
    timeout_s: int = 300,
) -> tuple[int, str, str]:
    """Runs a tool inside a disposable Docker container."""
    cmd = ["docker", "run", "--rm", f"--network={network}", image] + args
    logger.info("Executing via Docker fallback", image=image, cmd=" ".join(cmd))
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return res.returncode, res.stdout, res.stderr
