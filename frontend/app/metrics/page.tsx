"use client";

import { useEffect, useState } from "react";
import { metrics, type MetricsResponse } from "@/lib/api";

type Tab = "models" | "split" | "cal";

export default function MetricsPage() {
  const [data, setData] = useState<MetricsResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("models");

  useEffect(() => {
    metrics()
      .then(setData)
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : "Could not load metrics"));
  }, []);

  if (err) return <p className="text-sm" style={{ color: "var(--amp)" }}>{err}</p>;
  if (!data) return <p className="text-muted">Loading evaluation...</p>;

  return (
    <div className="space-y-10">
      <div>
        <p className="text-xs uppercase tracking-[0.22em] text-muted">Evaluation</p>
        <h1 className="mt-1 font-display text-4xl tracking-tight">Evidence</h1>
        <p className="mt-3 max-w-2xl text-muted">{data.plain_english}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat k="Homology RF" v="0.9515" s="ROC-AUC · n = 3230" />
        <Stat k="Random split RF" v="0.9791" s="clusters ignored" />
        <Stat k="RF ECE" v="0.078 → 0.023" s="15-bin, Platt" />
      </div>

      <div className="flex flex-wrap gap-2">
        {([
          ["models", "Models"],
          ["split", "Homology vs random"],
          ["cal", "Calibration"],
        ] as const).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className="rounded-full px-4 py-1.5 text-sm"
            style={{
              background: tab === id ? "var(--accent)" : "transparent",
              color: tab === id ? "#07140f" : "var(--text)",
              border: "1px solid var(--line)",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "models" && (
        <div className="space-y-6">
          <Table
            cols={["model", "accuracy", "macro-F1", "ROC-AUC", "PR-AUC"]}
            rows={data.homology_test.map((r) => [r.model, f(r.accuracy), f(r.macro_f1), f(r.roc_auc), f(r.pr_auc)])}
          />
          <Fig src="/figures/roc_homology_test.png" cap="Homology-test ROC (locked)" />
          <Fig src="/figures/cm_homology_rf_test.png" cap="RF confusion matrix, homology test" />
        </div>
      )}

      {tab === "split" && (
        <div className="space-y-6">
          <Table
            cols={["model", "accuracy", "ROC-AUC"]}
            rows={data.random_test.map((r) => [r.model, f(r.accuracy), f(r.roc_auc)])}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <Fig src="/figures/roc_homology_test.png" cap="Homology ROC" />
            <Fig src="/figures/roc_random_test.png" cap="Random-split ROC" />
          </div>
        </div>
      )}

      {tab === "cal" && (
        <div className="space-y-6">
          <Table
            cols={["model", "method", "ECE uncal", "ECE cal", "ROC-AUC"]}
            rows={data.calibration_ece_homology_test.map((r) => [r.model, r.method, f(r.ece_uncal), f(r.ece_cal), f(r.roc_auc)])}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <Fig src="/figures/reliability_homology_rf_test.png" cap="RF reliability (Platt)" />
            <Fig src="/figures/reliability_homology_cnn_test.png" cap="CNN reliability (T)" />
          </div>
        </div>
      )}
    </div>
  );
}

function f(n: number) {
  return n.toFixed(4);
}

function Stat({ k, v, s }: { k: string; v: string; s: string }) {
  return (
    <div className="panel p-5">
      <div className="text-[11px] uppercase tracking-[0.16em] text-muted">{k}</div>
      <div className="mt-2 font-display text-3xl">{v}</div>
      <div className="mt-1 text-xs text-muted">{s}</div>
    </div>
  );
}

function Table({ cols, rows }: { cols: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto rounded-xl border" style={{ borderColor: "var(--line)" }}>
      <table className="min-w-full text-left text-sm">
        <thead>
          <tr className="text-[11px] uppercase tracking-wide text-muted">
            {cols.map((c) => (
              <th key={c} className="px-4 py-3">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t" style={{ borderColor: "var(--line)" }}>
              {row.map((cell, j) => (
                <td key={j} className={`px-4 py-3 ${j ? "font-mono tabular-nums" : ""}`}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Fig({ src, cap }: { src: string; cap: string }) {
  return (
    <figure className="panel overflow-hidden">
      <img src={src} alt={cap} className="w-full bg-white" />
      <figcaption className="px-3 py-2 text-xs text-muted">{cap}</figcaption>
    </figure>
  );
}
