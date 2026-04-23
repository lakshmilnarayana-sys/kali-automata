from kali.experiments.cpu import CPUStressInjector
from kali.experiments.network import NetworkLatencyInjector, NetworkPacketLossInjector
from kali.experiments.process import ProcessKillInjector

INJECTOR_REGISTRY = {
    "cpu/stress": CPUStressInjector(),
    "network/latency": NetworkLatencyInjector(),
    "network/loss": NetworkPacketLossInjector(),
    "process/kill": ProcessKillInjector(),
}

__all__ = [
    "INJECTOR_REGISTRY",
    "CPUStressInjector",
    "NetworkLatencyInjector",
    "NetworkPacketLossInjector",
    "ProcessKillInjector",
]
