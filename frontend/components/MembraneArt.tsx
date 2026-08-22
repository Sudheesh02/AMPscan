/** Hero illustration: cationic peptide meeting a bilayer. */
export default function MembraneArt() {
  return (
    <svg viewBox="0 0 420 360" className="h-full w-full" fill="none" aria-hidden>
      <defs>
        <linearGradient id="pep" x1="40" y1="20" x2="280" y2="300">
          <stop offset="0%" stopColor="var(--accent)" />
          <stop offset="100%" stopColor="rgb(224,122,95)" />
        </linearGradient>
      </defs>
      {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map((i) => {
        const x = 28 + i * 32;
        return (
          <g key={i} opacity="0.9">
            <circle cx={x} cy="128" r="9" fill="var(--accent)" fillOpacity="0.85" />
            <circle cx={x} cy="248" r="9" fill="var(--accent)" fillOpacity="0.85" />
            <rect x={x - 2} y="137" width="4" height="102" fill="var(--accent)" fillOpacity="0.28" />
          </g>
        );
      })}
      <path
        d="M70 40c18 22 22 38 6 58 22 16 26 34 8 52 22 16 24 36 4 56 20 18 30 38 18 72"
        stroke="url(#pep)"
        strokeWidth="7"
        strokeLinecap="round"
      />
      <path
        d="M102 36c18 22 22 38 6 58 22 16 26 34 8 52 22 16 24 36 4 56 20 18 30 38 18 72"
        stroke="var(--text)"
        strokeOpacity="0.35"
        strokeWidth="5"
        strokeLinecap="round"
      />
      {[
        [78, 48],
        [108, 92],
        [86, 140],
        [118, 188],
        [92, 236],
        [124, 286],
      ].map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="6" fill="var(--text)" />
      ))}
      <text x="250" y="188" fill="var(--muted)" fontSize="12" fontFamily="ui-monospace, monospace">
        bilayer
      </text>
      <text x="48" y="28" fill="var(--muted)" fontSize="12" fontFamily="ui-monospace, monospace">
        peptide
      </text>
    </svg>
  );
}
