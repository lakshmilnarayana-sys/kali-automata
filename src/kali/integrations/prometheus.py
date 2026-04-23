"""Prometheus Pushgateway integration — pushes experiment events as metrics."""

from __future__ import annotations

from typing import Optional

import httpx

from kali.integrations.base import ObservabilityIntegration
from kali.models.experiment import ExperimentResult, ExperimentStatus


class PrometheusIntegration(ObservabilityIntegration):
    name = "prometheus"

    def __init__(self, pushgateway_url: str, job: str = "kali") -> None:
        self._url = pushgateway_url.rstrip("/")
        self._job = job

    async def on_experiment_start(self, result: ExperimentResult) -> None:
        await self._push(result, phase="start")

    async def on_experiment_end(self, result: ExperimentResult) -> None:
        await self._push(result, phase="end")

    async def _push(self, result: ExperimentResult, phase: str) -> None:
        labels = f'experiment="{result.experiment_title}",phase="{phase}"'
        status_value = 1 if result.status == ExperimentStatus.completed else 0
        payload = (
            f"# TYPE kali_experiment_status gauge\n"
            f"kali_experiment_status{{{labels}}} {status_value}\n"
        )
        if result.duration_seconds is not None:
            payload += (
                f"# TYPE kali_experiment_duration_seconds gauge\n"
                f"kali_experiment_duration_seconds{{{labels}}} {result.duration_seconds}\n"
            )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{self._url}/metrics/job/{self._job}",
                    content=payload,
                    headers={"Content-Type": "text/plain"},
                )
        except Exception:
            pass  # non-fatal — observability must not block experiments
