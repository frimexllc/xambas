import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

// Pagos por etapas (hitos): el cliente libera cada fase cuando el proveedor
// sube evidencia y él la aprueba. El plan se crea desde un trabajo aceptado.

const MS_STATUS_LABELS = { pending: "Pendiente", submitted: "Evidencia enviada", released: "Pagada" };

export function MilestonesPanel({ session, onError }) {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      const response = await api.listMilestonePlansForClient(session.userId);
      setPlans(response.items);
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function release(planId, milestoneId) {
    try {
      await api.releaseMilestone(planId, milestoneId, session.userId);
      refresh();
    } catch (err) {
      onError(err.message);
    }
  }

  return (
    <section className="card" data-testid="milestones-panel">
      <h2>Pagos por etapas</h2>
      <p className="muted">
        Para trabajos grandes: liberas el pago fase por fase, solo cuando el proveedor sube evidencia
        y tú la apruebas. Crea un plan desde un trabajo aceptado en “Solicitudes”.
      </p>
      {loading && <p className="muted">Cargando...</p>}
      {!loading && plans.length === 0 && <p className="muted">Aún no tienes planes por etapas.</p>}
      <ul className="request-list" data-testid="milestones-plan-list">
        {plans.map((plan) => (
          <li key={plan.id} className="match-item" data-testid={`plan-${plan.id}`}>
            <div className="space-between">
              <strong>Trabajo #{plan.request_id.slice(-6)}</strong>
              <span className="muted">
                Liberado ${plan.released_amount} / ${plan.total_amount} {plan.currency}
              </span>
            </div>
            <ul className="milestone-list">
              {plan.milestones.map((milestone) => (
                <li key={milestone.id} className="milestone-row">
                  <div className="space-between">
                    <span>{milestone.title} · <strong>${milestone.amount}</strong></span>
                    <span className={`badge badge-${milestone.status}`}>
                      {MS_STATUS_LABELS[milestone.status]}
                    </span>
                  </div>
                  {milestone.evidence.length > 0 && (
                    <div className="quote-thumbs">
                      {milestone.evidence.map((ev) => (
                        <img key={ev.path} src={ev.url} alt="evidencia" className="quote-thumb" />
                      ))}
                    </div>
                  )}
                  {milestone.status === "submitted" && (
                    <button
                      className="btn btn-primary"
                      onClick={() => release(plan.id, milestone.id)}
                      data-testid={`release-${milestone.id}`}
                    >
                      Aprobar y liberar pago
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}
