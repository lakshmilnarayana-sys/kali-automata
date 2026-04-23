"""Network fault injectors — latency, packet loss, partition."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict

from kali.experiments.base import FaultInjector
from kali.models.experiment import ActionResult


class NetworkLatencyInjector(FaultInjector):
    """Adds artificial latency via `tc netem`."""

    name = "network/latency"

    async def inject(self, provider: Dict[str, Any], duration: int, dry_run: bool = False) -> ActionResult:
        iface = provider.get("interface", "eth0")
        delay_ms = provider.get("delay_ms", 200)
        jitter_ms = provider.get("jitter_ms", 50)
        cmd = f"tc qdisc add dev {iface} root netem delay {delay_ms}ms {jitter_ms}ms"
        started = datetime.utcnow()
        if not dry_run:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                return ActionResult(
                    action_name=self.name,
                    success=False,
                    error=stderr.decode(),
                    started_at=started,
                    ended_at=datetime.utcnow(),
                )
            await asyncio.sleep(duration)
        return ActionResult(
            action_name=self.name,
            success=True,
            output=f"[dry-run] {cmd}" if dry_run else f"Applied {delay_ms}ms±{jitter_ms}ms on {iface}",
            started_at=started,
            ended_at=datetime.utcnow(),
        )

    async def rollback(self, provider: Dict[str, Any], dry_run: bool = False) -> ActionResult:
        iface = provider.get("interface", "eth0")
        cmd = f"tc qdisc del dev {iface} root"
        started = datetime.utcnow()
        if not dry_run:
            proc = await asyncio.create_subprocess_shell(cmd)
            await proc.communicate()
        return ActionResult(
            action_name=f"{self.name}/rollback",
            success=True,
            output=f"[dry-run] {cmd}" if dry_run else f"Removed netem on {iface}",
            started_at=started,
            ended_at=datetime.utcnow(),
        )


class NetworkPacketLossInjector(FaultInjector):
    """Drops a percentage of packets via `tc netem`."""

    name = "network/loss"

    async def inject(self, provider: Dict[str, Any], duration: int, dry_run: bool = False) -> ActionResult:
        iface = provider.get("interface", "eth0")
        loss_pct = provider.get("loss_percent", 10)
        cmd = f"tc qdisc add dev {iface} root netem loss {loss_pct}%"
        started = datetime.utcnow()
        if not dry_run:
            proc = await asyncio.create_subprocess_shell(cmd)
            await proc.communicate()
            await asyncio.sleep(duration)
        return ActionResult(
            action_name=self.name,
            success=True,
            output=f"[dry-run] {cmd}" if dry_run else f"Applied {loss_pct}% packet loss on {iface}",
            started_at=started,
            ended_at=datetime.utcnow(),
        )

    async def rollback(self, provider: Dict[str, Any], dry_run: bool = False) -> ActionResult:
        iface = provider.get("interface", "eth0")
        cmd = f"tc qdisc del dev {iface} root"
        started = datetime.utcnow()
        if not dry_run:
            proc = await asyncio.create_subprocess_shell(cmd)
            await proc.communicate()
        return ActionResult(
            action_name=f"{self.name}/rollback",
            success=True,
            output=f"Removed packet loss on {iface}",
            started_at=started,
            ended_at=datetime.utcnow(),
        )
