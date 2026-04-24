"""Pydantic schemas for experiment definitions and results."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProbeType(str, Enum):
    http = "http"
    metric = "metric"
    process = "process"
    custom = "custom"


class ActionType(str, Enum):
    # K-Vortex: network latency and disruption
    network_latency = "network/latency"
    network_loss = "network/loss"
    # K-Reaper: pod and service termination
    process_kill = "process/kill"
    # K-Gravity: resource overload and pressure
    cpu_stress = "cpu/stress"
    memory_stress = "memory/stress"
    disk_stress = "disk/stress"
    # K-Divide: network partitions and DNS faults
    network_partition = "network/partition"
    network_dns_fault = "network/dns-fault"
    # K-Kube: Kubernetes fault injection
    kubernetes_pod_delete = "kubernetes/pod-delete"
    kubernetes_node_drain = "kubernetes/node-drain"
    kubernetes_scale_down = "kubernetes/scale-down"
    kubernetes_network_policy = "kubernetes/network-policy"
    kubernetes_resource_limit = "kubernetes/resource-limit"
    custom = "custom"


class ExperimentStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    aborted = "aborted"
    failed = "failed"


class Probe(BaseModel):
    name: str
    type: ProbeType
    provider: Dict[str, Any]
    tolerance: Optional[Any] = None


class SteadyStateHypothesis(BaseModel):
    title: str
    probes: List[Probe]


class Action(BaseModel):
    name: str
    type: ActionType
    provider: Dict[str, Any]
    duration: int = Field(default=30, description="Duration in seconds")
    pauses: Optional[Dict[str, int]] = None


class RollbackAction(BaseModel):
    name: str
    type: ActionType
    provider: Dict[str, Any]


class CircuitBreakerConfig(BaseModel):
    enabled: bool = True
    check_interval: int = Field(default=10, description="Seconds between checks")
    max_failures: int = 3


class Experiment(BaseModel):
    version: str = "1.0.0"
    title: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    blast_radius: int = Field(default=50, ge=0, le=100, description="% of target affected. 100% is blocked.")
    steady_state_hypothesis: SteadyStateHypothesis
    method: List[Action]
    rollbacks: List[RollbackAction] = Field(default_factory=list)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    dry_run: bool = False


class ProbeResult(BaseModel):
    probe_name: str
    passed: bool
    value: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ActionResult(BaseModel):
    action_name: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    started_at: datetime
    ended_at: datetime


class ResiliencyScore(BaseModel):
    score: int = Field(ge=0, le=100)
    grade: str
    breakdown: Dict[str, int]


class ExperimentResult(BaseModel):
    experiment_title: str
    status: ExperimentStatus
    dry_run: bool = False
    blast_radius: int = 50
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    steady_state_before: List[ProbeResult] = Field(default_factory=list)
    steady_state_after: List[ProbeResult] = Field(default_factory=list)
    actions: List[ActionResult] = Field(default_factory=list)
    rollbacks_executed: List[ActionResult] = Field(default_factory=list)
    abort_reason: Optional[str] = None
    resiliency_score: Optional[ResiliencyScore] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    @property
    def hypothesis_held(self) -> bool:
        return all(p.passed for p in self.steady_state_after)
