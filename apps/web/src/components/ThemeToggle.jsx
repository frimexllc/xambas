import { useEffect, useState } from "react";
import { getStoredTheme, getSystemTheme, setTheme } from "../theme";

const base = { fill: "none", xmlns: "http://www.w3.org/2000/svg" };

function SunIcon({ size = 17, color = "currentColor" }) {
  return (
    <svg {...base} width={size} height={size} viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="4.2" stroke={color} strokeWidth="1.4" />
      <path
        d="M12 2.8v2.4M12 18.8v2.4M4.9 4.9l1.7 1.7M17.4 17.4l1.7 1.7M2.8 12h2.4M18.8 12h2.4M4.9 19.1l1.7-1.7M17.4 6.6l1.7-1.7"
        stroke={color}
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function MoonIcon({ size = 17, color = "currentColor" }) {
  return (
    <svg {...base} width={size} height={size} viewBox="0 0 24 24">
      <path
        d="M20 14.2A8.2 8.2 0 1 1 9.8 4a6.4 6.4 0 0 0 10.2 10.2Z"
        stroke={color}
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}

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
      {theme === "dark" ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}
