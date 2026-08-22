export default function ProbabilityMeter({
  value,
  label,
}: {
  value: number;
  label: string;
}) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100);
  return (
    <div>
      <div className="mb-2 flex items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-muted">{label}</div>
          <div className="font-display text-5xl leading-none tracking-tight tabular-nums">{value.toFixed(4)}</div>
        </div>
        <div className="text-sm text-muted">{pct}%</div>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full" style={{ background: "var(--bg-2)" }}>
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${pct}%`,
            background: "linear-gradient(90deg, var(--accent-2), var(--accent))",
          }}
        />
      </div>
    </div>
  );
}
