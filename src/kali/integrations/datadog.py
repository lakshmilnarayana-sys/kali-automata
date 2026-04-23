"""Datadog integration — emits events and metrics via the HTTP API."""

from __future__ import annotations

import httpx

from kali.integrations.base import ObservabilityIntegration
from kali.models.experiment import ExperimentResult, ExperimentStatus

_DD_EVENTS_URL = "https://api.datadoghq.com/api/v1/events"
_DD_METRICS_URL = "https://api.datadoghq.com/api/v1/series"


class DatadogIntegration(ObservabilityIntegration):
    name = "datadog"

    def __init__(self, api_key: str, site: str = "datadoghq.com") -> None:
        self._api_key = api_key
        self._events_url = f"https://api.{site}/api/v1/events"
        self._metrics_url = f"https://api.{site}/api/v1/series"
        self._headers = {"DD-API-KEY": api_key, "Content-Type": "application/json"}

    async def on_experiment_start(self, result: ExperimentResult) -> None:
        await self._post_event(result, "started", "info")

    async def on_experiment_end(self, result: ExperimentResult) -> None:
        alert = "success" if result.status == ExperimentStatus.completed else "error"
        await self._post_event(result, result.status.value, alert)

    async def _post_event(self, result: ExperimentResult, status: str, alert_type: str) -> None:
        body = {
            "title": f"Kali: {result.experiment_title}",
            "text": f"Experiment {status}. Dry-run: {result.dry_run}",
            "alert_type": alert_type,
            "tags": [f"kali:experiment", f"status:{status}"],
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(self._events_url, json=body, headers=self._headers)
        except Exception:
            pass
