/** Site-wide cell / membrane / helix field. */
export default function Backdrop() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden>
      <div className="absolute inset-0" style={{ background: "var(--bg)" }} />
      <div className="cyto absolute inset-0 opacity-80" />
      <div className="orb orb-a h-[46rem] w-[46rem] -left-32 -top-28" style={{ background: "var(--orb-a)" }} />
      <div className="orb orb-b right-[-8rem] top-[18%] h-[38rem] w-[38rem]" style={{ background: "var(--orb-b)" }} />
      <div className="orb bottom-[-10rem] left-[28%] h-[32rem] w-[32rem]" style={{ background: "var(--orb-a)" }} />

      <svg className="absolute left-[-4%] top-[8%] h-[70vh] w-[28vw] min-w-[220px] opacity-[0.22] dark:opacity-[0.28]" viewBox="0 0 120 420" fill="none">
        <Helix />
      </svg>
      <svg className="absolute right-[-2%] top-[22%] h-[62vh] w-[22vw] min-w-[180px] opacity-[0.18] dark:opacity-[0.24]" viewBox="0 0 120 420" fill="none">
        <Helix />
      </svg>

      <svg className="absolute left-[38%] top-[6%] h-40 w-40 opacity-25 dark:opacity-30" viewBox="0 0 100 100" fill="none">
        <ellipse cx="50" cy="50" rx="38" ry="26" stroke="currentColor" className="text-[color:var(--accent)]" strokeWidth="1.2" />
        <ellipse cx="50" cy="50" rx="26" ry="16" stroke="currentColor" className="text-[color:var(--accent)]" strokeWidth="0.8" opacity="0.7" />
        <circle cx="58" cy="46" r="6" fill="currentColor" className="text-[color:var(--accent)]" opacity="0.35" />
      </svg>

      <svg className="absolute bottom-0 left-0 h-[28vh] w-full opacity-50 dark:opacity-40" viewBox="0 0 1200 180" preserveAspectRatio="none" fill="none">
        <Bilayer />
      </svg>

      <div className="grain absolute inset-0 opacity-[0.16] dark:opacity-[0.26]" />
    </div>
  );
}

function Helix() {
  return (
    <g className="text-[color:var(--accent)]" stroke="currentColor">
      <path d="M40 8c28 18 28 36 0 54s-28 36 0 54 28 36 0 54 28 36 0 54 28 36 0 54 28 36 0 54 28 36 0 54" strokeWidth="2.2" fill="none" />
      <path d="M80 8c-28 18-28 36 0 54s28 36 0 54-28 36 0 54-28 36 0 54-28 36 0 54-28 36 0 54-28 36 0 54" strokeWidth="2.2" fill="none" />
      {[...Array(12)].map((_, i) => (
        <line key={i} x1="42" x2="78" y1={24 + i * 32} y2={40 + i * 32} strokeWidth="1" opacity="0.55" />
      ))}
    </g>
  );
}

function Bilayer() {
  const heads = Array.from({ length: 40 }, (_, i) => 18 + i * 30);
  return (
    <g className="text-[color:var(--accent)]">
      {heads.map((x) => (
        <g key={x} fill="currentColor" opacity="0.55">
          <circle cx={x} cy="48" r="7" />
          <circle cx={x} cy="128" r="7" />
          <rect x={x - 1.4} y="55" width="2.8" height="66" opacity="0.35" />
        </g>
      ))}
      <path d="M0 88h1200" stroke="currentColor" strokeOpacity="0.15" />
    </g>
  );
}
