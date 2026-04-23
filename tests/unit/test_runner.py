"""Unit tests for the experiment runner (dry-run mode)."""

import asyncio
import yaml
from pathlib import Path

import pytest

from kali.engine.runner import ExperimentRunner
from kali.models.experiment import Experiment, ExperimentStatus

EXPERIMENTS_DIR = Path(__file__).parent.parent.parent / "experiments"


def _load(filename: str) -> Experiment:
    raw = yaml.safe_load((EXPERIMENTS_DIR / filename).read_text())
    exp = Experiment.model_validate(raw)
    return exp.model_copy(update={"dry_run": True})


@pytest.mark.asyncio
async def test_dry_run_network_latency():
    exp = _load("network-latency.yaml")
    runner = ExperimentRunner()
    result = await runner.run(exp)
    assert result.dry_run is True
    assert result.status == ExperimentStatus.completed


@pytest.mark.asyncio
async def test_dry_run_cpu_stress():
    exp = _load("cpu-stress.yaml")
    runner = ExperimentRunner()
    result = await runner.run(exp)
    assert result.dry_run is True
    assert result.status == ExperimentStatus.completed
