import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Bar,
  BarChart,
  Cell,
} from "recharts";

interface TrendPoint {
  day: string;
  avg_score: number;
  runs: number;
}

interface GradeDist {
  grade: string;
  count: number;
}

const GRADE_COLOURS: Record<string, string> = {
  A: "#34d399",
  B: "#22d3ee",
  C: "#facc15",
  D: "#fb923c",
  F: "#f87171",
};

export function ScoreTrendChart({ data }: { data: TrendPoint[] }) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-full text-gray-700 text-sm">
        No score data yet
      </div>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    day: new Date(d.day).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={formatted} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis
          dataKey="day"
          tick={{ fill: "#6b7280", fontSize: 10 }}
          axisLine={{ stroke: "#1f2937" }}
          tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fill: "#6b7280", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "#0f1117", border: "1px solid #1f2937",
            borderRadius: 6, fontSize: 12, color: "#e5e7eb",
          }}
          formatter={(v: number) => [`${v}/100`, "Avg score"]}
        />
        <Line
          type="monotone"
          dataKey="avg_score"
          stroke="#60a5fa"
          strokeWidth={2}
          dot={{ fill: "#60a5fa", r: 3 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function GradeDistChart({ data }: { data: GradeDist[] }) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-full text-gray-700 text-sm">
        No grade data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
        <XAxis
          dataKey="grade"
          tick={{ fill: "#9ca3af", fontSize: 11, fontWeight: 600 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#6b7280", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
        />
        <Tooltip
          contentStyle={{
            background: "#0f1117", border: "1px solid #1f2937",
            borderRadius: 6, fontSize: 12, color: "#e5e7eb",
          }}
          formatter={(v: number) => [v, "Runs"]}
        />
        <Bar dataKey="count" radius={[3, 3, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.grade} fill={GRADE_COLOURS[d.grade] ?? "#6b7280"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
