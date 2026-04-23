"""Unit tests for experiment models."""

import pytest
import yaml
from pathlib import Path

from kali.models.experiment import Experiment, ExperimentStatus, ExperimentResult, ProbeResult


EXPERIMENTS_DIR = Path(__file__).parent.parent.parent / "experiments"


def load_experiment(filename: str) -> Experiment:
    raw = yaml.safe_load((EXPERIMENTS_DIR / filename).read_text())
    return Experiment.model_validate(raw)


def test_network_latency_experiment_loads():
    exp = load_experiment("network-latency.yaml")
    assert exp.title
    assert len(exp.steady_state_hypothesis.probes) == 1
    assert len(exp.method) == 1
    assert len(exp.rollbacks) == 1


def test_cpu_stress_experiment_loads():
    exp = load_experiment("cpu-stress.yaml")
    assert exp.title
    assert len(exp.steady_state_hypothesis.probes) == 2
    assert exp.method[0].duration == 30


def test_experiment_result_hypothesis_held():
    result = ExperimentResult(
        experiment_title="test",
        status=ExperimentStatus.completed,
        steady_state_after=[
            ProbeResult(probe_name="p1", passed=True),
            ProbeResult(probe_name="p2", passed=True),
        ],
    )
    assert result.hypothesis_held is True


def test_experiment_result_hypothesis_failed():
    result = ExperimentResult(
        experiment_title="test",
        status=ExperimentStatus.failed,
        steady_state_after=[
            ProbeResult(probe_name="p1", passed=True),
            ProbeResult(probe_name="p2", passed=False, error="timeout"),
        ],
    )
    assert result.hypothesis_held is False
