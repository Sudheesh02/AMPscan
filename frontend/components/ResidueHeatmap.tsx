"use client";

import { useMemo, useRef, useState } from "react";
import type { Residue } from "@/lib/api";
import { AA20, THREE } from "@/lib/aa";

type Props = {
  residues: Residue[];
  onMutate?: (pos1: number, aa: string) => void;
};

export default function ResidueHeatmap({ residues, onMutate }: { residues: Residue[]; onMutate?: Props["onMutate"] }) {
  const wrap = useRef<HTMLDivElement>(null);
  const [pick, setPick] = useState(0);
  const [mode, setMode] = useState<"signed" | "abs">("signed");
  const [cb, setCb] = useState(false);
  const vmax = Math.max(...residues.map((r) => Math.abs(r.ig)), 1e-8);
  const chosen = residues[pick];

  const amp = cb ? "rgb(234, 88, 12)" : "var(--amp)";
  const neg = cb ? "rgb(37, 99, 235)" : "var(--neg)";

  const colors = useMemo(
    () =>
      residues.map((r) => {
        const t = mode === "abs" ? Math.abs(r.ig) / vmax : r.ig / vmax;
        if (mode === "abs") return `color-mix(in srgb, ${amp} ${Math.round(18 + 82 * t)}%, transparent)`;
        return t >= 0
          ? `color-mix(in srgb, ${amp} ${Math.round(18 + 82 * t)}%, transparent)`
          : `color-mix(in srgb, ${neg} ${Math.round(18 + 82 * -t)}%, transparent)`;
      }),
    [residues, mode, vmax, amp, neg],
  );

  function exportSvg() {
    const el = wrap.current?.querySelector("svg");
    if (!el) return;
    const blob = new Blob([el.outerHTML], { type: "image/svg+xml" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "ampscan-ig.svg";
    a.click();
  }

  function exportPng() {
    const svg = wrap.current?.querySelector("svg");
    if (!svg) return;
    const xml = new XMLSerializer().serializeToString(svg);
    const img = new Image();
    const box = svg.getBoundingClientRect();
    img.onload = () => {
      const c = document.createElement("canvas");
      c.width = Math.max(800, box.width * 2);
      c.height = Math.max(200, box.height * 2);
      const ctx = c.getContext("2d");
      if (!ctx) return;
      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--surface") || "#10151a";
      ctx.fillRect(0, 0, c.width, c.height);
      ctx.drawImage(img, 0, 0, c.width, c.height);
      const a = document.createElement("a");
      a.href = c.toDataURL("image/png");
      a.download = "ampscan-ig.png";
      a.click();
    };
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);
  }

  const w = Math.max(residues.length * 28, 640);
  const h = 160;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2 text-xs">
          <Toggle on={mode === "signed"} onClick={() => setMode("signed")} label="signed" />
          <Toggle on={mode === "abs"} onClick={() => setMode("abs")} label="absolute" />
          <Toggle on={!cb} onClick={() => setCb(false)} label="default" />
          <Toggle on={cb} onClick={() => setCb(true)} label="colorblind" />
        </div>
        <div className="flex gap-2 text-xs">
          <button type="button" className="rounded-full border px-3 py-1" style={{ borderColor: "var(--line)" }} onClick={exportSvg}>
            Export SVG
          </button>
          <button type="button" className="rounded-full border px-3 py-1" style={{ borderColor: "var(--line)" }} onClick={exportPng}>
            Export PNG
          </button>
        </div>
      </div>

      <div ref={wrap} className="overflow-x-auto">
        <svg width="100%" viewBox={`0 0 ${w} ${h}`} className="min-w-full">
          {residues.map((r, i) => {
            const x = i * (w / residues.length);
            const cw = w / residues.length;
            const mag = Math.abs(r.ig) / vmax;
            const barH = 8 + mag * 70;
            const up = mode === "abs" ? true : r.ig >= 0;
            return (
              <g key={r.pos} onClick={() => setPick(i)} className="cursor-pointer">
                <rect x={x} y={0} width={cw} height={h} fill={pick === i ? "var(--bg-2)" : "transparent"} />
                <rect
                  x={x + cw * 0.28}
                  y={up ? 88 - barH : 88}
                  width={cw * 0.44}
                  height={barH}
                  rx="2"
                  fill={up ? amp : neg}
                  opacity={0.35 + 0.65 * mag}
                />
                <rect x={x + 2} y={96} width={cw - 4} height={28} rx="4" fill={colors[i]} />
                <text x={x + cw / 2} y={115} textAnchor="middle" fontSize="12" fontFamily="ui-monospace, monospace" fill="var(--text)">
                  {r.aa}
                </text>
                <text x={x + cw / 2} y={142} textAnchor="middle" fontSize="9" fontFamily="ui-monospace, monospace" fill="var(--muted)">
                  {r.pos}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {chosen && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
          <p className="font-mono text-muted">
            {chosen.pos} · {chosen.aa} · {THREE[chosen.aa] ?? "Xaa"} · IG {chosen.ig.toFixed(4)}
          </p>
          {onMutate && (
            <label className="flex items-center gap-2 text-xs text-muted">
              Mutate
              <select
                className="rounded-md border bg-transparent px-2 py-1 font-mono"
                style={{ borderColor: "var(--line)", color: "var(--text)" }}
                value={chosen.aa}
                onChange={(e) => onMutate(chosen.pos, e.target.value)}
              >
                {[...AA20].map((a) => (
                  <option key={a} value={a}>
                    {a} {THREE[a]}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      )}
    </div>
  );
}

function Toggle({ on, onClick, label }: { on: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full px-3 py-1"
      style={{
        background: on ? "var(--accent)" : "transparent",
        color: on ? "#07140f" : "var(--text)",
        border: "1px solid var(--line)",
      }}
    >
      {label}
    </button>
  );
}
