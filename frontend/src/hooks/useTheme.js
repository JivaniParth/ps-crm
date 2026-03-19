import { useEffect, useMemo, useState } from "react";

const THEME_KEY = "pscrm-theme";

export function useTheme() {
  const [theme, setTheme] = useState(() => {
    const persisted = localStorage.getItem(THEME_KEY);
    if (persisted === "dark" || persisted === "light") {
      return persisted;
    }
    return globalThis.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  return useMemo(
    () => ({
      theme,
      isDark: theme === "dark",
      toggleTheme
    }),
    [theme]
  );
}
