interface Props {
  blastRadius: number;
  blastBlocked: boolean;
  faultCount: number;
  hasHypothesis: boolean;
  hasCircuitBreaker: boolean;
}

export function Header({ blastRadius, blastBlocked, faultCount, hasHypothesis, hasCircuitBreaker }: Props) {
  const blastColour =
    blastRadius >= 100 ? 'bg-red-600' :
    blastRadius >= 80  ? 'bg-orange-500' :
    blastRadius >= 50  ? 'bg-yellow-500' :
                         'bg-emerald-500';

  const blastTextColour =
    blastRadius >= 100 ? 'text-red-400' :
    blastRadius >= 80  ? 'text-orange-400' :
    blastRadius >= 50  ? 'text-yellow-400' :
                         'text-emerald-400';

  return (
    <header className="flex items-center h-14 px-5 border-b border-gray-800 bg-[#0f1117] shrink-0 gap-6">
      {/* Logo */}
      <div className="flex items-center gap-2.5 shrink-0">
        <span className="text-xl">⚡</span>
        <div className="leading-none">
          <span className="font-bold text-white tracking-widest text-sm">KALI</span>
          <div className="text-[10px] text-gray-500 mt-0.5">Kinetic Automated Load &amp; Infrastructure</div>
        </div>
      </div>

      <div className="h-6 w-px bg-gray-800" />

      {/* Blast radius indicator */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-[10px] text-gray-500 uppercase tracking-widest">Blast Radius</span>
        <div className="relative w-28 h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ${blastColour} ${blastRadius >= 100 ? 'blast-danger' : ''}`}
            style={{ width: `${Math.min(blastRadius, 100)}%` }}
          />
        </div>
        <span className={`text-xs font-mono font-semibold ${blastTextColour}`}>
          {blastRadius}%
        </span>
        {blastBlocked && (
          <span className="text-[10px] bg-red-900/50 text-red-400 border border-red-700 rounded px-1.5 py-0.5 font-bold">
            BLOCKED
          </span>
        )}
      </div>

      <div className="h-6 w-px bg-gray-800" />

      {/* Checklist pills */}
      <div className="flex items-center gap-2 text-[11px]">
        <Pill ok={faultCount > 0}   label={`${faultCount} fault${faultCount !== 1 ? 's' : ''}`} />
        <Pill ok={hasHypothesis}    label="hypothesis" />
        <Pill ok={hasCircuitBreaker} label="circuit breaker" />
      </div>

      <div className="ml-auto text-[10px] text-gray-600 italic shrink-0 hidden xl:block">
        Controlled Instability. Indestructible Infrastructure.
      </div>
    </header>
  );
}

function Pill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`px-2 py-0.5 rounded-full border font-medium ${
      ok
        ? 'border-emerald-700 bg-emerald-900/30 text-emerald-400'
        : 'border-gray-700 bg-gray-900/30 text-gray-500'
    }`}>
      {ok ? '✓' : '○'} {label}
    </span>
  );
}
