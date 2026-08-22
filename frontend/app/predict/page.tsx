"use client";

import { motion } from "framer-motion";
import { Upload } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import HudDial from "@/components/HudDial";
import ResidueHeatmap from "@/components/ResidueHeatmap";
import { explain, predict, type ExplainResponse, type PredictResponse } from "@/lib/api";
import { BATCH_CAP, EXAMPLES, MAGAININ2, parseRecords, validateSeq } from "@/lib/sequence";

type Row = {
  id: string;
  seq: string;
  errors: string[];
  pred?: PredictResponse;
  ig?: ExplainResponse;
};

export default function PredictPage() {
  const [raw, setRaw] = useState(MAGAININ2);
  const [busy, setBusy] = useState(false);
  const [apiDown, setApiDown] = useState<string | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [active, setActive] = useState(0);
  const fileRef = useRef<HTMLInputElement>(null);

  const parsed = useMemo(() => parseRecords(raw), [raw]);
  const previewErrors = parsed.length ? validateSeq(parsed[0].seq) : ["Paste a peptide or FASTA."];

  async function run(text: string) {
    const recs = parseRecords(text).slice(0, BATCH_CAP);
    if (!recs.length) return;
    setBusy(true);
    setApiDown(null);
    const next: Row[] = recs.map((r) => ({ ...r, errors: validateSeq(r.seq) }));
    try {
      for (let i = 0; i < next.length; i++) {
        if (next[i].errors.length) continue;
        const pred = await predict(next[i].seq);
        next[i].pred = pred;
        if (pred.valid) next[i].ig = await explain(next[i].seq);
      }
      setRows(next);
      setActive(0);
    } catch (err) {
      setRows([]);
      setApiDown(err instanceof Error ? err.message : "API unreachable");
    } finally {
      setBusy(false);
    }
  }

  function mutate(pos1: number, aa: string) {
    const recs = parseRecords(raw);
    if (!recs[0]) return;
    const s = recs[0].seq.split("");
    s[pos1 - 1] = aa;
    const next = s.join("");
    setRaw(next);
    void run(next);
  }

  const row = rows[active];
  const p = row?.pred?.primary;
  const feat = row?.pred?.features_preview;

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs uppercase tracking-[0.22em] text-muted">Workbench</p>
        <h1 className="mt-1 font-display text-4xl tracking-tight">Classify</h1>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[5fr_7fr]">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void run(raw);
          }}
          className="membrane space-y-4 rounded-2xl p-5 pt-8"
        >
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex.id}
                type="button"
                onClick={() => {
                  setRaw(ex.seq);
                  void run(ex.seq);
                }}
                className="rounded-full border px-3 py-1 text-xs"
                style={{ borderColor: "var(--line)" }}
              >
                {ex.name} · train
              </button>
            ))}
          </div>
          <textarea
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                e.preventDefault();
                void run(raw);
              }
            }}
            rows={10}
            spellCheck={false}
            className="w-full rounded-xl border bg-transparent p-3 font-mono text-sm outline-none"
            style={{ borderColor: "var(--line)" }}
          />
          <div className="flex justify-between text-xs text-muted">
            <span>
              {parsed[0] ? `${parsed[0].seq.length} aa` : "empty"}
              {previewErrors.length && parsed.length ? ` · ${previewErrors[0]}` : ""}
            </span>
            <span>Ctrl / ⌘ + Enter</span>
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy || !parsed.length}
              className="rounded-full px-5 py-2 text-sm font-medium disabled:opacity-40"
              style={{ background: "var(--accent)", color: "#07140f" }}
            >
              {busy ? "Scoring..." : "Run"}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-full border px-4 py-2 text-sm"
              style={{ borderColor: "var(--line)" }}
              onClick={() => fileRef.current?.click()}
            >
              <Upload size={14} /> FASTA
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".fa,.fasta,.txt,.faa"
              className="hidden"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                const t = await f.text();
                setRaw(t);
                void run(t);
              }}
            />
          </div>
        </form>

        <div className="space-y-4">
          {apiDown && <p className="text-sm" style={{ color: "var(--amp)" }}>{apiDown}</p>}
          {row?.errors.length ? <p className="text-sm" style={{ color: "var(--amp)" }}>{row.errors.join(" · ")}</p> : null}

          {row?.pred?.valid && p && row.pred.secondary && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
              {row.ig?.train_set_warning && (
                <div className="rounded-xl border px-4 py-3 text-sm" style={{ borderColor: "var(--warn)", background: "var(--warn-bg)" }}>
                  Training-set sequence. {row.ig.canonical_name} = {row.ig.matched_train_id} is in the homology train fold.
                </div>
              )}
              <div className="panel p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <HudDial value={p.p_amp} label="Calibrated RF P(AMP)" />
                  <span
                    className="rounded-full px-3 py-1 text-xs font-semibold uppercase"
                    style={
                      p.label === "AMP"
                        ? { background: "var(--accent)", color: "#07140f" }
                        : { background: "var(--bg-2)" }
                    }
                  >
                    {p.label}
                  </span>
                </div>
                <div className="mt-6">
                  <div className="mb-1 flex justify-between text-xs text-muted">
                    <span>CNN T = {row.pred.secondary.temperature.toFixed(3)}</span>
                    <span className="font-mono">{row.pred.secondary.p_amp.toFixed(4)}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full" style={{ background: "var(--bg-2)" }}>
                    <div className="h-full" style={{ width: `${row.pred.secondary.p_amp * 100}%`, background: "var(--neg)" }} />
                  </div>
                </div>
                {feat && (
                  <div className="mt-5 grid grid-cols-2 gap-2 text-xs sm:grid-cols-5">
                    {[
                      ["length", feat.length],
                      ["charge pH 7", feat.net_charge_pH7],
                      ["GRAVY", feat.GRAVY],
                      ["μH", feat.hydrophobic_moment ?? "—"],
                      ["aromatic", feat.aromatic_fraction ?? "—"],
                    ].map(([k, v]) => (
                      <div key={String(k)} className="rounded-lg border p-2" style={{ borderColor: "var(--line)" }}>
                        <div className="text-muted">{k}</div>
                        <div className="font-mono">{v}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {row?.ig?.valid && row.ig.residues.length > 0 && (
        <section className="membrane rounded-2xl p-6 pt-9">
          <div className="mb-4">
            <div className="text-xs uppercase tracking-[0.2em] text-muted">Integrated Gradients · CNN</div>
            <h2 className="font-display text-2xl">Residue track</h2>
          </div>
          <ResidueHeatmap residues={row.ig.residues} onMutate={mutate} />
        </section>
      )}
    </div>
  );
}
