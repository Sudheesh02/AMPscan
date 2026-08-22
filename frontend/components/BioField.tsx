"use client";

export default function BioField() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden>
      <video
        className="absolute inset-0 h-full w-full object-cover"
        autoPlay
        muted
        loop
        playsInline
        poster="/media/membrane-still.jpg"
      >
        <source src="/media/membrane.mp4" type="video/mp4" />
      </video>
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(180deg, color-mix(in srgb, var(--bg) 42%, transparent) 0%, color-mix(in srgb, var(--bg) 78%, transparent) 48%, var(--bg) 100%)",
        }}
      />
      <div className="cyto absolute inset-0 opacity-30" />
      <svg className="absolute bottom-0 left-0 h-[22vh] w-full opacity-60 dark:opacity-50" viewBox="0 0 1200 180" preserveAspectRatio="none" fill="none">
        {Array.from({ length: 40 }, (_, i) => 18 + i * 30).map((x) => (
          <g key={x} fill="currentColor" className="text-[color:var(--accent)]" opacity="0.55">
            <circle cx={x} cy="48" r="7" />
            <circle cx={x} cy="128" r="7" />
            <rect x={x - 1.4} y="55" width="2.8" height="66" opacity="0.35" />
          </g>
        ))}
      </svg>
      <div className="grain absolute inset-0 opacity-[0.12] dark:opacity-[0.2]" />
    </div>
  );
}
