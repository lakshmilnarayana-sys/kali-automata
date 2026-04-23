"""Steady-state hypothesis probes."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from kali.models.experiment import Probe, ProbeResult, ProbeType


async def run_probe(probe: Probe, dry_run: bool = False) -> ProbeResult:
    if dry_run:
        return ProbeResult(probe_name=probe.name, passed=True, value="[dry-run]")

    match probe.type:
        case ProbeType.http:
            return await _http_probe(probe)
        case ProbeType.metric:
            return await _metric_probe(probe)
        case ProbeType.process:
            return await _process_probe(probe)
        case _:
            return ProbeResult(
                probe_name=probe.name,
                passed=False,
                error=f"Unsupported probe type: {probe.type}",
            )


async def _http_probe(probe: Probe) -> ProbeResult:
    provider = probe.provider
    url: str = provider["url"]
    method: str = provider.get("method", "GET").upper()
    expected_status: int = provider.get("expected_status", 200)
    timeout: float = provider.get("timeout", 5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(method, url)
            passed = resp.status_code == expected_status
            if probe.tolerance and not passed:
                passed = resp.status_code in (probe.tolerance if isinstance(probe.tolerance, list) else [probe.tolerance])
            return ProbeResult(
                probe_name=probe.name,
                passed=passed,
                value=resp.status_code,
                error=None if passed else f"Got {resp.status_code}, expected {expected_status}",
            )
    except Exception as exc:
        return ProbeResult(probe_name=probe.name, passed=False, error=str(exc))


async def _metric_probe(probe: Probe) -> ProbeResult:
    """Query a Prometheus-compatible /metrics endpoint."""
    provider = probe.provider
    url: str = provider["url"]
    metric_name: str = provider["metric"]
    operator: str = provider.get("operator", ">=")
    threshold: float = float(provider["threshold"])
    timeout: float = provider.get("timeout", 5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, params={"query": metric_name})
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            if not results:
                return ProbeResult(probe_name=probe.name, passed=False, error=f"No data for metric {metric_name}")
            value = float(results[0]["value"][1])
            passed = _compare(value, operator, threshold)
            return ProbeResult(
                probe_name=probe.name,
                passed=passed,
                value=value,
                error=None if passed else f"{value} {operator} {threshold} is False",
            )
    except Exception as exc:
        return ProbeResult(probe_name=probe.name, passed=False, error=str(exc))


async def _process_probe(probe: Probe) -> ProbeResult:
    process_name: str = probe.provider["process"]
    try:
        proc = await asyncio.create_subprocess_shell(
            f"pgrep -x {process_name}",
            stdout=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        running = proc.returncode == 0
        return ProbeResult(
            probe_name=probe.name,
            passed=running,
            value="running" if running else "stopped",
            error=None if running else f"Process '{process_name}' not found",
        )
    except Exception as exc:
        return ProbeResult(probe_name=probe.name, passed=False, error=str(exc))


def _compare(value: float, operator: str, threshold: float) -> bool:
    match operator:
        case ">=": return value >= threshold
        case "<=": return value <= threshold
        case ">":  return value > threshold
        case "<":  return value < threshold
        case "==": return value == threshold
        case "!=": return value != threshold
        case _:    return False
