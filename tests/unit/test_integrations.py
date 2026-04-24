"""Unit tests for observability integrations — all must be non-fatal."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kali.integrations.datadog import DatadogIntegration
from kali.integrations.pagerduty import PagerDutyIntegration
from kali.integrations.prometheus import PrometheusIntegration
from kali.models.experiment import ExperimentResult, ExperimentStatus


def _result(status: ExperimentStatus = ExperimentStatus.completed) -> ExperimentResult:
    return ExperimentResult(experiment_title="test", status=status)


# ── Prometheus ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_prometheus_on_start_succeeds():
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock()

        integration = PrometheusIntegration("http://pushgateway:9091")
        await integration.on_experiment_start(_result())

        mock_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
async def test_prometheus_on_end_succeeds():
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock()

        integration = PrometheusIntegration("http://pushgateway:9091")
        await integration.on_experiment_end(_result())

        mock_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
async def test_prometheus_silences_network_error():
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock(side_effect=Exception("connection refused"))

        integration = PrometheusIntegration("http://pushgateway:9091")
        # Must NOT raise
        await integration.on_experiment_end(_result())


# ── Datadog ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_datadog_on_start_posts_event():
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock()

        integration = DatadogIntegration(api_key="test-key")
        await integration.on_experiment_start(_result())

        mock_client.return_value.post.assert_called_once()
        call_kwargs = mock_client.return_value.post.call_args
        assert "kali" in str(call_kwargs).lower() or "test" in str(call_kwargs).lower()


@pytest.mark.asyncio
async def test_datadog_on_end_uses_success_alert_type():
    posted = {}

    async def capture_post(url, json=None, headers=None):
        posted["body"] = json

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock(side_effect=capture_post)

        integration = DatadogIntegration(api_key="test-key")
        await integration.on_experiment_end(_result(ExperimentStatus.completed))

    assert posted.get("body", {}).get("alert_type") == "success"


@pytest.mark.asyncio
async def test_datadog_silences_network_error():
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock(side_effect=RuntimeError("timeout"))

        integration = DatadogIntegration(api_key="test-key")
        await integration.on_experiment_end(_result())  # must not raise


# ── PagerDuty ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pagerduty_on_start_does_nothing():
    integration = PagerDutyIntegration(routing_key="rk")
    await integration.on_experiment_start(_result())  # fire-and-forget, no HTTP call


@pytest.mark.asyncio
async def test_pagerduty_triggers_on_aborted():
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock()

        integration = PagerDutyIntegration(routing_key="rk")
        await integration.on_experiment_end(_result(ExperimentStatus.aborted))

        mock_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
async def test_pagerduty_does_not_trigger_on_success():
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock()

        integration = PagerDutyIntegration(routing_key="rk")
        await integration.on_experiment_end(_result(ExperimentStatus.completed))

        mock_client.return_value.post.assert_not_called()


@pytest.mark.asyncio
async def test_pagerduty_silences_network_error():
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock(side_effect=Exception("PD unreachable"))

        integration = PagerDutyIntegration(routing_key="rk")
        await integration.on_experiment_end(_result(ExperimentStatus.failed))  # must not raise
