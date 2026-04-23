"""PagerDuty integration — fires an event when an experiment aborts or fails."""

from __future__ import annotations

import httpx

from kali.integrations.base import ObservabilityIntegration
from kali.models.experiment import ExperimentResult, ExperimentStatus

_EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"


class PagerDutyIntegration(ObservabilityIntegration):
    name = "pagerduty"

    def __init__(self, routing_key: str) -> None:
        self._routing_key = routing_key

    async def on_experiment_start(self, result: ExperimentResult) -> None:
        pass  # PagerDuty is alert-only

    async def on_experiment_end(self, result: ExperimentResult) -> None:
        if result.status in (ExperimentStatus.aborted, ExperimentStatus.failed):
            await self._trigger(result)

    async def on_abort(self, result: ExperimentResult, reason: str) -> None:
        await self._trigger(result, summary=f"Kali experiment aborted: {reason}")

    async def _trigger(self, result: ExperimentResult, summary: Optional[str] = None) -> None:  # type: ignore[name-defined]
        payload = {
            "routing_key": self._routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": summary or f"Kali: experiment '{result.experiment_title}' {result.status}",
                "severity": "warning",
                "source": "kali-chaos",
                "custom_details": {
                    "status": result.status,
                    "abort_reason": result.abort_reason,
                    "duration_s": result.duration_seconds,
                },
            },
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(_EVENTS_URL, json=payload)
        except Exception:
            pass
