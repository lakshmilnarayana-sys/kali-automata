# KALI — Kinetic Automated Load and Infrastructure

> Controlled Instability. Indestructible Infrastructure.

## Project

Python CLI toolkit for chaos engineering: fault injection via named modules (K-Vortex, K-Reaper, K-Gravity, K-Divide), steady-state verification, circuit breaker, and observability integrations.

Repository: https://github.com/lakshmilnarayana-sys/kali-automata

## Stack

- Python 3.9+, packaged with `hatchling` via `pyproject.toml`
- **CLI**: Typer + Rich
- **Models**: Pydantic v2
- **Async**: asyncio
- **HTTP**: httpx
- **Config**: PyYAML

## Module Map

| Module | File | Types |
|--------|------|-------|
| K-Vortex | `experiments/k_vortex.py` | `network/latency`, `network/loss` |
| K-Reaper | `experiments/k_reaper.py` | `process/kill` |
| K-Gravity | `experiments/k_gravity.py` | `cpu/stress`, `memory/stress` |
| K-Divide | `experiments/k_divide.py` | `network/partition`, `network/dns-fault` |

## Structure

```
src/kali/
├── cli/app.py              # Typer entry point — commands: run, validate, report
├── engine/runner.py        # ExperimentRunner — full lifecycle orchestration
├── experiments/            # Fault injectors; INJECTOR_REGISTRY in __init__.py
├── hypothesis/probes.py    # Steady-state probes: http, metric, process
├── integrations/           # Prometheus, Datadog, PagerDuty — all non-fatal
├── safety/circuit_breaker.py
└── models/experiment.py    # All Pydantic schemas
```

## Key conventions

- All injectors implement `FaultInjector` ABC: `inject()` + `rollback()`
- All integrations implement `ObservabilityIntegration` ABC: `on_experiment_start/end/abort()`
- Integration failures are silenced — observability must never block experiments
- `dry_run=True` skips all syscalls; use for CI validation
- YAML type strings (e.g. `network/latency`) are stable public API

## Dev commands

```bash
pip install -e ".[dev]"
pytest
pytest tests/unit/           # fast, no network
ruff check src/
mypy src/
kali validate experiments/network-latency.yaml
kali run experiments/k-divide-dns.yaml --dry-run
```

## Adding a new fault injector

1. Create `src/kali/experiments/k_<module>.py` implementing `FaultInjector`
2. Add to `INJECTOR_REGISTRY` in `src/kali/experiments/__init__.py`
3. Add a new `ActionType` enum value in `models/experiment.py`

## Adding a new integration

1. Create `src/kali/integrations/yourservice.py` implementing `ObservabilityIntegration`
2. Export from `src/kali/integrations/__init__.py`
