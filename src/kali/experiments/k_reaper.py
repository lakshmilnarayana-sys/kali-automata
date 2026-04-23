"""K-Reaper — pod and service termination faults."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict

from kali.experiments.base import FaultInjector
from kali.models.experiment import ActionResult


class KReaperProcessKillInjector(FaultInjector):
    """K-Reaper: kills a process by name or PID to test restart/recovery behaviour."""

    name = "process/kill"

    async def inject(self, provider: Dict[str, Any], duration: int, dry_run: bool = False) -> ActionResult:
        process_name = provider.get("process")
        pid = provider.get("pid")
        signal = provider.get("signal", "SIGTERM")

        if pid:
            cmd = f"kill -{signal} {pid}"
            target = f"PID {pid}"
        elif process_name:
            cmd = f"pkill -{signal} {process_name}"
            target = process_name
        else:
            return ActionResult(
                action_name=self.name,
                success=False,
                error="Provider must specify 'process' or 'pid'",
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow(),
            )

        started = datetime.utcnow()
        if not dry_run:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode not in (0, 1):
                return ActionResult(
                    action_name=self.name,
                    success=False,
                    error=stderr.decode(),
                    started_at=started,
                    ended_at=datetime.utcnow(),
                )
        return ActionResult(
            action_name=self.name,
            success=True,
            output=f"[dry-run] {cmd}" if dry_run else f"K-Reaper: sent {signal} to {target}",
            started_at=started,
            ended_at=datetime.utcnow(),
        )

    async def rollback(self, provider: Dict[str, Any], dry_run: bool = False) -> ActionResult:
        restart_cmd = provider.get("restart_cmd")
        started = datetime.utcnow()
        if restart_cmd and not dry_run:
            proc = await asyncio.create_subprocess_shell(restart_cmd)
            await proc.communicate()
        return ActionResult(
            action_name=f"{self.name}/rollback",
            success=True,
            output=f"K-Reaper: ran restart '{restart_cmd}'" if restart_cmd else "K-Reaper: no restart command configured",
            started_at=started,
            ended_at=datetime.utcnow(),
        )
