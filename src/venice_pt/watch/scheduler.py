from __future__ import annotations

import asyncio
from typing import Any

import structlog

from venice_pt.watch.alerts import global_alert_dispatcher
from venice_pt.watch.cve_match import CVEMatcher
from venice_pt.watch.drift import DriftDelta, SurfaceDriftDetector

logger = structlog.get_logger()


class WatchScheduler:
    """Manages periodic attack surface monitoring cycles and delta alerting."""

    def __init__(self, interval_seconds: float = 3600.0) -> None:
        self.interval_seconds = interval_seconds
        self.running = False
        self._last_snapshot: dict[str, Any] = {"assets": [], "ports": []}

    async def execute_cycle(self, current_snapshot: dict[str, Any]) -> DriftDelta:
        """Runs a single monitoring cycle, detecting drift and CVE matches."""
        logger.info("watch_cycle_started")
        drift = SurfaceDriftDetector.detect_drift(self._last_snapshot, current_snapshot)

        if drift.has_drift:
            logger.info(
                "surface_drift_detected",
                new_assets=len(drift.new_assets),
                new_ports=len(drift.new_ports),
            )
            # Dispatch alert
            alert_key = f"drift_{','.join(drift.new_assets)}_{len(drift.new_ports)}"
            await global_alert_dispatcher.dispatch(
                title="Surface Drift Detected",
                message=(
                    f"Discovered {len(drift.new_assets)} new assets "
                    f"and {len(drift.new_ports)} new ports"
                ),
                alert_key=alert_key,
            )

        # Check CVE matches on ports/services
        for port_info in current_snapshot.get("ports", []):
            product = port_info.get("product", "")
            version = port_info.get("version", "")
            if product and version:
                matches = CVEMatcher.match(product, version)
                for m in matches:
                    cve_key = f"cve_{m.cve_id}_{port_info.get('host')}"
                    await global_alert_dispatcher.dispatch(
                        title=f"New Vulnerability: {m.cve_id}",
                        message=(
                            f"{m.product} {version} on {port_info.get('host')}: "
                            f"{m.description}"
                        ),
                        alert_key=cve_key,
                    )

        # Update snapshot
        self._last_snapshot = current_snapshot
        logger.info("watch_cycle_completed")
        return drift

    async def start(self) -> None:
        self.running = True
        while self.running:
            # Periodic loop
            await asyncio.sleep(self.interval_seconds)

    def stop(self) -> None:
        self.running = False
