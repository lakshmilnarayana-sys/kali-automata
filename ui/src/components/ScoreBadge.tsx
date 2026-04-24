interface Props {
  score: number | null;
  grade: string | null;
  size?: "sm" | "md" | "lg";
}

const gradeColour: Record<string, string> = {
  A: "text-emerald-400 border-emerald-700 bg-emerald-900/30",
  B: "text-cyan-400    border-cyan-700    bg-cyan-900/30",
  C: "text-yellow-400  border-yellow-700  bg-yellow-900/30",
  D: "text-orange-400  border-orange-700  bg-orange-900/30",
  F: "text-red-400     border-red-700     bg-red-900/30",
};

const statusColour: Record<string, string> = {
  completed: "text-emerald-400 border-emerald-700 bg-emerald-900/20",
  aborted:   "text-yellow-400  border-yellow-700  bg-yellow-900/20",
  failed:    "text-red-400     border-red-700     bg-red-900/20",
  running:   "text-blue-400    border-blue-700    bg-blue-900/20",
  pending:   "text-gray-400    border-gray-700    bg-gray-900/20",
};

export function ScoreBadge({ score, grade, size = "md" }: Props) {
  const colour = grade ? gradeColour[grade] ?? gradeColour.F : "text-gray-500 border-gray-700 bg-gray-900/20";
  const textSize = size === "lg" ? "text-2xl" : size === "sm" ? "text-[10px]" : "text-xs";
  const px = size === "lg" ? "px-3 py-1" : "px-2 py-0.5";

  return (
    <span className={`inline-flex items-center gap-1.5 rounded border font-mono font-semibold ${colour} ${textSize} ${px}`}>
      {grade && <span>{grade}</span>}
      {score !== null && score !== undefined && (
        <span className="opacity-80">{score}<span className="text-[0.7em] opacity-60">/100</span></span>
      )}
      {score === null && grade === null && <span className="opacity-40">—</span>}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const colour = statusColour[status] ?? statusColour.pending;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded border text-[10px] font-semibold uppercase tracking-widest ${colour}`}>
      {status === "running" && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mr-1.5 animate-pulse" />}
      {status}
    </span>
  );
}
