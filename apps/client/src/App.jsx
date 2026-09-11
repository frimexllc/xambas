import { useState } from "react";
import { setAuthToken } from "./lib/api.js";
import { clearSession, loadSession, saveSession } from "./lib/session.js";
import { AuthFlow } from "./components/AuthFlow.jsx";
import { ClientHome } from "./panels/ClientHome.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";
import "./App.css";

// Rehidrata el token Bearer antes del primer render para que las llamadas
// autenticadas (recurring, ai-quote) funcionen tras recargar la página.
const initialSession = loadSession();
setAuthToken(initialSession?.token ?? null);

export default function App() {
  const [session, setSession] = useState(initialSession);
  const [error, setError] = useState(null);

  function handleAuthenticated(newSession) {
    saveSession(newSession);
    setAuthToken(newSession?.token ?? null);
    setSession(newSession);
  }

  function handleLogout() {
    clearSession();
    setAuthToken(null);
    setSession(null);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">X</span>
          <div>
            <h1>Xambas</h1>
            <p>Encuentra profesionales de confianza para tu hogar</p>
          </div>
        </div>
        <div className="header-right">
          <ThemeToggle />
          {session && (
            <button className="btn btn-ghost" onClick={handleLogout}>
              Cerrar sesion
            </button>
          )}
        </div>
      </header>

      {error && (
        <div className="banner banner-error" onClick={() => setError(null)}>
          {error} <span className="banner-dismiss">(clic para cerrar)</span>
        </div>
      )}

      <main className="app-main">
        {!session ? (
          <AuthFlow onAuthenticated={handleAuthenticated} onError={setError} />
        ) : (
          <ClientHome session={session} onError={setError} />
        )}
      </main>

      <footer className="app-footer">
        Xambas Cliente · Fase 0 · conectado a <code>{import.meta.env.VITE_API_BASE_URL}</code>
      </footer>
    </div>
  );
}
