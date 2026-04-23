# Kali — Chaos Engineering Toolkit

## Project

Python CLI tool for chaos engineering: fault injection, steady-state verification, observability integrations.

## Stack

- Python 3.9+, packaged with `hatchling` via `pyproject.toml`
- **CLI**: Typer + Rich
- **Models**: Pydantic v2
- **Async**: asyncio / anyio
- **HTTP**: httpx
- **Config**: PyYAML

## Structure

```
src/kali/
├── cli/app.py          # Typer entry point — commands: run, validate, report
├── engine/runner.py    # ExperimentRunner — full lifecycle orchestration
├── experiments/        # Fault injectors (network, cpu, process); registry in __init__.py
├── hypothesis/probes.py # Steady-state probes: http, metric, process
├── integrations/       # Prometheus, Datadog, PagerDuty — all non-fatal (never block experiments)
├── safety/circuit_breaker.py  # Auto-abort on N consecutive probe failures
└── models/experiment.py       # All Pydantic schemas
```

## Key conventions

- Fault injectors live in `src/kali/experiments/` and register in `INJECTOR_REGISTRY` (`experiments/__init__.py`)
- All injectors implement `FaultInjector` ABC: `inject()` + `rollback()`
- Observability integrations implement `ObservabilityIntegration` ABC: `on_experiment_start/end/abort()`
- Integration failures are silenced — observability must never block experiment execution
- `dry_run=True` skips all syscalls; use for CI validation
- Experiment YAML schema is defined by `Experiment` Pydantic model

## Dev commands

```bash
pip install -e ".[dev]"
pytest                  # run all tests
pytest tests/unit/      # unit only (fast, no network)
ruff check src/         # lint
mypy src/               # type check
kali validate experiments/network-latency.yaml
kali run experiments/network-latency.yaml --dry-run
```

## Adding a new fault injector

1. Create `src/kali/experiments/yourtype.py` implementing `FaultInjector`
2. Add to `INJECTOR_REGISTRY` in `src/kali/experiments/__init__.py`
3. Add a new `ActionType` enum value in `models/experiment.py`

## Adding a new integration

1. Create `src/kali/integrations/yourservice.py` implementing `ObservabilityIntegration`
2. Export from `src/kali/integrations/__init__.py`
