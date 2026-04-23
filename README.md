# Kali

**Chaos engineering toolkit** — fault injection, steady-state verification, and observability integrations.

Named after the Hindu goddess of destruction and transformation.

---

## Concepts

Kali follows the [Principles of Chaos Engineering](https://principlesofchaos.org/):

1. **Steady-State Hypothesis** — define what "healthy" looks like via probes (HTTP, metric, process)
2. **Method** — inject faults (network latency/loss, CPU stress, process kill)
3. **Circuit Breaker** — auto-abort if health degrades beyond threshold mid-experiment
4. **Rollback** — always clean up, regardless of outcome
5. **Verify** — confirm the system recovered to steady state

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

# Dry run (no faults injected)
kali run experiments/network-latency.yaml --dry-run

# Run live
kali run experiments/cpu-stress.yaml

# Save result to file and view report later
kali run experiments/network-latency.yaml --output results/run-001.json
kali report results/run-001.json
```

---

## Experiment Format

```yaml
version: "1.0.0"
title: "API survives 500ms network latency"
description: "Optional human-readable description"
tags: [network, api]

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
    type: network/latency
    duration: 60          # seconds
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

## Fault Types

| Type | Description | Required `provider` keys |
|------|-------------|--------------------------|
| `network/latency` | Add delay via `tc netem` | `interface`, `delay_ms`, `jitter_ms` |
| `network/loss` | Drop packets via `tc netem` | `interface`, `loss_percent` |
| `cpu/stress` | Burn CPU cores via `stress-ng` | `workers`, `load_percent` |
| `process/kill` | Send signal to process | `process` OR `pid`, `signal` |

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
| `prometheus` | Pushes experiment events/duration to Pushgateway |
| `datadog` | Fires Datadog events on start/end |
| `pagerduty` | Triggers PagerDuty alert on abort/failure |

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
├── cli/          # Typer CLI — run, validate, report
├── engine/       # Experiment runner & lifecycle orchestration
├── experiments/  # Fault injectors (network, cpu, process, …)
├── hypothesis/   # Steady-state probes
├── integrations/ # Observability integrations
├── safety/       # Circuit breaker
└── models/       # Pydantic schemas
```
