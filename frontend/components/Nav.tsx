"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import Logo from "@/components/Logo";
import Toggles from "@/components/Toggles";
import { health } from "@/lib/api";

const links = [
  { href: "/", label: "Overview" },
  { href: "/predict", label: "Classify" },
  { href: "/metrics", label: "Evidence" },
  { href: "/about", label: "Limits" },
];

export default function Nav() {
  const path = usePathname();
  const [live, setLive] = useState<boolean | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    health()
      .then((h) => setLive(!!h.ok))
      .catch(() => setLive(false));
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [path]);

  return (
    <header className="sticky top-0 z-50">
      <div className="mx-auto max-w-7xl px-4 pt-3">
        <div
          className="flex items-center justify-between gap-3 rounded-2xl border px-3 py-2 backdrop-blur-xl"
          style={{
            borderColor: "var(--line)",
            background: "color-mix(in srgb, var(--surface) 78%, transparent)",
          }}
        >
          <Link href="/" className="flex shrink-0 items-center gap-2" style={{ color: "var(--accent)" }}>
            <Logo className="h-11 w-11" />
            <span className="font-display text-lg tracking-tight" style={{ color: "var(--text)" }}>
              AMPscan
            </span>
          </Link>

          <nav className="hidden items-center rounded-full p-1 md:flex" style={{ background: "var(--bg-2)" }}>
            {links.map((l) => {
              const on = path === l.href;
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className="rounded-full px-3.5 py-1.5 text-sm transition"
                  style={{
                    color: on ? "#07140f" : "var(--muted)",
                    background: on ? "var(--accent)" : "transparent",
                    fontWeight: on ? 600 : 400,
                  }}
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-2">
            <span
              className="hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] sm:inline-flex"
              style={{ borderColor: "var(--line)", color: "var(--muted)" }}
            >
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: live ? "var(--accent)" : live === false ? "#e07a5f" : "var(--muted)" }}
              />
              {live ? "models live" : live === false ? "API down" : "checking"}
            </span>
            <div className="hidden sm:block">
              <Toggles />
            </div>
            <button
              type="button"
              className="rounded-full border px-3 py-1 text-xs md:hidden"
              style={{ borderColor: "var(--line)" }}
              aria-expanded={open}
              onClick={() => setOpen((v) => !v)}
            >
              Menu
            </button>
          </div>
        </div>
        {open && (
          <div
            className="mt-2 space-y-3 rounded-2xl border p-3 md:hidden"
            style={{ borderColor: "var(--line)", background: "var(--surface)" }}
          >
            <div className="flex flex-wrap gap-2">
              {links.map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  className="rounded-full px-3 py-1 text-sm"
                  style={{
                    background: path === l.href ? "var(--accent)" : "var(--bg-2)",
                    color: path === l.href ? "#07140f" : "var(--text)",
                  }}
                >
                  {l.label}
                </Link>
              ))}
            </div>
            <Toggles />
          </div>
        )}
      </div>
    </header>
  );
}
