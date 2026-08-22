"use client";

export default function HudDial({ value, label }: { value: number; label: string }) {
  const v = Math.min(1, Math.max(0, value));
  const r = 52;
  const c = 2 * Math.PI * r;
  const dash = c * v;
  return (
    <div className="flex items-center gap-5">
      <svg width="132" height="132" viewBox="0 0 132 132" className="-rotate-90">
        <circle cx="66" cy="66" r={r} fill="none" stroke="var(--bg-2)" strokeWidth="10" />
        <circle
          cx="66"
          cy="66"
          r={r}
          fill="none"
          stroke="var(--accent)"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c - dash}`}
        />
      </svg>
      <div>
        <div className="text-[11px] uppercase tracking-[0.18em] text-muted">{label}</div>
        <div className="font-display text-5xl tabular-nums leading-none">{value.toFixed(4)}</div>
        <div className="mt-1 font-mono text-xs text-muted">threshold 0.50</div>
      </div>
    </div>
  );
}
