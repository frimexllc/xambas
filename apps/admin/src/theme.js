// Selector de tema manual sobre el modo oscuro automático de HIG.
// Por defecto se sigue la preferencia del sistema (sin atributo). Al elegir
// explícitamente, se guarda en localStorage y se fuerza vía [data-theme] en
// <html>, que gana sobre prefers-color-scheme (ver reglas en App.css).
const STORAGE_KEY = "xambas-theme";

export function getStoredTheme() {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    return null;
  }
}

export function getSystemTheme() {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === "light" || theme === "dark") {
    root.setAttribute("data-theme", theme);
  } else {
    root.removeAttribute("data-theme");
  }
}

export function setTheme(theme) {
  try {
    if (theme === "light" || theme === "dark") {
      localStorage.setItem(STORAGE_KEY, theme);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    /* modo privado / storage deshabilitado: el tema no persiste, no es fatal */
  }
  applyTheme(theme);
}

// Se llama una vez al arrancar (antes de montar React) para evitar un
// flash del tema equivocado si ya había una preferencia explícita guardada.
export function initTheme() {
  applyTheme(getStoredTheme());
}
