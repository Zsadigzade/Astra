import { useCallback, useEffect, useState } from "react";
import { applyTheme, readStoredTheme, resolveTheme, storeTheme, systemTheme } from "../lib/theme.js";

const store = () => { try { return window.localStorage; } catch { return null; } };

export default function useTheme() {
  const [theme, setTheme] = useState(() => resolveTheme(store(), window.matchMedia?.bind(window)));

  useEffect(() => { applyTheme(document.documentElement, theme); }, [theme]);

  // Until the person picks a theme themselves, keep following the operating system.
  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!mq?.addEventListener) return undefined;
    const onChange = () => { if (!readStoredTheme(store())) setTheme(systemTheme(window.matchMedia.bind(window))); };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const toggle = useCallback(() => {
    setTheme((t) => {
      const next = t === "dark" ? "light" : "dark";
      storeTheme(store(), next);
      return next;
    });
  }, []);

  return { theme, toggle };
}
