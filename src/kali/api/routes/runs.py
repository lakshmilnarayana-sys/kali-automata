"""Run history and experiment execution endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from kali.api.db import get_run, get_stats, list_runs, save_run
from kali.engine.runner import ExperimentRunner
from kali.models.experiment import Experiment

router = APIRouter(tags=["runs"])


class RunRequest(BaseModel):
    path: str
    dry_run: bool = True


@router.post("/runs", response_model=Dict[str, Any])
async def create_run(req: RunRequest) -> Dict[str, Any]:
    """Trigger an experiment run. Blocks until complete (dry-runs finish fast)."""
    p = Path(req.path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Experiment file not found: {req.path}")

    try:
        raw = yaml.safe_load(p.read_text())
        exp = Experiment.model_validate(raw)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid experiment YAML: {exc}")

    if req.dry_run:
        exp = exp.model_copy(update={"dry_run": True})

    runner = ExperimentRunner()
    result = await runner.run(exp)

    result_json = result.model_dump_json()
    run_id = await save_run(result_json, experiment_file=req.path)

    data = result.model_dump()
    data["id"] = run_id
    return data


@router.get("/runs", response_model=List[Dict[str, Any]])
async def get_runs(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return await list_runs(limit=limit, offset=offset, status=status)


@router.get("/runs/stats", response_model=Dict[str, Any])
async def run_stats() -> Dict[str, Any]:
    return await get_stats()


@router.get("/runs/{run_id}", response_model=Dict[str, Any])
async def get_run_detail(run_id: str) -> Dict[str, Any]:
    row = await get_run(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return row
