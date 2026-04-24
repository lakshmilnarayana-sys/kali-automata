from kali.experiments.k_divide import KDivideDNSFaultInjector, KDivideNetworkPartitionInjector
from kali.experiments.k_gravity import KGravityCPUStressInjector, KGravityMemoryStressInjector
from kali.experiments.k_kube import (
    KKubeNetworkPolicyInjector,
    KKubeNodeDrainInjector,
    KKubePodDeleteInjector,
    KKubeResourceLimitInjector,
    KKubeScaleDownInjector,
)
from kali.experiments.k_reaper import KReaperProcessKillInjector
from kali.experiments.k_vortex import KVortexLatencyInjector, KVortexPacketLossInjector

INJECTOR_REGISTRY = {
    # K-Vortex: network latency and disruption
    "network/latency":              KVortexLatencyInjector(),
    "network/loss":                 KVortexPacketLossInjector(),
    # K-Reaper: pod and service termination
    "process/kill":                 KReaperProcessKillInjector(),
    # K-Gravity: resource overload and pressure
    "cpu/stress":                   KGravityCPUStressInjector(),
    "memory/stress":                KGravityMemoryStressInjector(),
    # K-Divide: network partitions and DNS faults
    "network/partition":            KDivideNetworkPartitionInjector(),
    "network/dns-fault":            KDivideDNSFaultInjector(),
    # K-Kube: Kubernetes fault injection
    "kubernetes/pod-delete":        KKubePodDeleteInjector(),
    "kubernetes/node-drain":        KKubeNodeDrainInjector(),
    "kubernetes/scale-down":        KKubeScaleDownInjector(),
    "kubernetes/network-policy":    KKubeNetworkPolicyInjector(),
    "kubernetes/resource-limit":    KKubeResourceLimitInjector(),
}

__all__ = [
    "INJECTOR_REGISTRY",
    "KVortexLatencyInjector",
    "KVortexPacketLossInjector",
    "KReaperProcessKillInjector",
    "KGravityCPUStressInjector",
    "KGravityMemoryStressInjector",
    "KDivideNetworkPartitionInjector",
    "KDivideDNSFaultInjector",
    "KKubePodDeleteInjector",
    "KKubeNodeDrainInjector",
    "KKubeScaleDownInjector",
    "KKubeNetworkPolicyInjector",
    "KKubeResourceLimitInjector",
]
