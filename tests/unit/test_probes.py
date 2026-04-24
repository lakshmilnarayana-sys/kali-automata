"""Unit tests for steady-state probes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kali.hypothesis.probes import _compare, run_probe
from kali.models.experiment import Probe, ProbeType


def _probe(type_: ProbeType, provider: dict) -> Probe:
    return Probe(name="test-probe", type=type_, provider=provider)


# ── dry-run always passes ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dry_run_always_passes():
    probe = _probe(ProbeType.http, {"url": "http://unreachable"})
    result = await run_probe(probe, dry_run=True)
    assert result.passed is True
    assert result.value == "[dry-run]"


# ── HTTP probe ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_http_probe_passes_on_expected_status():
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.request = AsyncMock(return_value=mock_resp)

        probe = _probe(ProbeType.http, {"url": "http://localhost/health", "expected_status": 200})
        result = await run_probe(probe)

    assert result.passed is True
    assert result.value == 200


@pytest.mark.asyncio
async def test_http_probe_fails_on_wrong_status():
    mock_resp = MagicMock()
    mock_resp.status_code = 503

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.request = AsyncMock(return_value=mock_resp)

        probe = _probe(ProbeType.http, {"url": "http://localhost/health", "expected_status": 200})
        result = await run_probe(probe)

    assert result.passed is False
    assert "503" in result.error


@pytest.mark.asyncio
async def test_http_probe_fails_on_network_error():
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.request = AsyncMock(side_effect=Exception("connection refused"))

        probe = _probe(ProbeType.http, {"url": "http://localhost/health"})
        result = await run_probe(probe)

    assert result.passed is False
    assert "connection refused" in result.error


# ── Metric probe ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_metric_probe_passes_when_threshold_met():
    payload = {"data": {"result": [{"value": ["ts", "0.005"]}]}}
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.get = AsyncMock(return_value=mock_resp)

        probe = _probe(ProbeType.metric, {
            "url": "http://prom/api/v1/query",
            "metric": "error_rate",
            "operator": "<",
            "threshold": 0.01,
        })
        result = await run_probe(probe)

    assert result.passed is True
    assert result.value == pytest.approx(0.005)


@pytest.mark.asyncio
async def test_metric_probe_fails_when_no_data():
    payload = {"data": {"result": []}}
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.get = AsyncMock(return_value=mock_resp)

        probe = _probe(ProbeType.metric, {
            "url": "http://prom/api/v1/query",
            "metric": "missing_metric",
            "operator": ">=",
            "threshold": 1.0,
        })
        result = await run_probe(probe)

    assert result.passed is False
    assert "No data" in result.error


# ── Process probe ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_probe_passes_when_running():
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"123", b""))

    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock, return_value=mock_proc):
        probe = _probe(ProbeType.process, {"process": "myapp"})
        result = await run_probe(probe)

    assert result.passed is True
    assert result.value == "running"


@pytest.mark.asyncio
async def test_process_probe_fails_when_not_running():
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))

    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock, return_value=mock_proc):
        probe = _probe(ProbeType.process, {"process": "myapp"})
        result = await run_probe(probe)

    assert result.passed is False
    assert "not found" in result.error


# ── Unsupported probe type ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unsupported_probe_type_returns_failure():
    probe = Probe(name="p", type=ProbeType.custom, provider={})
    result = await run_probe(probe)
    assert result.passed is False
    assert "Unsupported" in result.error


# ── _compare helper ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("value,op,threshold,expected", [
    (5.0, ">=", 4.0, True),
    (5.0, ">=", 5.0, True),
    (5.0, ">=", 6.0, False),
    (3.0, "<=", 4.0, True),
    (3.0, "<",  4.0, True),
    (5.0, ">",  4.0, True),
    (5.0, "==", 5.0, True),
    (5.0, "!=", 4.0, True),
    (5.0, "!=", 5.0, False),
    (5.0, "??", 1.0, False),  # unknown operator → False
])
def test_compare(value, op, threshold, expected):
    assert _compare(value, op, threshold) == expected
