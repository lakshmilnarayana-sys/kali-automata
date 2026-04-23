# KALI — Kinetic Automated Load and Infrastructure

> **Controlled Instability. Indestructible Infrastructure.**

Chaos engineering toolkit — fault injection, steady-state verification, and observability integrations.

Named after Kali, the Hindu goddess of destruction and transformation. Destroy deliberately. Build indestructibly.

---

## Chaos Modules

| Module | Domain | Fault Types |
|--------|--------|-------------|
| **K-Vortex** | Network Latency & Disruption | `network/latency`, `network/loss` |
| **K-Reaper** | Pod & Service Termination | `process/kill` |
| **K-Gravity** | Resource Overload & Pressure | `cpu/stress`, `memory/stress` |
| **K-Divide** | Network Partitions & DNS Faults | `network/partition`, `network/dns-fault` |

---

## Installation

```bash
pip install kali
# or from source
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# Validate an experiment definition
kali validate experiments/network-latency.yaml

# Dry run — plan without executing any faults
kali run experiments/k-divide-dns.yaml --dry-run

# Run live
kali run experiments/cpu-stress.yaml

# Save result and view report later
kali run experiments/network-latency.yaml --output results/run-001.json
kali report results/run-001.json
```

---

## Experiment Format

```yaml
version: "1.0.0"
title: "API survives 500ms network latency"
tags: [k-vortex, network, api]

steady_state_hypothesis:
  title: "API is healthy"
  probes:
    - name: api-health-check
      type: http
      provider:
        url: "http://localhost:8080/health"
        expected_status: 200
        timeout: 3.0

method:
  - name: inject-latency
    type: network/latency        # K-Vortex
    duration: 60
    provider:
      interface: eth0
      delay_ms: 500
      jitter_ms: 100

rollbacks:
  - name: remove-latency
    type: network/latency
    provider:
      interface: eth0

circuit_breaker:
  enabled: true
  check_interval: 10    # seconds between health checks
  max_failures: 3       # abort after N consecutive failures
```

---

## K-Vortex — Network Latency & Disruption

| Type | Provider keys | Description |
|------|--------------|-------------|
| `network/latency` | `interface`, `delay_ms`, `jitter_ms` | Add latency via `tc netem` |
| `network/loss` | `interface`, `loss_percent` | Drop packets via `tc netem` |

---

## K-Reaper — Pod & Service Termination

| Type | Provider keys | Description |
|------|--------------|-------------|
| `process/kill` | `process` or `pid`, `signal`, `restart_cmd` | Send signal to process |

---

## K-Gravity — Resource Overload & Pressure

| Type | Provider keys | Description |
|------|--------------|-------------|
| `cpu/stress` | `workers`, `load_percent` | Burn CPU cores via `stress-ng` |
| `memory/stress` | `workers`, `memory_mb` | Allocate RAM via `stress-ng --vm` |

---

## K-Divide — Network Partitions & DNS Faults

| Type | Provider keys | Description |
|------|--------------|-------------|
| `network/partition` | `targets` (list of IPs/CIDRs), `direction` (inbound/outbound/both) | Block traffic via `iptables` |
| `network/dns-fault` | `mode` (poison/block), `domains`, `blackhole_ip` | Poison `/etc/hosts` or block port 53 |

---

## Probe Types

| Type | Description |
|------|-------------|
| `http` | HTTP/HTTPS health check (status code) |
| `metric` | Prometheus-compatible metric query |
| `process` | Check process is running via `pgrep` |

---

## Observability Integrations

| Integration | What it does |
|-------------|-------------|
| `prometheus` | Pushes experiment events and duration to Pushgateway |
| `datadog` | Fires Datadog events on start/end |
| `pagerduty` | Triggers PagerDuty alert on abort/failure |

---

## Experiment Lifecycle

```
validate config
  → check steady state (before)
    → inject faults (method)          ← circuit breaker monitors in background
      → execute rollbacks             ← always, regardless of outcome
        → verify steady state (after)
          → report
```

---

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/
mypy src/
```

---

## Architecture

```
src/kali/
├── cli/            # Typer CLI — run, validate, report
├── engine/         # ExperimentRunner — lifecycle orchestration
├── experiments/
│   ├── k_vortex.py     # K-Vortex: network latency + packet loss
│   ├── k_reaper.py     # K-Reaper: process/pod termination
│   ├── k_gravity.py    # K-Gravity: CPU + memory pressure
│   └── k_divide.py     # K-Divide: network partition + DNS faults
├── hypothesis/     # Steady-state probes (http, metric, process)
├── integrations/   # Prometheus, Datadog, PagerDuty
├── safety/         # Circuit breaker
└── models/         # Pydantic schemas
```

---

## Adding a new fault injector

1. Create `src/kali/experiments/k_<module>.py` implementing `FaultInjector`
2. Register it in `INJECTOR_REGISTRY` in `src/kali/experiments/__init__.py`
3. Add the new `ActionType` value in `models/experiment.py`
