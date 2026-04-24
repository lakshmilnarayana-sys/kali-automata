"""
Kali MCP Server — lets AI agents (Claude, etc.) run and manage chaos experiments.

Start with:
    python -m kali.mcp.server          # stdio transport (Claude Desktop)
    python -m kali.mcp.server --http   # HTTP transport (port 8765)

Claude Desktop config (~/.claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "kali": {
          "command": "python",
          "args": ["-m", "kali.mcp.server"],
          "cwd": "/path/to/chaos"
        }
      }
    }
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

from kali.engine.runner import ExperimentRunner
from kali.models.experiment import Experiment, ExperimentStatus

# ── MCP protocol primitives ───────────────────────────────────────────────────
# Minimal hand-rolled MCP server (JSON-RPC 2.0 over stdio).
# Drop-in replacement once `mcp` PyPI package stabilises.


TOOLS: list[Dict[str, Any]] = [
    {
        "name": "kali_run_experiment",
        "description": (
            "Run a Kali chaos experiment from a YAML file path. "
            "Returns the full result including resiliency score and probe outcomes. "
            "Always dry-run first unless the caller explicitly sets dry_run=false."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the experiment YAML file.",
                },
                "dry_run": {
                    "type": "boolean",
                    "default": True,
                    "description": "When true, validates and plans without injecting any faults.",
                },
            },
        },
    },
    {
        "name": "kali_validate_experiment",
        "description": "Validate a Kali experiment YAML string or file path without running it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to YAML file."},
                "yaml_content": {"type": "string", "description": "Raw YAML string to validate."},
            },
        },
    },
    {
        "name": "kali_list_experiments",
        "description": "List all experiment YAML files in the experiments/ directory.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "kali_explain_result",
        "description": (
            "Given a JSON experiment result, return a plain-English explanation "
            "including the resiliency score, grade, what failed, and recommended next steps."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["result_json"],
            "properties": {
                "result_json": {
                    "type": "string",
                    "description": "JSON string of an ExperimentResult.",
                },
            },
        },
    },
]


async def _run_experiment(path: str, dry_run: bool = True) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"error": f"File not found: {path}"}
    try:
        raw = yaml.safe_load(p.read_text())
        exp = Experiment.model_validate(raw)
        if dry_run:
            exp = exp.model_copy(update={"dry_run": True})
        runner = ExperimentRunner()
        result = await runner.run(exp)
        return json.loads(result.model_dump_json())
    except Exception as exc:
        return {"error": str(exc)}


def _validate_experiment(path: str | None = None, yaml_content: str | None = None) -> Dict[str, Any]:
    try:
        if yaml_content:
            raw = yaml.safe_load(yaml_content)
        elif path:
            raw = yaml.safe_load(Path(path).read_text())
        else:
            return {"valid": False, "error": "Provide either 'path' or 'yaml_content'"}
        exp = Experiment.model_validate(raw)
        return {
            "valid": True,
            "title": exp.title,
            "blast_radius": exp.blast_radius,
            "fault_count": len(exp.method),
            "probe_count": len(exp.steady_state_hypothesis.probes),
            "rollback_count": len(exp.rollbacks),
            "blast_blocked": exp.blast_radius >= 100,
        }
    except Exception as exc:
        return {"valid": False, "error": str(exc)}


def _list_experiments() -> Dict[str, Any]:
    experiments_dir = Path("experiments")
    if not experiments_dir.exists():
        return {"experiments": [], "note": "No experiments/ directory found"}
    files = sorted(experiments_dir.glob("*.yaml"))
    result = []
    for f in files:
        try:
            raw = yaml.safe_load(f.read_text())
            exp = Experiment.model_validate(raw)
            result.append({
                "path": str(f),
                "title": exp.title,
                "tags": exp.tags,
                "fault_types": [a.type.value for a in exp.method],
                "blast_radius": exp.blast_radius,
            })
        except Exception as exc:
            result.append({"path": str(f), "error": str(exc)})
    return {"experiments": result}


def _explain_result(result_json: str) -> Dict[str, Any]:
    from kali.models.experiment import ExperimentResult
    try:
        result = ExperimentResult.model_validate_json(result_json)
    except Exception as exc:
        return {"error": f"Could not parse result: {exc}"}

    score = result.resiliency_score
    lines = [
        f"Experiment: {result.experiment_title}",
        f"Status: {result.status.upper()}",
        f"Duration: {result.duration_seconds:.1f}s" if result.duration_seconds else "Duration: —",
        "",
    ]

    if score:
        lines += [
            f"Resiliency Score: {score.score}/100  (Grade {score.grade})",
            "Breakdown:",
            *[f"  {k}: {'+' if v >= 0 else ''}{v}" for k, v in score.breakdown.items()],
            "",
        ]

    after_failures = [p for p in result.steady_state_after if not p.passed]
    if after_failures:
        lines.append("Probes that failed after experiment:")
        for p in after_failures:
            lines.append(f"  ✗ {p.probe_name}: {p.error}")
        lines.append("")

    if result.abort_reason:
        lines.append(f"Abort reason: {result.abort_reason}")

    # Recommendations
    lines.append("Recommendations:")
    if result.status == ExperimentStatus.completed and (score and score.score >= 90):
        lines.append("  ✓ System demonstrated strong resilience. Consider increasing fault intensity.")
    elif result.status == ExperimentStatus.aborted:
        lines.append("  ! Circuit breaker tripped — investigate why probes failed mid-experiment.")
        lines.append("  ! Reduce blast radius or duration before re-running.")
    elif result.status == ExperimentStatus.failed:
        if after_failures:
            lines.append("  ! Steady state did not recover. Check your rollback configuration.")
        lines.append("  ! Review monitoring dashboards at the time of the experiment.")

    return {"explanation": "\n".join(lines)}


# ── JSON-RPC 2.0 stdio loop ───────────────────────────────────────────────────

async def _dispatch(method: str, params: Dict[str, Any]) -> Any:
    if method == "tools/list":
        return {"tools": TOOLS}

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})

        if name == "kali_run_experiment":
            return {"content": [{"type": "text", "text": json.dumps(
                await _run_experiment(args["path"], args.get("dry_run", True)),
                indent=2,
            )}]}

        if name == "kali_validate_experiment":
            return {"content": [{"type": "text", "text": json.dumps(
                _validate_experiment(args.get("path"), args.get("yaml_content")),
                indent=2,
            )}]}

        if name == "kali_list_experiments":
            return {"content": [{"type": "text", "text": json.dumps(
                _list_experiments(), indent=2,
            )}]}

        if name == "kali_explain_result":
            return {"content": [{"type": "text", "text": json.dumps(
                _explain_result(args["result_json"]), indent=2,
            )}]}

        return {"error": {"code": -32601, "message": f"Unknown tool: {name}"}}

    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "kali", "version": "0.1.0"},
        }

    return {"error": {"code": -32601, "message": f"Unknown method: {method}"}}


async def _stdio_loop() -> None:
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    loop = asyncio.get_event_loop()
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    writer_transport, writer_protocol = await loop.connect_write_pipe(
        asyncio.BaseProtocol, sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, loop)

    while True:
        line = await reader.readline()
        if not line:
            break
        try:
            msg = json.loads(line)
            result = await _dispatch(msg.get("method", ""), msg.get("params", {}))
            response = {"jsonrpc": "2.0", "id": msg.get("id"), "result": result}
        except Exception as exc:
            response = {
                "jsonrpc": "2.0",
                "id": msg.get("id"),
                "error": {"code": -32603, "message": str(exc)},
            }
        writer.write((json.dumps(response) + "\n").encode())
        await writer.drain()


if __name__ == "__main__":
    asyncio.run(_stdio_loop())
