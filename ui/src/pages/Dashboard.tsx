import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ExperimentFile, RunSummary, Stats } from "../api";
import { StatCard } from "../components/StatCard";
import { RunsTable } from "../components/RunsTable";
import { ScoreTrendChart, GradeDistChart } from "../components/ScoreTrend";

export function Dashboard() {
  const nav = useNavigate();
  const [stats, setStats] = useState<Stats | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [experiments, setExperiments] = useState<ExperimentFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiDown, setApiDown] = useState(false);
  const [triggering, setTriggering] = useState<string | null>(null);

  async function load() {
    try {
      const [s, r, e] = await Promise.all([
        api.runs.stats(),
        api.runs.list({ limit: 10 }),
        api.experiments.list(),
      ]);
      setStats(s);
      setRuns(r);
      setExperiments(e.filter((ex) => !ex.error));
      setApiDown(false);
    } catch {
      setApiDown(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function triggerRun(path: string, dryRun: boolean) {
    setTriggering(path);
    try {
      const result = await api.runs.create(path, dryRun);
      nav(`/runs/${result.id}`);
    } catch (err) {
      alert(`Run failed: ${err instanceof Error ? err.message : err}`);
    } finally {
      setTriggering(null);
    }
  }

  const gradeDist = stats
    ? Object.entries(stats.grade_distribution).map(([grade, count]) => ({ grade, count }))
    : [];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">

      {apiDown && (
        <div className="bg-yellow-950/40 border border-yellow-800 rounded-lg px-4 py-3 text-yellow-400 text-sm flex items-center gap-2">
          <span>⚠️</span>
          <span>
            API server not reachable. Start it with{" "}
            <code className="font-mono bg-black/30 px-1 rounded">kali serve</code>{" "}
            then refresh.
          </span>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Total runs"
          value={loading ? "…" : (stats?.total_runs ?? 0)}
          icon="🧪"
          accent="text-blue-400"
        />
        <StatCard
          label="Avg resiliency score"
          value={loading ? "…" : `${stats?.avg_score ?? 0}/100`}
          icon="📊"
          accent="text-amber-400"
        />
        <StatCard
          label="Pass rate"
          value={loading ? "…" : `${stats?.pass_rate ?? 0}%`}
          sub="experiments where steady state held"
          icon="✅"
          accent="text-emerald-400"
        />
        <StatCard
          label="This week"
          value={loading ? "…" : (stats?.runs_this_week ?? 0)}
          sub="runs in the last 7 days"
          icon="📅"
          accent="text-purple-400"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 bg-[#0f1117] border border-gray-800 rounded-lg p-4">
          <div className="text-[11px] text-gray-500 uppercase tracking-widest mb-3">
            Score Trend · last 30 days
          </div>
          <div className="h-48">
            <ScoreTrendChart data={stats?.score_trend ?? []} />
          </div>
        </div>
        <div className="bg-[#0f1117] border border-gray-800 rounded-lg p-4">
          <div className="text-[11px] text-gray-500 uppercase tracking-widest mb-3">
            Grade Distribution
          </div>
          <div className="h-48">
            <GradeDistChart data={gradeDist} />
          </div>
        </div>
      </div>

      {/* Quick-run experiments */}
      {experiments.length > 0 && (
        <div className="bg-[#0f1117] border border-gray-800 rounded-lg p-4">
          <div className="text-[11px] text-gray-500 uppercase tracking-widest mb-3">
            Quick Run
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
            {experiments.map((ex) => (
              <div
                key={ex.path}
                className="border border-gray-800 rounded-lg p-3 flex flex-col gap-2 hover:border-gray-700 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-medium text-gray-200 leading-tight">{ex.title}</div>
                    <div className="text-[10px] text-gray-600 mt-0.5 font-mono truncate">{ex.path}</div>
                  </div>
                  {ex.blast_blocked && (
                    <span className="text-[10px] shrink-0 bg-red-900/40 border border-red-800 text-red-400 rounded px-1.5 py-0.5">
                      BLOCKED
                    </span>
                  )}
                </div>
                {ex.fault_types && (
                  <div className="flex flex-wrap gap-1">
                    {ex.fault_types.map((t) => (
                      <span key={t} className="text-[9px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 font-mono">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex gap-2 mt-auto pt-1">
                  <button
                    disabled={!!triggering || ex.blast_blocked}
                    onClick={() => triggerRun(ex.path!, true)}
                    className="flex-1 text-[11px] py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors disabled:opacity-40"
                  >
                    {triggering === ex.path ? "Running…" : "Dry run"}
                  </button>
                  <button
                    disabled={!!triggering || !!ex.blast_blocked}
                    onClick={() => triggerRun(ex.path!, false)}
                    className="flex-1 text-[11px] py-1 rounded bg-blue-900/50 hover:bg-blue-800/50 text-blue-300 transition-colors disabled:opacity-40"
                  >
                    {triggering === ex.path ? "Running…" : "▶ Run"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent runs */}
      <div className="bg-[#0f1117] border border-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="text-[11px] text-gray-500 uppercase tracking-widest">Recent Runs</div>
          <button
            onClick={() => nav("/runs")}
            className="text-[11px] text-blue-400 hover:text-blue-300 transition-colors"
          >
            View all →
          </button>
        </div>
        <RunsTable runs={runs} loading={loading && !apiDown} />
      </div>

    </div>
  );
}
