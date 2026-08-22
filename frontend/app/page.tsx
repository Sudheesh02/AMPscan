"use client";

import Link from "next/link";
import Workflow from "@/components/Workflow";

export default function HomePage() {
  return (
    <div className="space-y-16">
      <section className="membrane overflow-hidden rounded-3xl px-6 py-12 sm:px-10 sm:py-16">
        <div className="grid items-center gap-10 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-muted">peptide · membrane · homology</p>
            <h1 className="mt-4 font-display text-5xl leading-[0.95] tracking-tight sm:text-7xl">AMPscan</h1>
            <p className="mt-4 font-display text-2xl text-muted sm:text-3xl">Binary antimicrobial peptide classifier</p>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">
              Sequences 5-100 amino acids. Primary score is a Platt-calibrated random forest after a
              30% identity cluster split. Not a wet-lab assay.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/predict" className="rounded-full px-6 py-2.5 text-sm font-medium" style={{ background: "var(--accent)", color: "#07140f" }}>
                Classify a sequence
              </Link>
              <Link href="/metrics" className="rounded-full border px-6 py-2.5 text-sm" style={{ borderColor: "var(--line)" }}>
                View evaluation
              </Link>
            </div>
          </div>
          <div className="relative min-h-[280px] overflow-hidden rounded-2xl ring-1 ring-[color:var(--line)]">
            <video className="absolute inset-0 h-full w-full object-cover" autoPlay muted loop playsInline poster="/media/peptides-still.jpg">
              <source src="/media/peptides.mp4" type="video/mp4" />
            </video>
          </div>
        </div>
        <div className="mt-12 grid gap-4 sm:grid-cols-3">
          {[
            { k: "Homology test", v: "0.9515", s: "Random Forest ROC-AUC" },
            { k: "Length", v: "5-100", s: "amino acids" },
            { k: "Task", v: "binary", s: "AMP vs non-AMP" },
          ].map((c) => (
            <div key={c.k} className="rounded-2xl border p-5" style={{ borderColor: "var(--line)", background: "color-mix(in srgb, var(--bg) 65%, transparent)" }}>
              <div className="text-[11px] uppercase tracking-[0.18em] text-muted">{c.k}</div>
              <div className="mt-2 font-display text-4xl">{c.v}</div>
              <div className="mt-1 text-sm text-muted">{c.s}</div>
            </div>
          ))}
        </div>
      </section>

      <Workflow />

      <section className="grid gap-4 md:grid-cols-2">
        <div className="panel p-6">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Random split</div>
          <div className="mt-2 font-display text-5xl">0.9791</div>
          <p className="mt-3 text-sm text-muted">Same peptides, clusters ignored. Related sequences can appear in both train and test.</p>
        </div>
        <div className="panel p-6" style={{ boxShadow: "0 0 0 1px var(--accent)" }}>
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Homology split</div>
          <div className="mt-2 font-display text-5xl">0.9515</div>
          <p className="mt-3 text-sm text-muted">MMseqs2 30% identity. Whole clusters stay in one fold. This is the reported result.</p>
        </div>
      </section>
    </div>
  );
}
