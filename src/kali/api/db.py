"""SQLite persistence layer for experiment run history."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

DB_PATH = Path(os.environ.get("KALI_DB", ".kali/runs.db"))


async def _connect() -> aiosqlite.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db() -> None:
    async with await _connect() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id              TEXT PRIMARY KEY,
                experiment_title TEXT NOT NULL,
                experiment_file  TEXT,
                status           TEXT NOT NULL,
                blast_radius     INTEGER DEFAULT 50,
                score            INTEGER,
                grade            TEXT,
                dry_run          INTEGER DEFAULT 0,
                started_at       TEXT,
                ended_at         TEXT,
                duration_seconds REAL,
                abort_reason     TEXT,
                result_json      TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at DESC)
        """)
        await db.commit()


async def save_run(result_json: str, experiment_file: Optional[str] = None) -> str:
    data = json.loads(result_json)
    run_id = str(uuid.uuid4())
    score_obj = data.get("resiliency_score") or {}

    async with await _connect() as db:
        await db.execute(
            """
            INSERT INTO runs
              (id, experiment_title, experiment_file, status, blast_radius,
               score, grade, dry_run, started_at, ended_at, duration_seconds,
               abort_reason, result_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                run_id,
                data.get("experiment_title", "unknown"),
                experiment_file,
                data.get("status", "unknown"),
                data.get("blast_radius", 50),
                score_obj.get("score"),
                score_obj.get("grade"),
                1 if data.get("dry_run") else 0,
                data.get("started_at"),
                data.get("ended_at"),
                data.get("duration_seconds"),  # computed client-side via property
                data.get("abort_reason"),
                result_json,
            ),
        )
        await db.commit()
    return run_id


async def list_runs(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    async with await _connect() as db:
        where = "WHERE status = ?" if status else ""
        params = [status, limit, offset] if status else [limit, offset]
        async with db.execute(
            f"""
            SELECT id, experiment_title, experiment_file, status, blast_radius,
                   score, grade, dry_run, started_at, ended_at, duration_seconds, abort_reason
            FROM runs {where}
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    async with await _connect() as db:
        async with db.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    result = dict(row)
    result["result"] = json.loads(result.pop("result_json"))
    return result


async def get_stats() -> Dict[str, Any]:
    async with await _connect() as db:
        async with db.execute(
            "SELECT COUNT(*) as total, AVG(score) as avg_score FROM runs"
        ) as cur:
            totals = dict(await cur.fetchone())

        async with db.execute(
            """
            SELECT COUNT(*) as count FROM runs
            WHERE started_at >= datetime('now', '-7 days')
            """
        ) as cur:
            week = dict(await cur.fetchone())

        async with db.execute(
            """
            SELECT COUNT(*) as passed FROM runs
            WHERE status = 'completed'
            """
        ) as cur:
            passed = dict(await cur.fetchone())

        async with db.execute(
            """
            SELECT grade, COUNT(*) as count FROM runs
            WHERE grade IS NOT NULL
            GROUP BY grade
            """
        ) as cur:
            grade_rows = await cur.fetchall()

        async with db.execute(
            """
            SELECT date(started_at) as day, AVG(score) as avg_score, COUNT(*) as runs
            FROM runs
            WHERE started_at >= datetime('now', '-30 days') AND score IS NOT NULL
            GROUP BY day
            ORDER BY day
            """
        ) as cur:
            trend_rows = await cur.fetchall()

    total = totals["total"] or 0
    return {
        "total_runs": total,
        "avg_score": round(totals["avg_score"] or 0, 1),
        "pass_rate": round((passed["passed"] / total * 100) if total else 0, 1),
        "runs_this_week": week["count"],
        "grade_distribution": {r["grade"]: r["count"] for r in grade_rows},
        "score_trend": [
            {"day": r["day"], "avg_score": round(r["avg_score"], 1), "runs": r["runs"]}
            for r in trend_rows
        ],
    }
