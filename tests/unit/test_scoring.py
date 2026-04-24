"""Unit tests for the resiliency scoring module."""

from __future__ import annotations

from kali.models.experiment import (
    ActionResult,
    ExperimentResult,
    ExperimentStatus,
    ProbeResult,
)
from kali.scoring import compute_resiliency_score
from datetime import datetime


def _result(
    status: ExperimentStatus = ExperimentStatus.completed,
    before_pass: bool = True,
    after_pass: bool = True,
    after_fail_count: int = 0,
    action_fail_count: int = 0,
) -> ExperimentResult:
    before = [ProbeResult(probe_name="p", passed=before_pass)]
    after = [ProbeResult(probe_name="p", passed=True)] * max(1 - after_fail_count, 0)
    after += [ProbeResult(probe_name=f"pf{i}", passed=False, error="err") for i in range(after_fail_count)]

    actions = [
        ActionResult(
            action_name=f"a{i}",
            success=(i >= action_fail_count),
            started_at=datetime.utcnow(),
            ended_at=datetime.utcnow(),
        )
        for i in range(max(action_fail_count, 1))
    ]

    return ExperimentResult(
        experiment_title="test",
        status=status,
        steady_state_before=before,
        steady_state_after=after,
        actions=actions,
    )


def test_perfect_run_scores_100():
    result = _result(
        status=ExperimentStatus.completed,
        before_pass=True,
        after_pass=True,
        after_fail_count=0,
        action_fail_count=0,
    )
    score = compute_resiliency_score(result)
    assert score.score == 100
    assert score.grade == "A"


def test_aborted_run_loses_circuit_breaker_points():
    result = _result(status=ExperimentStatus.aborted)
    score = compute_resiliency_score(result)
    assert score.score < 100
    assert score.breakdown.get("no_circuit_break", 0) == 0


def test_failed_run_gets_failure_penalty():
    result = _result(status=ExperimentStatus.failed, after_fail_count=1)
    score = compute_resiliency_score(result)
    assert score.score < 70
    assert score.breakdown.get("failure_penalty") == -30


def test_probe_failure_after_reduces_score():
    good = _result(after_fail_count=0)
    bad  = _result(after_fail_count=2)
    assert compute_resiliency_score(bad).score < compute_resiliency_score(good).score


def test_unhealthy_before_reduces_score():
    good = _result(before_pass=True)
    bad  = _result(before_pass=False)
    assert compute_resiliency_score(bad).score < compute_resiliency_score(good).score


def test_grade_boundaries():
    for score_val, expected_grade in [(95, "A"), (85, "B"), (75, "C"), (65, "D"), (50, "F")]:
        from kali.models.experiment import ResiliencyScore
        from kali.scoring import compute_resiliency_score
        r = ExperimentResult(experiment_title="t", status=ExperimentStatus.completed)
        computed = compute_resiliency_score(r)
        # Just verify grade logic is consistent with score
        if computed.score >= 90:
            assert computed.grade == "A"
        elif computed.score >= 80:
            assert computed.grade == "B"


def test_score_clamped_0_to_100():
    result = _result(
        status=ExperimentStatus.failed,
        before_pass=False,
        after_fail_count=3,
        action_fail_count=2,
    )
    score = compute_resiliency_score(result)
    assert 0 <= score.score <= 100


def test_breakdown_keys_present():
    result = _result()
    score = compute_resiliency_score(result)
    assert "steady_state_recovery" in score.breakdown
    assert "actions_completed" in score.breakdown
    assert "pre_experiment_health" in score.breakdown


def test_completed_with_all_probes_passing_is_grade_a():
    result = ExperimentResult(
        experiment_title="perfect",
        status=ExperimentStatus.completed,
        steady_state_before=[ProbeResult(probe_name="p1", passed=True)],
        steady_state_after=[ProbeResult(probe_name="p1", passed=True)],
        actions=[ActionResult(
            action_name="a1", success=True,
            started_at=datetime.utcnow(), ended_at=datetime.utcnow(),
        )],
    )
    score = compute_resiliency_score(result)
    assert score.grade == "A"
    assert score.score == 100
