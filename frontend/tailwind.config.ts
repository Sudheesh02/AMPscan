import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        moss: {
          DEFAULT: "#3dba8b",
          dim: "#1f6f54",
          ink: "#0c3d2e",
        },
        clay: "#e07a5f",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        lift: "0 24px 60px -28px rgba(0,0,0,0.55)",
      },
    },
  },
  plugins: [],
};

export default config;
