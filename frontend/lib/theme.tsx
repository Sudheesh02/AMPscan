"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

type Mode = "dark" | "light";

const Ctx = createContext<{
  mode: Mode;
  toggle: () => void;
  setMode: (m: Mode) => void;
}>({
  mode: "dark",
  toggle: () => {},
  setMode: () => {},
});

const KEY = "ampscan-theme";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<Mode>("dark");

  useEffect(() => {
    const stored = window.localStorage.getItem(KEY);
    const next: Mode = stored === "light" ? "light" : "dark";
    setModeState(next);
    applyTheme(next);
    document.documentElement.classList.remove("reduce-motion");
  }, []);

  function applyTheme(m: Mode) {
    document.documentElement.classList.toggle("dark", m === "dark");
  }

  const value = useMemo(
    () => ({
      mode,
      setMode: (m: Mode) => {
        setModeState(m);
        applyTheme(m);
        window.localStorage.setItem(KEY, m);
      },
      toggle: () => {
        setModeState((prev) => {
          const next: Mode = prev === "dark" ? "light" : "dark";
          applyTheme(next);
          window.localStorage.setItem(KEY, next);
          return next;
        });
      },
    }),
    [mode],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme() {
  return useContext(Ctx);
}
