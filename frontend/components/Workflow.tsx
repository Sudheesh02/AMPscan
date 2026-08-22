"use client";

import { useEffect, useState } from "react";

const STEPS = [
  { n: "01", t: "Letters", d: "FASTA or raw amino acids. Length 5-100. B/Z/U/O/J become X." },
  { n: "02", t: "Forest", d: "425 composition features. Platt map to a calibrated P(AMP)." },
  { n: "03", t: "CNN", d: "One-hot 21x100. Temperature T ~ 1.283. Secondary score only." },
  { n: "04", t: "Plot", d: "Integrated Gradients on the CNN. Training examples are bannered." },
];

export default function Workflow() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setStep((s) => (s + 1) % STEPS.length);
    }, 3500);
    return () => window.clearInterval(id);
  }, []);

  return (
    <section>
      <h2 className="font-display text-3xl tracking-tight">How a sequence moves through the machine</h2>
      <div className="mt-8 flex flex-col items-stretch lg:flex-row lg:items-center">
        {STEPS.map((s, i) => (
          <div key={s.n} className="flex flex-1 items-stretch lg:items-center">
            <button
              type="button"
              onClick={() => setStep(i)}
              className={`membrane h-full w-full rounded-2xl p-5 pt-7 text-left transition ${step === i ? "node-lit" : ""}`}
              style={{ opacity: step === i ? 1 : 0.7 }}
            >
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-sm" style={{ color: step === i ? "var(--accent)" : "var(--muted)" }}>
                  {s.n}
                </span>
                <span className="font-medium">{s.t}</span>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-muted">{s.d}</p>
            </button>
            {i < STEPS.length - 1 && (
              <Arrow lit={step === i} />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function Arrow({ lit }: { lit: boolean }) {
  return (
    <div className="flex items-center justify-center px-1 py-2 lg:px-2 lg:py-0" aria-hidden>
      <svg className="h-8 w-8 rotate-90 lg:h-10 lg:w-14 lg:rotate-0" viewBox="0 0 64 24" fill="none">
        <path
          d="M4 12h48m0 0-7-7m7 7-7 7"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={lit ? "flow-arrow text-[color:var(--accent)]" : "text-[color:var(--muted)]"}
          opacity={lit ? 1 : 0.4}
        />
      </svg>
    </div>
  );
}
