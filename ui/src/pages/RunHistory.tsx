import { useEffect, useState } from "react";
import { api, RunSummary } from "../api";
import { RunsTable } from "../components/RunsTable";

const STATUS_OPTIONS = ["", "completed", "aborted", "failed"];

export function RunHistory() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const PER_PAGE = 25;

  useEffect(() => {
    setLoading(true);
    api.runs
      .list({ limit: PER_PAGE, offset: page * PER_PAGE, status: status || undefined })
      .then(setRuns)
      .catch(() => setRuns([]))
      .finally(() => setLoading(false));
  }, [status, page]);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-100">Run History</h1>

        <div className="flex items-center gap-2">
          <span className="text-[11px] text-gray-500">Filter:</span>
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s || "all"}
              onClick={() => { setStatus(s); setPage(0); }}
              className={`text-[11px] px-2.5 py-1 rounded border transition-colors ${
                status === s
                  ? "border-blue-600 bg-blue-900/40 text-blue-300"
                  : "border-gray-700 text-gray-500 hover:text-gray-300"
              }`}
            >
              {s || "All"}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-[#0f1117] border border-gray-800 rounded-lg p-4">
        <RunsTable runs={runs} loading={loading} />
      </div>

      {runs.length === PER_PAGE && (
        <div className="flex justify-end">
          <button
            onClick={() => setPage((p) => p + 1)}
            className="text-[11px] px-3 py-1.5 rounded border border-gray-700 text-gray-400 hover:text-gray-200 transition-colors"
          >
            Next page →
          </button>
        </div>
      )}

      {page > 0 && (
        <div className="flex justify-start">
          <button
            onClick={() => setPage((p) => p - 1)}
            className="text-[11px] px-3 py-1.5 rounded border border-gray-700 text-gray-400 hover:text-gray-200 transition-colors"
          >
            ← Previous page
          </button>
        </div>
      )}
    </div>
  );
}
