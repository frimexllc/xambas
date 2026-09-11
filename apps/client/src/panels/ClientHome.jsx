import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { RequestsPanel } from "./RequestsPanel.jsx";
import { RecurringPanel } from "./RecurringPanel.jsx";
import { AiQuotePanel } from "./AiQuotePanel.jsx";
import { MilestonesPanel } from "./MilestonesPanel.jsx";

// Home del cliente: barra de pestañas + panel activo. Las categorías se cargan
// una vez y se pasan a los paneles que las necesitan para sus <select>.

const TABS = [
  { id: "requests", code: "S.01", label: "Solicitudes" },
  { id: "recurring", code: "S.02", label: "Recurrentes" },
  { id: "ai-quote", code: "S.03", label: "Cotización IA" },
  { id: "milestones", code: "S.04", label: "Pagos por etapas" },
];

export function ClientHome({ session, onError }) {
  const [categories, setCategories] = useState([]);
  const [view, setView] = useState("requests");

  useEffect(() => {
    api
      .listCategories()
      .then((response) => setCategories(response.items))
      .catch((err) => onError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="stack">
      <nav className="tab-bar" data-testid="client-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`tab ${view === tab.id ? "tab-active" : ""}`}
            onClick={() => setView(tab.id)}
            data-testid={`tab-${tab.id}`}
          >
            <span className="tab-code">{tab.code}</span>
            {tab.label}
          </button>
        ))}
      </nav>

      {view === "requests" && (
        <RequestsPanel session={session} categories={categories} onError={onError} />
      )}
      {view === "recurring" && (
        <RecurringPanel session={session} categories={categories} onError={onError} />
      )}
      {view === "ai-quote" && (
        <AiQuotePanel session={session} categories={categories} onError={onError} />
      )}
      {view === "milestones" && <MilestonesPanel session={session} onError={onError} />}
    </div>
  );
}
