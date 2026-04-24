"""Unit tests for the MCP server tool handlers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from kali.mcp.server import (
    _explain_result,
    _list_experiments,
    _validate_experiment,
)
from kali.models.experiment import (
    ActionResult,
    ExperimentResult,
    ExperimentStatus,
    ProbeResult,
    ResiliencyScore,
)
from datetime import datetime

EXPERIMENTS_DIR = Path(__file__).parent.parent.parent / "experiments"


# ── validate_experiment ───────────────────────────────────────────────────────

def test_validate_valid_yaml_file():
    path = str(EXPERIMENTS_DIR / "network-latency.yaml")
    result = _validate_experiment(path=path)
    assert result["valid"] is True
    assert result["fault_count"] >= 1
    assert result["probe_count"] >= 1
    assert result["blast_blocked"] is False


def test_validate_valid_yaml_string():
    yaml_content = """
version: "1.0.0"
title: Inline Test
blast_radius: 50
steady_state_hypothesis:
  title: healthy
  probes:
    - name: p
      type: http
      provider:
        url: http://localhost/health
        expected_status: 200
method:
  - name: a
    type: cpu/stress
    duration: 10
    provider:
      workers: 1
      load_percent: 80
"""
    result = _validate_experiment(yaml_content=yaml_content)
    assert result["valid"] is True
    assert result["title"] == "Inline Test"


def test_validate_invalid_yaml_returns_error():
    result = _validate_experiment(yaml_content="not: valid: yaml: [[[")
    assert result["valid"] is False
    assert "error" in result


def test_validate_missing_required_field():
    result = _validate_experiment(yaml_content="title: no-hypothesis")
    assert result["valid"] is False


def test_validate_no_path_or_content():
    result = _validate_experiment()
    assert result["valid"] is False
    assert "error" in result


def test_validate_nonexistent_file():
    result = _validate_experiment(path="/nonexistent/experiment.yaml")
    assert result["valid"] is False


def test_validate_blast_radius_100_flagged():
    yaml_content = """
version: "1.0.0"
title: Dangerous
blast_radius: 100
steady_state_hypothesis:
  title: h
  probes: []
method: []
"""
    result = _validate_experiment(yaml_content=yaml_content)
    assert result["valid"] is True
    assert result["blast_blocked"] is True


# ── list_experiments ──────────────────────────────────────────────────────────

def test_list_experiments_finds_yaml_files():
    result = _list_experiments()
    assert "experiments" in result
    names = [e["path"] for e in result["experiments"]]
    assert any("network-latency" in n for n in names)
    assert any("cpu-stress" in n for n in names)


def test_list_experiments_includes_metadata():
    result = _list_experiments()
    valid = [e for e in result["experiments"] if "title" in e]
    assert len(valid) > 0
    for exp in valid:
        assert "fault_types" in exp
        assert "blast_radius" in exp


# ── explain_result ────────────────────────────────────────────────────────────

def _make_result_json(
    status: ExperimentStatus = ExperimentStatus.completed,
    score: int = 100,
    grade: str = "A",
    abort_reason: str | None = None,
) -> str:
    now = datetime.utcnow()
    result = ExperimentResult(
        experiment_title="Explain Test",
        status=status,
        started_at=now,
        ended_at=now,
        steady_state_after=[ProbeResult(probe_name="p", passed=True)],
        abort_reason=abort_reason,
        resiliency_score=ResiliencyScore(
            score=score, grade=grade,
            breakdown={"steady_state_recovery": 60, "actions_completed": 20},
        ),
    )
    return result.model_dump_json()


def test_explain_completed_experiment():
    result = _explain_result(_make_result_json())
    explanation = result["explanation"]
    assert "Explain Test" in explanation
    assert "COMPLETED" in explanation
    assert "100/100" in explanation
    assert "Grade A" in explanation


def test_explain_aborted_experiment():
    result = _explain_result(_make_result_json(
        status=ExperimentStatus.aborted,
        score=40,
        grade="F",
        abort_reason="Circuit breaker tripped",
    ))
    explanation = result["explanation"]
    assert "ABORTED" in explanation
    assert "Circuit breaker" in explanation or "circuit" in explanation.lower()


def test_explain_failed_experiment():
    result = _explain_result(_make_result_json(status=ExperimentStatus.failed, score=30, grade="F"))
    explanation = result["explanation"]
    assert "FAILED" in explanation
    assert "Recommendations" in explanation


def test_explain_invalid_json():
    result = _explain_result("not valid json {{{")
    assert "error" in result


def test_explain_includes_recommendations():
    result = _explain_result(_make_result_json(score=100, grade="A"))
    assert "Recommendations" in result["explanation"]
    assert "resilience" in result["explanation"].lower()
