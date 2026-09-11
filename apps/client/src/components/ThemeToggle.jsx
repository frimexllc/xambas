import { useEffect, useState } from "react";
import { getStoredTheme, getSystemTheme, setTheme } from "../theme";
import { SunIcon, MoonIcon } from "./icons";

// Botón que fuerza claro/oscuro sobre la preferencia del sistema. Mientras
// no se haya elegido nada explícito, sigue reflejando el cambio de tema del
// sistema en vivo (por si el usuario cambia su OS con la app abierta).
export default function ThemeToggle() {
  const [theme, setThemeState] = useState(() => getStoredTheme() || getSystemTheme());

  useEffect(() => {
    if (getStoredTheme()) return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e) => setThemeState(e.matches ? "dark" : "light");
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    setThemeState(next);
  }

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      title={theme === "dark" ? "Modo claro" : "Modo oscuro"}
    >
      {theme === "dark" ? <SunIcon size={17} /> : <MoonIcon size={17} />}
    </button>
  );
}
