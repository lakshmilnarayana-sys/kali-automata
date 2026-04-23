"""CPU stress fault injector."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict

from kali.experiments.base import FaultInjector
from kali.models.experiment import ActionResult


class CPUStressInjector(FaultInjector):
    """Burns CPU cores using `stress-ng`."""

    name = "cpu/stress"

    async def inject(self, provider: Dict[str, Any], duration: int, dry_run: bool = False) -> ActionResult:
        workers = provider.get("workers", 2)
        cpu_load = provider.get("load_percent", 80)
        cmd = f"stress-ng --cpu {workers} --cpu-load {cpu_load} --timeout {duration}s"
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
            output=f"[dry-run] {cmd}" if dry_run else f"CPU stress: {workers} workers at {cpu_load}% for {duration}s",
            started_at=started,
            ended_at=datetime.utcnow(),
        )

    async def rollback(self, provider: Dict[str, Any], dry_run: bool = False) -> ActionResult:
        started = datetime.utcnow()
        if not dry_run:
            proc = await asyncio.create_subprocess_shell("pkill stress-ng")
            await proc.communicate()
        return ActionResult(
            action_name=f"{self.name}/rollback",
            success=True,
            output="stress-ng terminated",
            started_at=started,
            ended_at=datetime.utcnow(),
        )
