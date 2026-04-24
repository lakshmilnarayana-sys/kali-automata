"""Unit tests for Pydantic experiment models."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from kali.models.experiment import (
    Action,
    ActionType,
    CircuitBreakerConfig,
    Experiment,
    ExperimentResult,
    ExperimentStatus,
    Probe,
    ProbeResult,
    ProbeType,
    ResiliencyScore,
    RollbackAction,
    SteadyStateHypothesis,
)

EXPERIMENTS_DIR = Path(__file__).parent.parent.parent / "experiments"


def _load(filename: str) -> Experiment:
    raw = yaml.safe_load((EXPERIMENTS_DIR / filename).read_text())
    return Experiment.model_validate(raw)


# ── Example YAML loading ──────────────────────────────────────────────────────

def test_network_latency_yaml_loads():
    exp = _load("network-latency.yaml")
    assert exp.title
    assert len(exp.steady_state_hypothesis.probes) == 1
    assert len(exp.method) == 1
    assert len(exp.rollbacks) == 1
    assert exp.method[0].type == ActionType.network_latency


def test_cpu_stress_yaml_loads():
    exp = _load("cpu-stress.yaml")
    assert len(exp.steady_state_hypothesis.probes) == 2
    assert exp.method[0].type == ActionType.cpu_stress
    assert exp.method[0].duration == 30


def test_k_divide_dns_yaml_loads():
    exp = _load("k-divide-dns.yaml")
    assert exp.method[0].type == ActionType.network_dns_fault
    assert "mode" in exp.method[0].provider


def test_k_divide_partition_yaml_loads():
    exp = _load("k-divide-partition.yaml")
    assert exp.method[0].type == ActionType.network_partition
    assert isinstance(exp.method[0].provider["targets"], list)


# ── Blast radius validation ───────────────────────────────────────────────────

def test_blast_radius_default_is_50():
    exp = Experiment(
        title="t",
        steady_state_hypothesis=SteadyStateHypothesis(title="h", probes=[]),
        method=[],
    )
    assert exp.blast_radius == 50


def test_blast_radius_accepts_0_to_100():
    for val in (0, 1, 50, 99, 100):
        exp = Experiment(
            title="t",
            blast_radius=val,
            steady_state_hypothesis=SteadyStateHypothesis(title="h", probes=[]),
            method=[],
        )
        assert exp.blast_radius == val


def test_blast_radius_rejects_negative():
    with pytest.raises(ValidationError):
        Experiment(
            title="t",
            blast_radius=-1,
            steady_state_hypothesis=SteadyStateHypothesis(title="h", probes=[]),
            method=[],
        )


def test_blast_radius_rejects_above_100():
    with pytest.raises(ValidationError):
        Experiment(
            title="t",
            blast_radius=101,
            steady_state_hypothesis=SteadyStateHypothesis(title="h", probes=[]),
            method=[],
        )


# ── ExperimentResult properties ───────────────────────────────────────────────

def test_hypothesis_held_all_passed():
    result = ExperimentResult(
        experiment_title="t",
        status=ExperimentStatus.completed,
        steady_state_after=[
            ProbeResult(probe_name="p1", passed=True),
            ProbeResult(probe_name="p2", passed=True),
        ],
    )
    assert result.hypothesis_held is True


def test_hypothesis_held_one_failed():
    result = ExperimentResult(
        experiment_title="t",
        status=ExperimentStatus.failed,
        steady_state_after=[
            ProbeResult(probe_name="p1", passed=True),
            ProbeResult(probe_name="p2", passed=False, error="timeout"),
        ],
    )
    assert result.hypothesis_held is False


def test_hypothesis_held_empty_probes():
    result = ExperimentResult(
        experiment_title="t",
        status=ExperimentStatus.completed,
        steady_state_after=[],
    )
    assert result.hypothesis_held is True


def test_duration_seconds_computed():
    now = datetime(2024, 1, 1, 12, 0, 0)
    result = ExperimentResult(
        experiment_title="t",
        status=ExperimentStatus.completed,
        started_at=now,
        ended_at=now + timedelta(seconds=42),
    )
    assert result.duration_seconds == 42.0


def test_duration_seconds_none_when_not_ended():
    result = ExperimentResult(experiment_title="t", status=ExperimentStatus.running)
    assert result.duration_seconds is None


# ── Model construction ────────────────────────────────────────────────────────

def test_circuit_breaker_defaults():
    cb = CircuitBreakerConfig()
    assert cb.enabled is True
    assert cb.check_interval == 10
    assert cb.max_failures == 3


def test_action_default_duration():
    action = Action(
        name="test",
        type=ActionType.cpu_stress,
        provider={"workers": 1, "load_percent": 80},
    )
    assert action.duration == 30


def test_probe_type_enum_values():
    assert ProbeType.http == "http"
    assert ProbeType.metric == "metric"
    assert ProbeType.process == "process"


def test_action_type_enum_all_k_modules():
    assert ActionType.network_latency == "network/latency"
    assert ActionType.network_loss == "network/loss"
    assert ActionType.network_partition == "network/partition"
    assert ActionType.network_dns_fault == "network/dns-fault"
    assert ActionType.cpu_stress == "cpu/stress"
    assert ActionType.memory_stress == "memory/stress"
    assert ActionType.process_kill == "process/kill"


def test_resiliency_score_model():
    score = ResiliencyScore(score=85, grade="B", breakdown={"steady_state_recovery": 60})
    assert score.score == 85
    assert score.grade == "B"
