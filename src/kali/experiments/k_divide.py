"""K-Divide — network partition and DNS fault injectors."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from kali.experiments.base import FaultInjector
from kali.models.experiment import ActionResult

_HOSTS_PATH = Path("/etc/hosts")
_HOSTS_MARKER_START = "# kali:k-divide:start"
_HOSTS_MARKER_END = "# kali:k-divide:end"


class KDivideNetworkPartitionInjector(FaultInjector):
    """K-Divide: blocks traffic to/from target IPs or CIDRs via iptables."""

    name = "network/partition"

    async def inject(self, provider: Dict[str, Any], duration: int, dry_run: bool = False) -> ActionResult:
        targets: List[str] = provider.get("targets", [])
        direction: str = provider.get("direction", "both")  # inbound | outbound | both

        if not targets:
            return ActionResult(
                action_name=self.name,
                success=False,
                error="Provider must specify at least one target IP/CIDR in 'targets'",
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow(),
            )

        commands: List[str] = []
        for target in targets:
            if direction in ("inbound", "both"):
                commands.append(f"iptables -A INPUT -s {target} -j DROP")
            if direction in ("outbound", "both"):
                commands.append(f"iptables -A OUTPUT -d {target} -j DROP")

        started = datetime.utcnow()
        if not dry_run:
            for cmd in commands:
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
                        error=f"Failed '{cmd}': {stderr.decode()}",
                        started_at=started,
                        ended_at=datetime.utcnow(),
                    )
            await asyncio.sleep(duration)
        return ActionResult(
            action_name=self.name,
            success=True,
            output=(
                f"[dry-run] would run:\n" + "\n".join(commands)
                if dry_run
                else f"K-Divide: partitioned {targets} ({direction}) for {duration}s"
            ),
            started_at=started,
            ended_at=datetime.utcnow(),
        )

    async def rollback(self, provider: Dict[str, Any], dry_run: bool = False) -> ActionResult:
        targets: List[str] = provider.get("targets", [])
        direction: str = provider.get("direction", "both")
        commands: List[str] = []
        for target in targets:
            if direction in ("inbound", "both"):
                commands.append(f"iptables -D INPUT -s {target} -j DROP")
            if direction in ("outbound", "both"):
                commands.append(f"iptables -D OUTPUT -d {target} -j DROP")

        started = datetime.utcnow()
        if not dry_run:
            for cmd in commands:
                proc = await asyncio.create_subprocess_shell(cmd)
                await proc.communicate()
        return ActionResult(
            action_name=f"{self.name}/rollback",
            success=True,
            output=(
                f"[dry-run] would run:\n" + "\n".join(commands)
                if dry_run
                else f"K-Divide: partition rules removed for {targets}"
            ),
            started_at=started,
            ended_at=datetime.utcnow(),
        )


class KDivideDNSFaultInjector(FaultInjector):
    """K-Divide: injects DNS faults by poisoning /etc/hosts or blocking port 53.

    Modes (provider.mode):
      - 'poison'  — redirect specific domains to a blackhole IP via /etc/hosts
      - 'block'   — drop all DNS traffic on UDP/TCP port 53 via iptables
    """

    name = "network/dns-fault"

    async def inject(self, provider: Dict[str, Any], duration: int, dry_run: bool = False) -> ActionResult:
        mode: str = provider.get("mode", "poison")
        started = datetime.utcnow()

        if mode == "poison":
            return await self._poison_inject(provider, duration, dry_run, started)
        elif mode == "block":
            return await self._block_inject(duration, dry_run, started)
        else:
            return ActionResult(
                action_name=self.name,
                success=False,
                error=f"Unknown DNS fault mode '{mode}'. Use 'poison' or 'block'.",
                started_at=started,
                ended_at=datetime.utcnow(),
            )

    async def _poison_inject(
        self, provider: Dict[str, Any], duration: int, dry_run: bool, started: datetime
    ) -> ActionResult:
        domains: List[str] = provider.get("domains", [])
        blackhole_ip: str = provider.get("blackhole_ip", "192.0.2.1")  # TEST-NET-1, RFC5737

        if not domains:
            return ActionResult(
                action_name=self.name,
                success=False,
                error="Poison mode requires 'domains' list",
                started_at=started,
                ended_at=datetime.utcnow(),
            )

        entries = "\n".join(f"{blackhole_ip} {d}" for d in domains)
        block = f"\n{_HOSTS_MARKER_START}\n{entries}\n{_HOSTS_MARKER_END}\n"

        if not dry_run:
            original = _HOSTS_PATH.read_text()
            _HOSTS_PATH.write_text(original + block)
            await asyncio.sleep(duration)

        return ActionResult(
            action_name=self.name,
            success=True,
            output=(
                f"[dry-run] would append to /etc/hosts:\n{block}"
                if dry_run
                else f"K-Divide DNS poison: {domains} → {blackhole_ip} for {duration}s"
            ),
            started_at=started,
            ended_at=datetime.utcnow(),
        )

    async def _block_inject(self, duration: int, dry_run: bool, started: datetime) -> ActionResult:
        cmds = [
            "iptables -A OUTPUT -p udp --dport 53 -j DROP",
            "iptables -A OUTPUT -p tcp --dport 53 -j DROP",
        ]
        if not dry_run:
            for cmd in cmds:
                proc = await asyncio.create_subprocess_shell(cmd)
                await proc.communicate()
            await asyncio.sleep(duration)
        return ActionResult(
            action_name=self.name,
            success=True,
            output=(
                f"[dry-run] would run:\n" + "\n".join(cmds)
                if dry_run
                else f"K-Divide DNS block: port 53 dropped for {duration}s"
            ),
            started_at=started,
            ended_at=datetime.utcnow(),
        )

    async def rollback(self, provider: Dict[str, Any], dry_run: bool = False) -> ActionResult:
        mode: str = provider.get("mode", "poison")
        started = datetime.utcnow()

        if mode == "poison":
            if not dry_run:
                text = _HOSTS_PATH.read_text()
                # strip everything between markers (inclusive)
                lines = text.splitlines(keepends=True)
                out, skip = [], False
                for line in lines:
                    if line.strip() == _HOSTS_MARKER_START:
                        skip = True
                    if not skip:
                        out.append(line)
                    if line.strip() == _HOSTS_MARKER_END:
                        skip = False
                _HOSTS_PATH.write_text("".join(out))
            return ActionResult(
                action_name=f"{self.name}/rollback",
                success=True,
                output="[dry-run] /etc/hosts entries not modified" if dry_run else "K-Divide DNS poison cleared from /etc/hosts",
                started_at=started,
                ended_at=datetime.utcnow(),
            )
        else:
            cmds = [
                "iptables -D OUTPUT -p udp --dport 53 -j DROP",
                "iptables -D OUTPUT -p tcp --dport 53 -j DROP",
            ]
            if not dry_run:
                for cmd in cmds:
                    proc = await asyncio.create_subprocess_shell(cmd)
                    await proc.communicate()
            return ActionResult(
                action_name=f"{self.name}/rollback",
                success=True,
                output="[dry-run] iptables not modified" if dry_run else "K-Divide DNS block rules removed",
                started_at=started,
                ended_at=datetime.utcnow(),
            )
