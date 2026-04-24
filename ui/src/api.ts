/** Typed API client — all calls proxied via Vite to http://localhost:8000 */

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface RunSummary {
  id: string;
  experiment_title: string;
  experiment_file: string | null;
  status: "completed" | "aborted" | "failed" | "running" | "pending";
  blast_radius: number;
  score: number | null;
  grade: string | null;
  dry_run: boolean;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  abort_reason: string | null;
}

export interface ProbeResult {
  probe_name: string;
  passed: boolean;
  value: unknown;
  error: string | null;
  timestamp: string;
}

export interface ActionResult {
  action_name: string;
  success: boolean;
  output: string | null;
  error: string | null;
  started_at: string;
  ended_at: string;
}

export interface ResiliencyScore {
  score: number;
  grade: string;
  breakdown: Record<string, number>;
}

export interface RunDetail extends RunSummary {
  result: {
    experiment_title: string;
    status: string;
    dry_run: boolean;
    blast_radius: number;
    started_at: string | null;
    ended_at: string | null;
    steady_state_before: ProbeResult[];
    steady_state_after: ProbeResult[];
    actions: ActionResult[];
    rollbacks_executed: ActionResult[];
    abort_reason: string | null;
    resiliency_score: ResiliencyScore | null;
  };
}

export interface ExperimentFile {
  path: string;
  title?: string;
  description?: string;
  tags?: string[];
  blast_radius?: number;
  blast_blocked?: boolean;
  fault_types?: string[];
  probe_count?: number;
  rollback_count?: number;
  error?: string;
}

export interface Stats {
  total_runs: number;
  avg_score: number;
  pass_rate: number;
  runs_this_week: number;
  grade_distribution: Record<string, number>;
  score_trend: { day: string; avg_score: number; runs: number }[];
}

// ── API calls ─────────────────────────────────────────────────────────────────

export const api = {
  runs: {
    list: (params?: { limit?: number; offset?: number; status?: string }) => {
      const q = new URLSearchParams();
      if (params?.limit)  q.set("limit",  String(params.limit));
      if (params?.offset) q.set("offset", String(params.offset));
      if (params?.status) q.set("status", params.status);
      return get<RunSummary[]>(`/runs?${q}`);
    },
    get: (id: string) => get<RunDetail>(`/runs/${id}`),
    stats: () => get<Stats>("/runs/stats"),
    create: (path: string, dry_run: boolean) =>
      post<RunSummary & { id: string }>("/runs", { path, dry_run }),
  },
  experiments: {
    list: () => get<ExperimentFile[]>("/experiments"),
    validate: (path: string) => get<Record<string, unknown>>(`/experiments/validate?path=${encodeURIComponent(path)}`),
  },
  health: () => get<{ status: string }>("/health"),
};
