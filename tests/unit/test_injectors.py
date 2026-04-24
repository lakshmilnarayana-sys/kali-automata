"""Unit tests for all K-* fault injectors (dry-run and rollback)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kali.experiments.k_divide import KDivideDNSFaultInjector, KDivideNetworkPartitionInjector
from kali.experiments.k_gravity import KGravityCPUStressInjector, KGravityMemoryStressInjector
from kali.experiments.k_reaper import KReaperProcessKillInjector
from kali.experiments.k_vortex import KVortexLatencyInjector, KVortexPacketLossInjector
from kali.experiments import INJECTOR_REGISTRY


# ── Registry ──────────────────────────────────────────────────────────────────

def test_registry_contains_all_types():
    expected = {
        "network/latency",
        "network/loss",
        "network/partition",
        "network/dns-fault",
        "cpu/stress",
        "memory/stress",
        "process/kill",
    }
    assert expected.issubset(set(INJECTOR_REGISTRY.keys()))


# ── K-Vortex ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kvortex_latency_dry_run():
    injector = KVortexLatencyInjector()
    result = await injector.inject(
        {"interface": "lo0", "delay_ms": 200, "jitter_ms": 50}, duration=1, dry_run=True
    )
    assert result.success is True
    assert "[dry-run]" in result.output


@pytest.mark.asyncio
async def test_kvortex_latency_rollback_dry_run():
    injector = KVortexLatencyInjector()
    result = await injector.rollback({"interface": "lo0"}, dry_run=True)
    assert result.success is True


@pytest.mark.asyncio
async def test_kvortex_latency_inject_returns_failure_on_nonzero():
    mock_proc = MagicMock()
    mock_proc.returncode = 2
    mock_proc.communicate = AsyncMock(return_value=(b"", b"RTNETLINK error"))

    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock, return_value=mock_proc):
        injector = KVortexLatencyInjector()
        result = await injector.inject({"interface": "eth0", "delay_ms": 100, "jitter_ms": 10}, 1, dry_run=False)

    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_kvortex_packet_loss_dry_run():
    injector = KVortexPacketLossInjector()
    result = await injector.inject({"interface": "lo0", "loss_percent": 10}, 1, dry_run=True)
    assert result.success is True


@pytest.mark.asyncio
async def test_kvortex_packet_loss_rollback_dry_run():
    injector = KVortexPacketLossInjector()
    result = await injector.rollback({"interface": "lo0"}, dry_run=True)
    assert result.success is True


# ── K-Reaper ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kreaper_kill_dry_run_by_process_name():
    injector = KReaperProcessKillInjector()
    result = await injector.inject(
        {"process": "myapp", "signal": "SIGTERM"}, duration=1, dry_run=True
    )
    assert result.success is True
    assert "[dry-run]" in result.output


@pytest.mark.asyncio
async def test_kreaper_kill_dry_run_by_pid():
    injector = KReaperProcessKillInjector()
    result = await injector.inject(
        {"pid": 12345, "signal": "SIGKILL"}, duration=1, dry_run=True
    )
    assert result.success is True


@pytest.mark.asyncio
async def test_kreaper_kill_fails_without_process_or_pid():
    injector = KReaperProcessKillInjector()
    result = await injector.inject({}, duration=1, dry_run=True)
    assert result.success is False
    assert "process" in result.error.lower() or "pid" in result.error.lower()


@pytest.mark.asyncio
async def test_kreaper_rollback_no_restart_cmd():
    injector = KReaperProcessKillInjector()
    result = await injector.rollback({}, dry_run=True)
    assert result.success is True
    assert "no restart" in result.output.lower()


@pytest.mark.asyncio
async def test_kreaper_rollback_with_restart_cmd_dry_run():
    injector = KReaperProcessKillInjector()
    result = await injector.rollback({"restart_cmd": "systemctl start myapp"}, dry_run=True)
    assert result.success is True


# ── K-Gravity ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kgravity_cpu_dry_run():
    injector = KGravityCPUStressInjector()
    result = await injector.inject({"workers": 2, "load_percent": 80}, 1, dry_run=True)
    assert result.success is True
    assert "[dry-run]" in result.output


@pytest.mark.asyncio
async def test_kgravity_cpu_rollback_dry_run():
    injector = KGravityCPUStressInjector()
    result = await injector.rollback({}, dry_run=True)
    assert result.success is True


@pytest.mark.asyncio
async def test_kgravity_memory_dry_run():
    injector = KGravityMemoryStressInjector()
    result = await injector.inject({"workers": 1, "memory_mb": 256}, 1, dry_run=True)
    assert result.success is True
    assert "[dry-run]" in result.output


@pytest.mark.asyncio
async def test_kgravity_memory_rollback_dry_run():
    injector = KGravityMemoryStressInjector()
    result = await injector.rollback({}, dry_run=True)
    assert result.success is True


# ── K-Divide ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kdivide_partition_dry_run():
    injector = KDivideNetworkPartitionInjector()
    result = await injector.inject(
        {"targets": ["10.0.0.1"], "direction": "both"}, 1, dry_run=True
    )
    assert result.success is True
    assert "dry-run" in result.output


@pytest.mark.asyncio
async def test_kdivide_partition_fails_without_targets():
    injector = KDivideNetworkPartitionInjector()
    result = await injector.inject({"targets": []}, 1, dry_run=False)
    assert result.success is False
    assert "targets" in result.error.lower()


@pytest.mark.asyncio
async def test_kdivide_partition_rollback_dry_run():
    injector = KDivideNetworkPartitionInjector()
    result = await injector.rollback(
        {"targets": ["10.0.0.1"], "direction": "both"}, dry_run=True
    )
    assert result.success is True


@pytest.mark.asyncio
async def test_kdivide_dns_poison_dry_run():
    injector = KDivideDNSFaultInjector()
    result = await injector.inject(
        {"mode": "poison", "domains": ["bad.example.com"], "blackhole_ip": "192.0.2.1"},
        1, dry_run=True,
    )
    assert result.success is True
    assert "/etc/hosts" in result.output


@pytest.mark.asyncio
async def test_kdivide_dns_block_dry_run():
    injector = KDivideDNSFaultInjector()
    result = await injector.inject({"mode": "block"}, 1, dry_run=True)
    assert result.success is True
    assert "53" in result.output


@pytest.mark.asyncio
async def test_kdivide_dns_poison_fails_without_domains():
    injector = KDivideDNSFaultInjector()
    result = await injector.inject({"mode": "poison", "domains": []}, 1, dry_run=False)
    assert result.success is False
    assert "domains" in result.error.lower()


@pytest.mark.asyncio
async def test_kdivide_dns_unknown_mode():
    injector = KDivideDNSFaultInjector()
    result = await injector.inject({"mode": "explode"}, 1, dry_run=False)
    assert result.success is False
    assert "Unknown" in result.error


@pytest.mark.asyncio
async def test_kdivide_dns_rollback_poison_dry_run():
    injector = KDivideDNSFaultInjector()
    result = await injector.rollback(
        {"mode": "poison", "domains": ["bad.example.com"]}, dry_run=True
    )
    assert result.success is True


@pytest.mark.asyncio
async def test_kdivide_dns_rollback_block_dry_run():
    injector = KDivideDNSFaultInjector()
    result = await injector.rollback({"mode": "block"}, dry_run=True)
    assert result.success is True
