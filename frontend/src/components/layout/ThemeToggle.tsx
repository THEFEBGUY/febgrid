import { Moon, Sun } from "lucide-react";

import type { ThemeMode } from "../../hooks/useTheme";

interface ThemeToggleProps {
  theme: ThemeMode;
  onToggle: () => void;
}

export function ThemeToggle({ theme, onToggle }: ThemeToggleProps): JSX.Element {
  const isDark = theme === "dark";
  const label = isDark ? "Switch to light mode" : "Switch to dark mode";

  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={isDark}
      title={label}
      className="relative inline-flex h-10 w-[4.25rem] shrink-0 items-center rounded-full border border-grid-200 bg-white p-1 text-ink-700 shadow-sm transition hover:border-grid-300 hover:bg-grid-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
      onClick={onToggle}
    >
      <span
        className={`absolute left-1 top-1 flex size-8 items-center justify-center rounded-full bg-brand-600 text-white shadow-button transition-transform ${
          isDark ? "translate-x-7" : "translate-x-0"
        }`}
        aria-hidden="true"
      >
        {isDark ? <Moon className="size-4" aria-hidden="true" /> : <Sun className="size-4" aria-hidden="true" />}
      </span>
      <span className="flex w-full items-center justify-between px-1.5" aria-hidden="true">
        <Sun className={`size-3.5 transition ${isDark ? "text-ink-500" : "text-amber-700"}`} />
        <Moon className={`size-3.5 transition ${isDark ? "text-blue-700" : "text-ink-500"}`} />
      </span>
    </button>
  );
}
