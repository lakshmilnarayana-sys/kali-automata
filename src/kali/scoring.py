"""Resiliency scoring — grades an experiment result on a 0-100 scale."""

from __future__ import annotations

from kali.models.experiment import ExperimentResult, ExperimentStatus, ResiliencyScore


def compute_resiliency_score(result: ExperimentResult) -> ResiliencyScore:
    """
    Scoring breakdown (100 points total):

    +60  Steady state recovered after experiment  (hypothesis held)
    +20  All actions completed without failure
    +10  Circuit breaker did NOT trip
    +10  System was healthy BEFORE the experiment

    Deductions:
    -10  Each probe that failed in steady_state_after (up to -60)
    -20  Experiment aborted by circuit breaker
    -30  Experiment status == failed
    """
    breakdown: dict[str, int] = {}

    base = 0

    # Steady state recovery (after)
    after_failures = sum(1 for p in result.steady_state_after if not p.passed)
    recovery_pts = max(0, 60 - after_failures * 10)
    breakdown["steady_state_recovery"] = recovery_pts
    base += recovery_pts

    # Actions completed
    action_failures = sum(1 for a in result.actions if not a.success)
    action_pts = 20 if action_failures == 0 else max(0, 20 - action_failures * 5)
    breakdown["actions_completed"] = action_pts
    base += action_pts

    # Circuit breaker did not trip
    if result.status != ExperimentStatus.aborted:
        breakdown["no_circuit_break"] = 10
        base += 10
    else:
        breakdown["no_circuit_break"] = 0
        base -= 20
        breakdown["abort_penalty"] = -20

    # System healthy before
    before_failures = sum(1 for p in result.steady_state_before if not p.passed)
    pre_pts = 10 if before_failures == 0 else 0
    breakdown["pre_experiment_health"] = pre_pts
    base += pre_pts

    # Hard failure penalty
    if result.status == ExperimentStatus.failed:
        breakdown["failure_penalty"] = -30
        base -= 30

    score = max(0, min(100, base))

    grade = (
        "A" if score >= 90 else
        "B" if score >= 80 else
        "C" if score >= 70 else
        "D" if score >= 60 else
        "F"
    )

    return ResiliencyScore(score=score, grade=grade, breakdown=breakdown)
