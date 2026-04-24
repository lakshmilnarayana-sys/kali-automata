import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, RunDetail as RunDetailType } from "../api";
import { ScoreBadge, StatusBadge } from "../components/ScoreBadge";

function ProbeRow({ name, passed, value, error }: {
  name: string; passed: boolean; value: unknown; error: string | null;
}) {
  return (
    <div className={`flex items-start gap-2 py-1.5 border-b border-gray-900 last:border-0`}>
      <span className={`mt-0.5 text-sm shrink-0 ${passed ? "text-emerald-400" : "text-red-400"}`}>
        {passed ? "✓" : "✗"}
      </span>
      <div className="min-w-0">
        <div className="text-sm text-gray-300 font-mono">{name}</div>
        {value !== null && value !== undefined && (
          <div className="text-[11px] text-gray-500 mt-0.5">
            value: <span className="text-gray-400">{String(value)}</span>
          </div>
        )}
        {error && <div className="text-[11px] text-red-500 mt-0.5">{error}</div>}
      </div>
    </div>
  );
}

function ActionRow({ name, success, output, error, started_at, ended_at }: {
  name: string; success: boolean; output: string | null;
  error: string | null; started_at: string; ended_at: string;
}) {
  const dur = ((new Date(ended_at).getTime() - new Date(started_at).getTime()) / 1000).toFixed(1);
  return (
    <div className="flex items-start gap-2 py-1.5 border-b border-gray-900 last:border-0">
      <span className={`mt-0.5 text-sm shrink-0 ${success ? "text-emerald-400" : "text-red-400"}`}>
        {success ? "✓" : "✗"}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-300 font-mono">{name}</span>
          <span className="text-[10px] text-gray-600">{dur}s</span>
        </div>
        {output && <div className="text-[11px] text-gray-500 mt-0.5 font-mono break-all">{output}</div>}
        {error && <div className="text-[11px] text-red-500 mt-0.5">{error}</div>}
      </div>
    </div>
  );
}

function Section({ title, children, count }: {
  title: string; children: React.ReactNode; count?: number;
}) {
  return (
    <div className="bg-[#0f1117] border border-gray-800 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[11px] text-gray-500 uppercase tracking-widest">{title}</span>
        {count !== undefined && (
          <span className="text-[10px] bg-gray-800 text-gray-500 rounded-full px-1.5">{count}</span>
        )}
      </div>
      {children}
    </div>
  );
}

export function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [run, setRun] = useState<RunDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api.runs.get(id)
      .then(setRun)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-600">Loading…</div>
    );
  }

  if (error || !run) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 text-red-500">
        <span className="text-4xl">⚠️</span>
        <span>{error ?? "Run not found"}</span>
        <button onClick={() => nav(-1)} className="text-sm text-gray-400 hover:text-gray-200">← Go back</button>
      </div>
    );
  }

  const r = run.result;
  const score = r.resiliency_score;
  const dur = r.started_at && r.ended_at
    ? ((new Date(r.ended_at).getTime() - new Date(r.started_at).getTime()) / 1000).toFixed(1)
    : null;

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">

      {/* Header */}
      <div className="flex items-start gap-3">
        <button
          onClick={() => nav(-1)}
          className="text-gray-500 hover:text-gray-200 transition-colors mt-0.5 shrink-0"
        >
          ←
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-gray-100 truncate">{r.experiment_title}</h1>
          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            <StatusBadge status={r.status} />
            <ScoreBadge score={score?.score ?? null} grade={score?.grade ?? null} size="md" />
            {r.dry_run && (
              <span className="text-[10px] border border-yellow-800 text-yellow-600 rounded px-1.5 py-0.5">dry-run</span>
            )}
            {dur && <span className="text-xs text-gray-500 font-mono">{dur}s</span>}
            <span className="text-xs text-gray-600">Blast radius: {r.blast_radius}%</span>
          </div>
          {r.abort_reason && (
            <div className="mt-2 text-sm text-red-400 bg-red-950/30 border border-red-900 rounded px-3 py-2">
              {r.abort_reason}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">

        {/* Steady state before */}
        <Section title="Steady State — Before" count={r.steady_state_before.length}>
          {r.steady_state_before.length === 0
            ? <span className="text-sm text-gray-600">No probes recorded</span>
            : r.steady_state_before.map((p) => (
                <ProbeRow key={p.probe_name} name={p.probe_name} passed={p.passed} value={p.value} error={p.error} />
              ))
          }
        </Section>

        {/* Steady state after */}
        <Section title="Steady State — After" count={r.steady_state_after.length}>
          {r.steady_state_after.length === 0
            ? <span className="text-sm text-gray-600">No probes recorded</span>
            : r.steady_state_after.map((p) => (
                <ProbeRow key={p.probe_name} name={p.probe_name} passed={p.passed} value={p.value} error={p.error} />
              ))
          }
        </Section>

        {/* Actions */}
        <Section title="Method — Actions" count={r.actions.length}>
          {r.actions.length === 0
            ? <span className="text-sm text-gray-600">No actions executed</span>
            : r.actions.map((a) => (
                <ActionRow key={a.action_name} name={a.action_name} success={a.success} output={a.output} error={a.error} started_at={a.started_at} ended_at={a.ended_at} />
              ))
          }
        </Section>

        {/* Rollbacks */}
        <Section title="Rollbacks" count={r.rollbacks_executed.length}>
          {r.rollbacks_executed.length === 0
            ? <span className="text-sm text-gray-600">No rollbacks executed</span>
            : r.rollbacks_executed.map((a) => (
                <ActionRow key={a.action_name} name={a.action_name} success={a.success} output={a.output} error={a.error} started_at={a.started_at} ended_at={a.ended_at} />
              ))
          }
        </Section>

      </div>

      {/* Score breakdown */}
      {score && (
        <Section title="Resiliency Score Breakdown">
          <div className="flex items-center gap-4 mb-4">
            <ScoreBadge score={score.score} grade={score.grade} size="lg" />
            <div>
              <div className="text-gray-400 text-sm">Grade {score.grade}</div>
              <div className="text-gray-600 text-xs mt-0.5">
                {score.score >= 90 ? "Excellent resilience demonstrated" :
                 score.score >= 80 ? "Good resilience, minor gaps" :
                 score.score >= 70 ? "Acceptable — some probes struggled" :
                 score.score >= 60 ? "Below target — investigate failures" :
                 "Poor resilience — immediate investigation needed"}
              </div>
            </div>
          </div>

          <div className="space-y-2">
            {Object.entries(score.breakdown).map(([key, val]) => {
              const isNeg = val < 0;
              const pct = Math.abs(val);
              return (
                <div key={key} className="flex items-center gap-3">
                  <div className="text-[11px] text-gray-500 w-48 shrink-0 capitalize">
                    {key.replace(/_/g, " ")}
                  </div>
                  <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${isNeg ? "bg-red-500" : "bg-emerald-500"}`}
                      style={{ width: `${Math.min(pct, 60)}%` }}
                    />
                  </div>
                  <div className={`text-xs font-mono w-10 text-right ${isNeg ? "text-red-400" : "text-emerald-400"}`}>
                    {val > 0 ? "+" : ""}{val}
                  </div>
                </div>
              );
            })}
          </div>
        </Section>
      )}

    </div>
  );
}
