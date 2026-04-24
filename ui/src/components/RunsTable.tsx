import { useNavigate } from "react-router-dom";
import { RunSummary } from "../api";
import { ScoreBadge, StatusBadge } from "./ScoreBadge";

interface Props {
  runs: RunSummary[];
  loading?: boolean;
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function dur(s: number | null): string {
  if (s === null || s === undefined) return "—";
  return s < 60 ? `${s.toFixed(1)}s` : `${(s / 60).toFixed(1)}m`;
}

export function RunsTable({ runs, loading }: Props) {
  const nav = useNavigate();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-600 text-sm">
        Loading runs…
      </div>
    );
  }

  if (!runs.length) {
    return (
      <div className="flex flex-col items-center justify-center h-32 text-gray-600 text-sm gap-2">
        <span className="text-2xl">🌱</span>
        <span>No runs yet — trigger one from the Builder or CLI.</span>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-[10px] text-gray-500 uppercase tracking-widest">
            <th className="text-left py-2 px-3">Experiment</th>
            <th className="text-left py-2 px-3">Status</th>
            <th className="text-left py-2 px-3">Score</th>
            <th className="text-left py-2 px-3 hidden md:table-cell">Duration</th>
            <th className="text-left py-2 px-3 hidden lg:table-cell">Dry run</th>
            <th className="text-left py-2 px-3">Started</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr
              key={r.id}
              onClick={() => nav(`/runs/${r.id}`)}
              className="border-b border-gray-900 hover:bg-white/[0.03] cursor-pointer transition-colors"
            >
              <td className="py-2.5 px-3">
                <div className="font-medium text-gray-200 truncate max-w-[220px]">{r.experiment_title}</div>
                {r.abort_reason && (
                  <div className="text-[10px] text-red-500 truncate max-w-[220px] mt-0.5">{r.abort_reason}</div>
                )}
              </td>
              <td className="py-2.5 px-3"><StatusBadge status={r.status} /></td>
              <td className="py-2.5 px-3"><ScoreBadge score={r.score} grade={r.grade} /></td>
              <td className="py-2.5 px-3 hidden md:table-cell text-gray-400 font-mono text-xs">{dur(r.duration_seconds)}</td>
              <td className="py-2.5 px-3 hidden lg:table-cell">
                {r.dry_run
                  ? <span className="text-[10px] text-yellow-600 border border-yellow-800 rounded px-1.5 py-0.5">dry</span>
                  : <span className="text-[10px] text-emerald-600 border border-emerald-800 rounded px-1.5 py-0.5">live</span>
                }
              </td>
              <td className="py-2.5 px-3 text-gray-500 text-xs">{fmt(r.started_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
