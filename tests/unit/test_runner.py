"""Unit tests for the experiment runner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from kali.engine.runner import ExperimentRunner
from kali.models.experiment import (
    Action,
    ActionType,
    CircuitBreakerConfig,
    Experiment,
    ExperimentStatus,
    Probe,
    ProbeType,
    RollbackAction,
    SteadyStateHypothesis,
)

EXPERIMENTS_DIR = Path(__file__).parent.parent.parent / "experiments"


def _load_dry(filename: str) -> Experiment:
    raw = yaml.safe_load((EXPERIMENTS_DIR / filename).read_text())
    exp = Experiment.model_validate(raw)
    return exp.model_copy(update={"dry_run": True})


def _minimal_experiment(**overrides) -> Experiment:
    defaults = dict(
        title="test",
        dry_run=True,
        blast_radius=50,
        steady_state_hypothesis=SteadyStateHypothesis(
            title="healthy",
            probes=[Probe(name="p", type=ProbeType.http, provider={"url": "http://x"})],
        ),
        method=[
            Action(name="a", type=ActionType.cpu_stress, provider={"workers": 1, "load_percent": 50}, duration=1),
        ],
        rollbacks=[],
    )
    defaults.update(overrides)
    return Experiment(**defaults)


# ── Dry-run integration (uses real YAML files) ────────────────────────────────

@pytest.mark.asyncio
async def test_dry_run_network_latency():
    result = await ExperimentRunner().run(_load_dry("network-latency.yaml"))
    assert result.dry_run is True
    assert result.status == ExperimentStatus.completed


@pytest.mark.asyncio
async def test_dry_run_cpu_stress():
    result = await ExperimentRunner().run(_load_dry("cpu-stress.yaml"))
    assert result.status == ExperimentStatus.completed


@pytest.mark.asyncio
async def test_dry_run_k_divide_dns():
    result = await ExperimentRunner().run(_load_dry("k-divide-dns.yaml"))
    assert result.status == ExperimentStatus.completed


@pytest.mark.asyncio
async def test_dry_run_k_divide_partition():
    result = await ExperimentRunner().run(_load_dry("k-divide-partition.yaml"))
    assert result.status == ExperimentStatus.completed


# ── Blast radius safety gate ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_blast_radius_100_is_blocked():
    exp = _minimal_experiment(blast_radius=100, dry_run=False)
    result = await ExperimentRunner().run(exp)
    assert result.status == ExperimentStatus.aborted
    assert "100%" in result.abort_reason or "blocked" in (result.abort_reason or "").lower()


@pytest.mark.asyncio
async def test_blast_radius_99_is_allowed_in_dry_run():
    exp = _minimal_experiment(blast_radius=99, dry_run=True)
    result = await ExperimentRunner().run(exp)
    assert result.status == ExperimentStatus.completed


@pytest.mark.asyncio
async def test_blast_radius_100_dry_run_is_allowed():
    """dry_run=True bypasses the blast-radius gate (safe for CI validation)."""
    exp = _minimal_experiment(blast_radius=100, dry_run=True)
    result = await ExperimentRunner().run(exp)
    assert result.status == ExperimentStatus.completed


# ── Steady-state pre-check ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_aborts_when_steady_state_not_met_before():
    exp = _minimal_experiment(dry_run=False, blast_radius=50)
    failing_probe = MagicMock()
    failing_probe.passed = False
    failing_probe.error = "not healthy"

    with patch("kali.engine.runner.run_probe", new_callable=AsyncMock, return_value=failing_probe):
        result = await ExperimentRunner().run(exp)

    assert result.status == ExperimentStatus.aborted
    assert "steady state" in (result.abort_reason or "").lower()


# ── Resiliency score attached ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resiliency_score_attached_after_run():
    result = await ExperimentRunner().run(_load_dry("network-latency.yaml"))
    assert result.resiliency_score is not None
    assert 0 <= result.resiliency_score.score <= 100
    assert result.resiliency_score.grade in ("A", "B", "C", "D", "F")


# ── Rollback executes concurrently ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_rollbacks_execute_after_run():
    exp = _load_dry("network-latency.yaml")
    result = await ExperimentRunner().run(exp)
    assert len(result.rollbacks_executed) >= 1


@pytest.mark.asyncio
async def test_rollbacks_execute_on_action_failure():
    rollback = RollbackAction(
        name="rb", type=ActionType.cpu_stress, provider={"workers": 1, "load_percent": 50}
    )
    exp = _minimal_experiment(dry_run=False, blast_radius=50, rollbacks=[rollback])

    passing_probe = MagicMock()
    passing_probe.passed = True

    from kali.models.experiment import ActionResult
    from datetime import datetime
    failing_action = ActionResult(
        action_name="a", success=False, error="boom",
        started_at=datetime.utcnow(), ended_at=datetime.utcnow(),
    )

    with patch("kali.engine.runner.run_probe", new_callable=AsyncMock, return_value=passing_probe):
        with patch("kali.experiments.k_gravity.KGravityCPUStressInjector.inject",
                   new_callable=AsyncMock, return_value=failing_action):
            with patch("kali.experiments.k_gravity.KGravityCPUStressInjector.rollback",
                       new_callable=AsyncMock, return_value=ActionResult(
                           action_name="rb", success=True,
                           started_at=datetime.utcnow(), ended_at=datetime.utcnow(),
                       )):
                result = await ExperimentRunner().run(exp)

    assert result.status == ExperimentStatus.failed
    assert len(result.rollbacks_executed) == 1


# ── Integration callbacks are called ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_integration_on_start_and_end_called():
    integration = MagicMock()
    integration.on_experiment_start = AsyncMock()
    integration.on_experiment_end = AsyncMock()

    exp = _load_dry("network-latency.yaml")
    await ExperimentRunner(integrations=[integration]).run(exp)

    integration.on_experiment_start.assert_called_once()
    integration.on_experiment_end.assert_called_once()
