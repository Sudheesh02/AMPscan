"use client";

import { motion } from "framer-motion";
import { CheckCircle2, ChevronRight, Layers, Sparkles, Upload } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import HudDial from "@/components/HudDial";
import ResidueHeatmap from "@/components/ResidueHeatmap";
import {
  explain,
  predict,
  predictBatch,
  scanProtein,
  type ExplainResponse,
  type PredictResponse,
  type ScanResponse,
} from "@/lib/api";
import {
  BATCH_CAP,
  EXAMPLES,
  HCAP18,
  MAGAININ2,
  parseRecords,
  validateSeq,
} from "@/lib/sequence";

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
  const [scanResult, setScanResult] = useState<ScanResponse | null>(null);
  const [scanMode, setScanMode] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const parsed = useMemo(() => parseRecords(raw), [raw]);
  const isLongSeq = parsed.length === 1 && parsed[0].seq.length > 100;
  const previewErrors = parsed.length && !isLongSeq ? validateSeq(parsed[0].seq) : [];

  async function run(text: string) {
    const recs = parseRecords(text).slice(0, BATCH_CAP);
    if (!recs.length) return;
    setBusy(true);
    setApiDown(null);
    setScanResult(null);

    // If single long protein > 100 aa, automatically route to protein sliding-window scanner
    if (recs.length === 1 && recs[0].seq.length > 100) {
      setScanMode(true);
      try {
        const scanRes = await scanProtein(recs[0].seq, 25, 1);
        setScanResult(scanRes);
        setRows([{ id: recs[0].id, seq: recs[0].seq, errors: scanRes.errors }]);
        setActive(0);
      } catch (err) {
        setApiDown(err instanceof Error ? err.message : "Scanning API unreachable");
      } finally {
        setBusy(false);
      }
      return;
    }

    setScanMode(false);
    const next: Row[] = recs.map((r) => ({ ...r, errors: validateSeq(r.seq) }));
    const validRecs = next.filter((r) => !r.errors.length).map((r) => ({ id: r.id, sequence: r.seq }));

    try {
      if (validRecs.length > 1) {
        // Fast batched scoring
        const batchRes = await predictBatch(validRecs);
        const resMap = new Map(batchRes.results.map((res) => [res.id, res]));
        for (const item of next) {
          if (resMap.has(item.id)) {
            item.pred = resMap.get(item.id);
          }
        }
      } else if (validRecs.length === 1) {
        const pred = await predict(validRecs[0].sequence);
        const idx = next.findIndex((r) => !r.errors.length);
        if (idx >= 0) next[idx].pred = pred;
      }

      // Fetch explain attribution for the first valid sequence
      const firstValid = next.find((r) => r.pred?.valid);
      if (firstValid && firstValid.pred?.valid) {
        firstValid.ig = await explain(firstValid.seq);
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

  async function selectRow(index: number) {
    setActive(index);
    const target = rows[index];
    if (target && target.pred?.valid && !target.ig) {
      try {
        target.ig = await explain(target.seq);
        setRows([...rows]);
      } catch {
        // IG error non-fatal
      }
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
  const nearest = row?.pred?.nearest_train;

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
                {ex.name}
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
              {parsed[0]
                ? `${parsed.length > 1 ? `${parsed.length} records · ` : ""}${parsed[0].seq.length} aa`
                : "empty"}
              {isLongSeq ? " · Long chain (auto-scan mode)" : ""}
              {previewErrors.length && parsed.length && !isLongSeq ? ` · ${previewErrors[0]}` : ""}
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
              {busy ? "Scoring..." : isLongSeq ? "Scan Protein" : parsed.length > 1 ? `Score Batch (${parsed.length})` : "Run"}
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
          {row?.errors.length && !scanMode ? (
            <p className="text-sm" style={{ color: "var(--amp)" }}>{row.errors.join(" · ")}</p>
          ) : null}

          {/* Multi-item Batch Navigation */}
          {rows.length > 1 && !scanMode && (
            <div className="rounded-xl border p-3 space-y-2" style={{ borderColor: "var(--line)" }}>
              <div className="flex items-center justify-between text-xs text-muted">
                <span className="font-semibold uppercase tracking-wider">Batch Results ({rows.length} sequences)</span>
                <span>Click to inspect</span>
              </div>
              <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
                {rows.map((r, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => void selectRow(i)}
                    className={`w-full flex items-center justify-between rounded-lg px-3 py-1.5 text-xs text-left transition-colors ${
                      active === i ? "bg-white/10 font-medium" : "hover:bg-white/5"
                    }`}
                  >
                    <span className="font-mono truncate max-w-[180px]">{r.id} ({r.seq.length} aa)</span>
                    <span className="flex items-center gap-2">
                      {r.pred?.primary ? (
                        <span
                          className="rounded px-1.5 py-0.5 text-[10px] font-semibold"
                          style={
                            r.pred.primary.label === "AMP"
                              ? { background: "var(--accent)", color: "#07140f" }
                              : { background: "var(--bg-2)" }
                          }
                        >
                          {r.pred.primary.p_amp.toFixed(3)}
                        </span>
                      ) : r.errors.length ? (
                        <span className="text-red-400">Error</span>
                      ) : (
                        <span>—</span>
                      )}
                      <ChevronRight size={12} className="text-muted" />
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Protein Sliding-Window Scanner Mode */}
          {scanMode && scanResult?.valid && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
              <div className="panel p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase tracking-[0.2em] text-muted flex items-center gap-1.5">
                    <Layers size={14} /> Protein Sliding-Window Scan
                  </span>
                  <span className="rounded-full px-2.5 py-0.5 text-xs border" style={{ borderColor: "var(--line)" }}>
                    {scanResult.sequence_length} aa · {scanResult.n_windows} windows (L={scanResult.window})
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-muted">
                  {scanResult.note}
                </p>
                {scanResult.summary && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-xs">
                    <div className="rounded-lg border p-2.5" style={{ borderColor: "var(--line)" }}>
                      <div className="text-muted">Peak P(AMP)</div>
                      <div className="font-mono text-base font-semibold" style={{ color: "var(--accent)" }}>
                        {scanResult.summary.max_p_amp?.toFixed(4) ?? "—"}
                      </div>
                    </div>
                    <div className="rounded-lg border p-2.5" style={{ borderColor: "var(--line)" }}>
                      <div className="text-muted">Peak Region</div>
                      <div className="font-mono text-sm font-medium">
                        {scanResult.summary.max_start && scanResult.summary.max_end
                          ? `aa ${scanResult.summary.max_start}–${scanResult.summary.max_end}`
                          : "—"}
                      </div>
                    </div>
                    <div className="rounded-lg border p-2.5" style={{ borderColor: "var(--line)" }}>
                      <div className="text-muted">Windows P ≥ 0.5</div>
                      <div className="font-mono text-base font-semibold">{scanResult.summary.n_windows_ge_0.5}</div>
                    </div>
                    <div className="rounded-lg border p-2.5" style={{ borderColor: "var(--line)" }}>
                      <div className="text-muted">Windows P ≥ 0.9</div>
                      <div className="font-mono text-base font-semibold">{scanResult.summary.n_windows_ge_0.9}</div>
                    </div>
                  </div>
                )}

                {/* Top Active Windows */}
                <div className="space-y-1.5 pt-2">
                  <div className="text-[11px] uppercase tracking-wider text-muted font-semibold">Active Windows Sample:</div>
                  <div className="max-h-48 overflow-y-auto space-y-1 text-xs font-mono">
                    {scanResult.windows.slice(0, 15).map((w, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between rounded p-1.5 border"
                        style={{ borderColor: "var(--line)" }}
                      >
                        <span>aa {w.start}–{w.end}: {w.seq.slice(0, 14)}...</span>
                        <span
                          className="px-1.5 py-0.5 rounded text-[10px] font-semibold"
                          style={
                            w.label === "AMP"
                              ? { background: "var(--accent)", color: "#07140f" }
                              : { background: "var(--bg-2)" }
                          }
                        >
                          {w.p_amp.toFixed(4)} ({w.label})
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Standard Peptide Classification Card */}
          {row?.pred?.valid && p && row.pred.secondary && !scanMode && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
              {row.ig?.train_set_warning && (
                <div className="rounded-xl border px-4 py-3 text-sm" style={{ borderColor: "var(--warn)", background: "var(--warn-bg)" }}>
                  Training-set sequence. {row.ig.canonical_name} = {row.ig.matched_train_id} is in the homology train fold.
                </div>
              )}
              <div className="panel p-6">
                <p className="mb-4 rounded-lg border px-3 py-2 text-sm leading-relaxed" style={{ borderColor: "var(--line)", color: "var(--text)" }}>
                  <strong>Trust this number.</strong> Calibrated RF P(AMP) {p.p_amp.toFixed(4)} is the
                  primary score. Label is AMP if P ≥ 0.5. It means this string looks more like DRAMP
                  AMPs than AMPlify non-AMPs on our homology-held-out test. It is not a killing assay.
                </p>
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

                {/* Nearest Training Set Homolog Card */}
                {nearest && (
                  <div className="mt-5 rounded-xl border p-3.5 text-xs space-y-1.5" style={{ borderColor: "var(--line)" }}>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-text flex items-center gap-1.5">
                        <Sparkles size={13} style={{ color: "var(--accent)" }} /> Nearest Train Peptide (MMseqs Wall)
                      </span>
                      {nearest.exact_match ? (
                        <span className="flex items-center gap-1 text-[11px] font-semibold text-amber-400">
                          <CheckCircle2 size={12} /> Exact Train Match
                        </span>
                      ) : nearest.identity !== null ? (
                        <span className="font-mono text-muted">
                          {(nearest.identity * 100).toFixed(1)}% identity (len {nearest.train_length})
                        </span>
                      ) : null}
                    </div>
                    <p className="text-muted leading-relaxed">
                      {nearest.train_id ? (
                        <>
                          Closest training sequence: <strong className="font-mono text-text">{nearest.train_id}</strong> ({nearest.train_label}). {nearest.note}
                        </>
                      ) : (
                        nearest.note
                      )}
                    </p>
                  </div>
                )}

                <div className="mt-5">
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

      {row?.ig?.valid && row.ig.residues.length > 0 && !scanMode && (
        <section className="membrane rounded-2xl p-6 pt-9">
          <div className="mb-4">
            <div className="text-xs uppercase tracking-[0.2em] text-muted">Integrated Gradients · CNN</div>
            <h2 className="font-display text-2xl">Residue track</h2>
            <p className="mt-3 max-w-3xl text-sm leading-relaxed text-muted">
              <strong style={{ color: "var(--text)" }}>This is the explanation.</strong> Each letter
              is one amino acid. Color and bar height are Integrated Gradients on the <em>CNN</em>{" "}
              AMP score: they show which residues pulled that network toward AMP (warm) or away
              (cool). Click a letter to read its IG value. This is not a wet-lab active site and not
              the Random Forest (the RF has no per-residue map). AMPlify can dump attention as
              numbers; this is the same idea, drawn.
            </p>
          </div>
          <ResidueHeatmap residues={row.ig.residues} onMutate={mutate} />
        </section>
      )}
    </div>
  );
}

