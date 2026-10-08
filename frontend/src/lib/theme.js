// Theme persistence helpers. Pure (storage and matchMedia are injected) so they are unit-testable.
export const THEME_KEY = "haggle-theme";

export function readStoredTheme(storage) {
  try {
    const v = storage?.getItem(THEME_KEY);
    return v === "light" || v === "dark" ? v : null;
  } catch {
    return null; // blocked storage (private mode) must never break the page
  }
}

export function systemTheme(matchMedia) {
  try {
    return matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  } catch {
    return "light";
  }
}

// An explicit choice wins; otherwise follow the operating system.
export const resolveTheme = (storage, matchMedia) => readStoredTheme(storage) ?? systemTheme(matchMedia);

export function storeTheme(storage, theme) {
  try {
    storage?.setItem(THEME_KEY, theme);
    return true;
  } catch {
    return false;
  }
}

export function applyTheme(root, theme) {
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
}
