"use client";

import { useTheme } from "@/lib/theme";

export default function Toggles() {
  const { mode, toggle } = useTheme();
  const dark = mode === "dark";
  return (
    <label className="flex items-center gap-1.5 text-[11px] text-muted">
      {dark ? "Dark" : "Light"}
      <button
        type="button"
        className="switch"
        data-on={dark ? "true" : "false"}
        aria-pressed={dark}
        aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
        onClick={toggle}
      />
    </label>
  );
}
