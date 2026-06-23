import { useCallback, useEffect, useState } from "react";

export type ThemeMode = "light" | "dark";

const storageKey = "febgrid-theme";

function readStoredTheme(): ThemeMode {
  try {
    return window.localStorage.getItem(storageKey) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

function applyTheme(theme: ThemeMode): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.dataset.theme = theme;
}

export function useTheme(): { theme: ThemeMode; toggleTheme: () => void } {
  const [theme, setTheme] = useState<ThemeMode>(() => readStoredTheme());

  useEffect(() => {
    applyTheme(theme);
    try {
      window.localStorage.setItem(storageKey, theme);
    } catch {
      // Theme persistence is non-critical; the UI still updates for this session.
    }
  }, [theme]);

  const toggleTheme = useCallback((): void => {
    setTheme((currentTheme) => (currentTheme === "dark" ? "light" : "dark"));
  }, []);

  return { theme, toggleTheme };
}
