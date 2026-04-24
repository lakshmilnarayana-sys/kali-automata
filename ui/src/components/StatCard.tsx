interface Props {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
  icon?: string;
}

export function StatCard({ label, value, sub, accent = "text-white", icon }: Props) {
  return (
    <div className="bg-[#0f1117] border border-gray-800 rounded-lg p-5 flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-gray-500 uppercase tracking-widest">{label}</span>
        {icon && <span className="text-lg opacity-60">{icon}</span>}
      </div>
      <div className={`text-3xl font-bold font-mono ${accent}`}>{value}</div>
      {sub && <div className="text-[11px] text-gray-600">{sub}</div>}
    </div>
  );
}
