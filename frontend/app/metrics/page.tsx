"use client";

import { useEffect, useState } from "react";
import { metrics, type MetricsResponse } from "@/lib/api";

type Tab = "models" | "split" | "cal" | "external";

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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat k="Homology RF" v="0.9515" s="ROC-AUC · n = 3230" />
        <Stat k="Random split RF" v="0.9791" s="do not quote · leakage" />
        <Stat k="RF ECE" v="0.078 → 0.023" s="15-bin, Platt" />
        <Stat k="External 2b RF" v="0.903" s="length-matched DBAASP · fragment negs" />
      </div>

      <div className="flex flex-wrap gap-2">
        {([
          ["models", "Models"],
          ["split", "Homology vs random"],
          ["cal", "Calibration"],
          ["external", "External (2b)"],
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
          <div className="rounded-xl border p-4 text-sm leading-relaxed text-muted" style={{ borderColor: "var(--line)" }}>
            <p className="font-semibold text-text">Operating Points & Statistical Ranking (Cohort 1 Test, N=3230):</p>
            <p className="mt-1">
              • <strong>Threshold Triage:</strong> At default P ≥ 0.50, AMPscan RF achieves 87.5% precision / 88.0% recall. For peptide discovery screens where AMPs are rare, raising threshold to <strong>P ≥ 0.90</strong> delivers <strong>97.4% precision</strong> and <strong>98.3% specificity</strong> (1,059 candidates selected).
            </p>
            <p className="mt-1">
              • <strong>AMPscan vs Macrel:</strong> Paired bootstrap on common sequences (N=3182) shows ΔROC = +0.0014 with 95% CI [-0.0049, 0.0075]. The CI includes 0, confirming a statistical <strong>tie on discriminative ranking</strong>, while AMPscan cleanly wins on probability calibration (<strong>ECE 0.023 vs 0.204</strong>).
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Fig src="/figures/01_cohort1_roc.png" cap="Multi-tool SOTA ROC benchmark (AMPscan vs Macrel, AMPlify, AI4AMP, AmpGram)" />
            <Fig src="/figures/cm_homology_rf_test.png" cap="RF confusion matrix, homology test" />
          </div>
        </div>
      )}

      {tab === "split" && (
        <div className="space-y-6">
          <Table
            cols={["model", "accuracy", "ROC-AUC"]}
            rows={data.random_test.map((r) => [r.model, f(r.accuracy), f(r.roc_auc)])}
          />
          <div className="rounded-xl border p-4 text-sm text-muted" style={{ borderColor: "var(--line)" }}>
            <strong className="text-text">Why this gap matters:</strong> Random splitting scatters
            similar peptides across train and test, inflating ROC-AUC to ~0.979. Homology clustering
            (30% identity threshold) keeps entire peptide families together, revealing the true
            generalization performance of 0.9515.
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Fig src="/figures/roc_homology_test.png" cap="Homology-split ROC (honest evaluation)" />
            <Fig src="/figures/roc_random_test.png" cap="Random-split ROC (homology leakage demo)" />
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

      {tab === "external" && (
        <div className="space-y-6">
          <div className="rounded-xl border p-5 text-sm leading-relaxed text-muted space-y-3" style={{ borderColor: "var(--line)" }}>
            <p className="font-semibold text-text text-base">Cohort 2b — Length-Matched External DBAASP OOD Validation</p>
            <p>
              • <strong>Locked Baseline Unaltered:</strong> Locked AMPscan v1 headline metric remains Cohort 1 Homology RF <strong>ROC-AUC 0.9515</strong>.
            </p>
            <p>
              • <strong>Benchmark Scope:</strong> Cohort 2b evaluates <strong>N = 22,380</strong> total sequences (11,190 novel synthetic DBAASP positives with &lt;30% identity to train vs 11,190 length-matched negative controls; median length 14 aa vs 14 aa).
            </p>
            <p>
              • <strong>Negative Sample Provenance:</strong> Negatives are <strong>windows cut from unused long UniProt-style non-AMP chains</strong> (11,012 fragment windows + 178 intact short non-AMPs), not experimentally assayed inactives.
            </p>
            <p>
              • <strong>Honest Calibration Transfer:</strong> At P ≥ 0.5 on Cohort 2b, RF accuracy is <strong>0.645</strong> and ECE is <strong>0.28</strong>. Platt scaling parameters fitted on natural DRAMP/AMPlify sets do not transfer directly to short fragment background distributions; quote threshold-invariant ROC.
            </p>
            <p>
              • <strong>Cross-Tool Parity:</strong> On Cohort 2b, discriminative ranking between tools is a statistical <strong>tie</strong> (~0.90 ROC): <strong>AMPscan RF 0.9030</strong>, <strong>Macrel 0.8998</strong>, <strong>AMPlify 0.8991</strong>, <strong>AI4AMP 0.8786</strong>.
            </p>
            <p className="text-xs text-warn">
              * Note: Do not quote the earlier length-confounded 0.9935 table (which paired 14-aa DBAASP synthetics against 76-aa UniProt leftovers).
            </p>
          </div>
          <Table
            cols={["model", "evaluated N", "tool skips", "accuracy @ 0.5", "MCC", "ROC-AUC", "PR-AUC", "ECE-15"]}
            rows={
              data.cohort_2b?.table
                ? data.cohort_2b.table.map((r) => [
                    r.model,
                    String(r.n),
                    r.skip ? `${r.skip} (X)` : "0",
                    f(r.accuracy),
                    f(r.mcc),
                    f(r.roc_auc),
                    f(r.pr_auc),
                    f(r.ece_15),
                  ])
                : [
                    ["AMPscan RF (Platt)", "22380", "0", "0.6449", "0.3765", "0.9030", "0.9205", "0.2767"],
                    ["AMPscan 1D-CNN (T)", "22380", "0", "0.6162", "0.3235", "0.8894", "0.9117", "0.3044"],
                    ["Macrel ONNX", "20426", "1954 (X)", "0.8222", "0.6554", "0.8998", "0.9017", "0.1058"],
                    ["AMPlify balanced", "20426", "1954 (X)", "0.8216", "0.6421", "0.8991", "0.9075", "0.0867"],
                    ["AI4AMP PC6", "22380", "0", "0.8081", "0.6287", "0.8786", "0.9031", "0.0870"],
                  ]
            }
          />
          <Fig src="/figures/02b_cohort2b_roc.png" cap="Cohort 2b ROC — Length-matched DBAASP OOD (fragment negatives)" />
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
