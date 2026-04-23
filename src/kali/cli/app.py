"""Kali CLI — chaos engineering at your fingertips."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from kali.engine.runner import ExperimentRunner
from kali.models.experiment import Experiment, ExperimentStatus

app = typer.Typer(
    name="kali",
    help="Kali — chaos engineering toolkit. Run, validate, and report on fault-injection experiments.",
    no_args_is_help=True,
)
console = Console()


def _load_experiment(path: Path) -> Experiment:
    raw = yaml.safe_load(path.read_text())
    return Experiment.model_validate(raw)


@app.command()
def run(
    experiment_file: Path = typer.Argument(..., help="Path to experiment YAML"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Validate and plan without executing"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write JSON result to file"),
) -> None:
    """Run a chaos experiment."""
    if not experiment_file.exists():
        console.print(f"[red]File not found:[/red] {experiment_file}")
        raise typer.Exit(1)

    experiment = _load_experiment(experiment_file)
    if dry_run:
        experiment = experiment.model_copy(update={"dry_run": True})

    console.print(
        Panel.fit(
            f"[bold]{experiment.title}[/bold]\n"
            + (f"[dim]{experiment.description}[/dim]" if experiment.description else ""),
            title="[cyan]Kali[/cyan]",
            border_style="cyan",
        )
    )
    if experiment.dry_run:
        console.print("[yellow]DRY RUN — no faults will be injected[/yellow]\n")

    runner = ExperimentRunner()
    result = asyncio.run(runner.run(experiment))

    # Status panel
    colour = {
        ExperimentStatus.completed: "green",
        ExperimentStatus.aborted: "yellow",
        ExperimentStatus.failed: "red",
        ExperimentStatus.running: "blue",
        ExperimentStatus.pending: "dim",
    }.get(result.status, "white")

    console.print(
        Panel.fit(
            f"[{colour}]{result.status.upper()}[/{colour}]"
            + (f"\n[dim]{result.abort_reason}[/dim]" if result.abort_reason else ""),
            title="Result",
        )
    )

    # Probe table
    _render_probe_table("Steady State — Before", result.steady_state_before)
    _render_probe_table("Steady State — After", result.steady_state_after)

    if output:
        output.write_text(result.model_dump_json(indent=2))
        console.print(f"\n[dim]Result written to {output}[/dim]")

    raise typer.Exit(0 if result.status == ExperimentStatus.completed else 1)


@app.command()
def validate(
    experiment_file: Path = typer.Argument(..., help="Path to experiment YAML"),
) -> None:
    """Validate an experiment definition without running it."""
    if not experiment_file.exists():
        console.print(f"[red]File not found:[/red] {experiment_file}")
        raise typer.Exit(1)
    try:
        exp = _load_experiment(experiment_file)
        console.print(f"[green]Valid[/green] — {exp.title}")
        console.print(f"  Probes  : {len(exp.steady_state_hypothesis.probes)}")
        console.print(f"  Actions : {len(exp.method)}")
        console.print(f"  Rollbacks: {len(exp.rollbacks)}")
    except Exception as exc:
        console.print(f"[red]Invalid:[/red] {exc}")
        raise typer.Exit(1)


@app.command()
def report(
    result_file: Path = typer.Argument(..., help="Path to JSON result file from a previous run"),
) -> None:
    """Display a formatted report from a saved experiment result."""
    from kali.models.experiment import ExperimentResult
    if not result_file.exists():
        console.print(f"[red]File not found:[/red] {result_file}")
        raise typer.Exit(1)
    result = ExperimentResult.model_validate_json(result_file.read_text())
    console.print(Panel.fit(f"[bold]{result.experiment_title}[/bold]", title="Kali Report"))
    console.print(f"Status   : {result.status}")
    console.print(f"Duration : {result.duration_seconds:.1f}s" if result.duration_seconds else "Duration : —")
    _render_probe_table("Steady State — Before", result.steady_state_before)
    _render_probe_table("Steady State — After", result.steady_state_after)


def _render_probe_table(title: str, probes: list) -> None:  # type: ignore[type-arg]
    if not probes:
        return
    table = Table(title=title, box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Probe")
    table.add_column("Passed")
    table.add_column("Value")
    table.add_column("Error")
    for p in probes:
        table.add_row(
            p.probe_name,
            "[green]yes[/green]" if p.passed else "[red]no[/red]",
            str(p.value or ""),
            p.error or "",
        )
    console.print(table)
