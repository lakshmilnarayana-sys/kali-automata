"""Core experiment runner — orchestrates the full chaos lifecycle."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import List

from kali.experiments import INJECTOR_REGISTRY
from kali.hypothesis.probes import run_probe
from kali.integrations.base import ObservabilityIntegration
from kali.models.experiment import Experiment, ExperimentResult, ExperimentStatus
from kali.safety.circuit_breaker import CircuitBreaker, CircuitBreakerTripped
from kali.scoring import compute_resiliency_score


class BlastRadiusBlocked(Exception):
    """Raised when blast_radius == 100% — experiment is never executed."""


class ExperimentRunner:
    def __init__(self, integrations: List[ObservabilityIntegration] | None = None) -> None:
        self._integrations = integrations or []

    async def run(self, experiment: Experiment) -> ExperimentResult:
        result = ExperimentResult(
            experiment_title=experiment.title,
            status=ExperimentStatus.running,
            dry_run=experiment.dry_run,
            blast_radius=experiment.blast_radius,
            started_at=datetime.utcnow(),
        )

        # ── Safety gate: blast radius 100% is always blocked ─────────────────
        if experiment.blast_radius >= 100 and not experiment.dry_run:
            result.status = ExperimentStatus.aborted
            result.abort_reason = (
                f"Blast radius is {experiment.blast_radius}% — execution blocked. "
                "Reduce to ≤ 99% to proceed."
            )
            return await self._finalize(result)

        await self._notify_start(result)

        cb = CircuitBreaker(experiment.circuit_breaker, experiment.steady_state_hypothesis.probes)

        try:
            # 1. Verify steady state before chaos
            result.steady_state_before = [
                await run_probe(p, dry_run=experiment.dry_run)
                for p in experiment.steady_state_hypothesis.probes
            ]
            if not all(r.passed for r in result.steady_state_before):
                result.status = ExperimentStatus.aborted
                result.abort_reason = "Steady state not met before experiment — aborting to protect target."
                return await self._finalize(result)

            # 2. Start circuit breaker background monitor
            await cb.start()

            try:
                # 3. Execute method (fault injections)
                for action in experiment.method:
                    injector = INJECTOR_REGISTRY.get(action.type.value)
                    if not injector:
                        raise ValueError(f"No injector registered for type '{action.type}'")

                    if action.pauses and action.pauses.get("before"):
                        await asyncio.sleep(action.pauses["before"])

                    action_result = await injector.inject(
                        action.provider, action.duration, dry_run=experiment.dry_run
                    )
                    result.actions.append(action_result)

                    if not action_result.success:
                        result.status = ExperimentStatus.failed
                        result.abort_reason = f"Action '{action.name}' failed: {action_result.error}"
                        break

                    if action.pauses and action.pauses.get("after"):
                        await asyncio.sleep(action.pauses["after"])

            except CircuitBreakerTripped as exc:
                result.status = ExperimentStatus.aborted
                result.abort_reason = str(exc)
                await self._notify_abort(result, str(exc))

            finally:
                # Stop the circuit breaker immediately
                await cb.stop()

            # 4. Immediate concurrent rollback — always, regardless of outcome
            await self._rollback_immediately(experiment, result)

            # 5. Verify steady state recovered
            result.steady_state_after = [
                await run_probe(p, dry_run=experiment.dry_run)
                for p in experiment.steady_state_hypothesis.probes
            ]

            if result.status == ExperimentStatus.running:
                result.status = (
                    ExperimentStatus.completed
                    if result.hypothesis_held
                    else ExperimentStatus.failed
                )
                if not result.hypothesis_held:
                    result.abort_reason = "Steady state did not recover after experiment."

        except Exception as exc:
            result.status = ExperimentStatus.failed
            result.abort_reason = str(exc)
            # Best-effort rollback on unexpected failure
            try:
                await self._rollback_immediately(experiment, result)
            except Exception:
                pass

        return await self._finalize(result)

    async def _rollback_immediately(self, experiment: Experiment, result: ExperimentResult) -> None:
        """Execute all rollbacks concurrently for minimum recovery time."""
        if not experiment.rollbacks:
            return

        async def _do_rollback(rb):  # type: ignore[no-untyped-def]
            injector = INJECTOR_REGISTRY.get(rb.type.value)
            if injector:
                return await injector.rollback(rb.provider, dry_run=experiment.dry_run)
            return None

        rb_results = await asyncio.gather(
            *[_do_rollback(rb) for rb in experiment.rollbacks],
            return_exceptions=True,
        )
        for r in rb_results:
            if r and not isinstance(r, Exception):
                result.rollbacks_executed.append(r)

    async def _finalize(self, result: ExperimentResult) -> ExperimentResult:
        result.ended_at = datetime.utcnow()
        result.resiliency_score = compute_resiliency_score(result)
        await self._notify_end(result)
        return result

    async def _notify_start(self, result: ExperimentResult) -> None:
        for i in self._integrations:
            await i.on_experiment_start(result)

    async def _notify_end(self, result: ExperimentResult) -> None:
        for i in self._integrations:
            await i.on_experiment_end(result)

    async def _notify_abort(self, result: ExperimentResult, reason: str) -> None:
        for i in self._integrations:
            await i.on_abort(result, reason)
