import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef5ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          500: "#2563eb",
          600: "#1d4ed8",
          700: "#1e40af",
        },
        ink: {
          950: "#0f172a",
          900: "#172033",
          700: "#344054",
          600: "#475467",
          500: "#667085",
          400: "#98a2b3",
        },
        grid: {
          50: "#f8fafc",
          100: "#eef2f7",
          200: "#d8e0ea",
          300: "#c4cfdd",
          500: "#5d6b82",
          700: "#334155",
        },
        signal: {
          green: "#15803d",
          amber: "#b45309",
          red: "#be123c",
          blue: "#2563eb",
          teal: "#0f766e",
        },
      },
      boxShadow: {
        soft: "0 18px 45px rgba(15, 23, 42, 0.10)",
        panel: "0 1px 2px rgba(15, 23, 42, 0.06), 0 18px 48px rgba(15, 23, 42, 0.08)",
        button: "0 1px 1px rgba(15, 23, 42, 0.08), 0 8px 18px rgba(15, 23, 42, 0.08)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-up": "fade-up 220ms ease-out both",
        shimmer: "shimmer 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
