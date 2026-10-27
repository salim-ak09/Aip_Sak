from __future__ import annotations

import asyncio
import shutil
import time
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from venice_pt.config import config
from venice_pt.contracts.events import Event, EventKind, Phase, Risk
from venice_pt.contracts.facts import Fact
from venice_pt.contracts.tools import ToolSpec
from venice_pt.exec.flags import FlagSchemaManager
from venice_pt.exec.ratelimit import RateLimiter
from venice_pt.exec.sandbox import prepare_sanitized_env
from venice_pt.exec.scope import ScopeDefinition, ScopeViolation
from venice_pt.logging import logger
from venice_pt.store.bus import EventBus
from venice_pt.store.eventlog import EventLog


class ToolResult(BaseModel):
    event_id: str
    tool: str
    argv: list[str]
    exit_code: int
    duration_s: float
    stdout_path: Path
    stderr_path: Path
    parsed: BaseModel | None = None
    facts: list[Fact] = Field(default_factory=list)
    error: str | None = None


class Runner(Protocol):
    async def execute(
        self,
        spec: ToolSpec,
        args: list[str],
        *,
        engagement_id: str,
        phase: Phase,
        stdin: bytes | None = None,
    ) -> ToolResult: ...


class SubprocessRunner:
    def __init__(
        self,
        event_log: EventLog | None = None,
        event_bus: EventBus | None = None,
        scope: ScopeDefinition | None = None,
        rate_limiter: RateLimiter | None = None,
        flag_manager: FlagSchemaManager | None = None,
        risk_ceiling: Risk = Risk.SAFE,
        use_docker: bool = False,
    ) -> None:
        self.event_log = event_log
        self.event_bus = event_bus
        self.scope = scope or ScopeDefinition()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.flag_manager = flag_manager or FlagSchemaManager()
        self.risk_ceiling = risk_ceiling
        self.use_docker = use_docker

    async def _emit(self, event: Event) -> None:
        if self.event_log:
            self.event_log.append(event)
        if self.event_bus:
            await self.event_bus.publish(event)

    async def execute(
        self,
        spec: ToolSpec,
        args: list[str],
        *,
        engagement_id: str,
        phase: Phase,
        stdin: bytes | None = None,
        target: str | None = None,
        force: bool = False,
    ) -> ToolResult:
        # 1. Risk gate check
        if spec.risk > self.risk_ceiling and not force:
            err_msg = (
                f"Tool '{spec.name}' has risk {spec.risk.name} which exceeds "
                f"engagement ceiling {self.risk_ceiling.name}. Refusing to run unless forced."
            )
            err_event = Event(
                engagement_id=engagement_id,
                phase=phase,
                actor="runner",
                kind=EventKind.ERROR,
                tool=spec.name,
                payload={"error": err_msg},
            )
            await self._emit(err_event)
            raise PermissionError(err_msg)

        # 2. Scope validation check
        if target:
            try:
                self.scope.validate_target(target)
            except ScopeViolation as e:
                err_event = Event(
                    engagement_id=engagement_id,
                    phase=phase,
                    actor="runner",
                    kind=EventKind.ERROR,
                    tool=spec.name,
                    payload={"error": str(e), "target": target},
                )
                await self._emit(err_event)
                dummy_path = Path("/dev/null")
                return ToolResult(
                    event_id=err_event.id,
                    tool=spec.name,
                    argv=args,
                    exit_code=1,
                    duration_s=0.0,
                    stdout_path=dummy_path,
                    stderr_path=dummy_path,
                    parsed=None,
                    facts=[],
                    error=str(e),
                )

        # 3. Rate limiting
        if target:
            host = self.scope.extract_host(target)
            await self.rate_limiter.acquire(host)

        # 4. Flag validation
        clean_args = self.flag_manager.validate_args(spec, args)

        # Artifacts directory setup
        artifacts_dir = config.engagements_dir / engagement_id / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        cmd_event = Event(
            engagement_id=engagement_id,
            phase=phase,
            actor="runner",
            kind=EventKind.CMD,
            tool=spec.name,
            cmd=f"{spec.binary} {' '.join(clean_args)}",
            payload={"args": clean_args, "target": target},
        )
        await self._emit(cmd_event)

        stdout_file = artifacts_dir / f"{cmd_event.id}.out"
        stderr_file = artifacts_dir / f"{cmd_event.id}.err"

        # Determine binary or docker execution
        binary_path = shutil.which(spec.binary)
        if not binary_path and not self.use_docker:
            # Fallback to binary name directly if in path
            binary_path = spec.binary

        full_cmd: list[str] = []
        if self.use_docker:
            image = "instrumentisto/nmap:latest"
            for step in spec.install:
                if step.method == "docker" and step.image:
                    image = step.image
                    break
            full_cmd = ["docker", "run", "--rm", "--network=host", image] + clean_args
        else:
            full_cmd = [binary_path or spec.binary] + clean_args

        t0 = time.perf_counter()
        exit_code = -1
        error_msg: str | None = None

        env = prepare_sanitized_env()

        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdin=asyncio.subprocess.PIPE if stdin else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdout_data, stderr_data = await asyncio.wait_for(
                proc.communicate(input=stdin),
                timeout=spec.timeout_s,
            )
            exit_code = proc.returncode or 0

            stdout_file.write_bytes(stdout_data)
            stderr_file.write_bytes(stderr_data)

            if stdout_data:
                await self._emit(
                    Event(
                        engagement_id=engagement_id,
                        phase=phase,
                        actor="runner",
                        kind=EventKind.STDOUT,
                        tool=spec.name,
                        parent_id=cmd_event.id,
                        payload={"path": str(stdout_file), "size": len(stdout_data)},
                    )
                )

            if stderr_data:
                await self._emit(
                    Event(
                        engagement_id=engagement_id,
                        phase=phase,
                        actor="runner",
                        kind=EventKind.STDERR,
                        tool=spec.name,
                        parent_id=cmd_event.id,
                        payload={"path": str(stderr_file), "size": len(stderr_data)},
                    )
                )

        except TimeoutError:
            proc.kill()
            await proc.wait()
            error_msg = f"Execution of {spec.name} timed out after {spec.timeout_s}s"
            logger.error("Tool execution timed out", tool=spec.name, timeout_s=spec.timeout_s)
            exit_code = 124
            stdout_file.write_text("")
            stderr_file.write_text(error_msg)
            await self._emit(
                Event(
                    engagement_id=engagement_id,
                    phase=phase,
                    actor="runner",
                    kind=EventKind.ERROR,
                    tool=spec.name,
                    parent_id=cmd_event.id,
                    payload={"error": error_msg},
                )
            )

        except Exception as e:
            error_msg = str(e)
            exit_code = 1
            stdout_file.write_text("")
            stderr_file.write_text(error_msg)
            await self._emit(
                Event(
                    engagement_id=engagement_id,
                    phase=phase,
                    actor="runner",
                    kind=EventKind.ERROR,
                    tool=spec.name,
                    parent_id=cmd_event.id,
                    payload={"error": error_msg},
                )
            )

        duration = time.perf_counter() - t0

        return ToolResult(
            event_id=cmd_event.id,
            tool=spec.name,
            argv=clean_args,
            exit_code=exit_code,
            duration_s=round(duration, 3),
            stdout_path=stdout_file,
            stderr_path=stderr_file,
            parsed=None,
            facts=[],
            error=error_msg,
        )
