"""Abstract base for observability integrations."""

from __future__ import annotations

import abc

from kali.models.experiment import ExperimentResult


class ObservabilityIntegration(abc.ABC):
    name: str

    @abc.abstractmethod
    async def on_experiment_start(self, result: ExperimentResult) -> None:
        """Called when an experiment begins."""

    @abc.abstractmethod
    async def on_experiment_end(self, result: ExperimentResult) -> None:
        """Called when an experiment completes, aborts, or fails."""

    async def on_abort(self, result: ExperimentResult, reason: str) -> None:
        """Called when the circuit breaker trips. Defaults to on_experiment_end."""
        await self.on_experiment_end(result)
