import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#10151f",
          900: "#17202e",
          700: "#354154",
          500: "#667085",
        },
        grid: {
          50: "#f6f7f9",
          100: "#ebeef2",
          200: "#d9dee7",
          500: "#5d6b82",
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
        soft: "0 10px 30px rgba(16, 21, 31, 0.08)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
