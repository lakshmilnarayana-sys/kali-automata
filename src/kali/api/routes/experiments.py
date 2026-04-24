"""Experiment file listing and validation endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml
from fastapi import APIRouter, HTTPException

from kali.models.experiment import Experiment

router = APIRouter(tags=["experiments"])
EXPERIMENTS_DIR = Path("experiments")


@router.get("/experiments", response_model=List[Dict[str, Any]])
async def list_experiments() -> List[Dict[str, Any]]:
    if not EXPERIMENTS_DIR.exists():
        return []
    results = []
    for f in sorted(EXPERIMENTS_DIR.glob("*.yaml")):
        try:
            raw = yaml.safe_load(f.read_text())
            exp = Experiment.model_validate(raw)
            results.append({
                "path": str(f),
                "title": exp.title,
                "description": exp.description,
                "tags": exp.tags,
                "blast_radius": exp.blast_radius,
                "blast_blocked": exp.blast_radius >= 100,
                "fault_types": [a.type.value for a in exp.method],
                "probe_count": len(exp.steady_state_hypothesis.probes),
                "rollback_count": len(exp.rollbacks),
                "dry_run": exp.dry_run,
            })
        except Exception as exc:
            results.append({"path": str(f), "error": str(exc)})
    return results


@router.get("/experiments/validate")
async def validate_experiment(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    try:
        raw = yaml.safe_load(p.read_text())
        exp = Experiment.model_validate(raw)
        return {
            "valid": True,
            "title": exp.title,
            "blast_radius": exp.blast_radius,
            "blast_blocked": exp.blast_radius >= 100,
            "fault_count": len(exp.method),
            "probe_count": len(exp.steady_state_hypothesis.probes),
        }
    except Exception as exc:
        return {"valid": False, "error": str(exc)}
