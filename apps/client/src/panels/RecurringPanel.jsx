import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { COUNTRY_CODE } from "../constants.js";
import { EmptyState } from "../components/EmptyState.jsx";
import { RepeatIcon } from "../components/icons.jsx";

// Servicios recurrentes: suscripciones y visitas programadas.

const FREQUENCY_LABELS = {
  weekly: "Semanal",
  biweekly: "Quincenal",
  monthly: "Mensual",
};

const SUBSCRIPTION_STATUS_LABELS = {
  active: "Activa",
  paused: "En pausa",
  cancelled: "Cancelada",
};

export function RecurringPanel({ session, categories, onError }) {
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openOccurrencesId, setOpenOccurrencesId] = useState(null);

  async function refresh() {
    setLoading(true);
    try {
      const response = await api.listSubscriptions(session.userId);
      setSubscriptions(response.items);
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

  return (
    <div className="grid-2" data-testid="recurring-panel">
      <section className="card">
        <h2>Nueva suscripción</h2>
        <p className="muted">
          Programa un servicio que se repite (limpieza semanal, mantenimiento mensual) y genera
          cada visita con proveedores verificados, sin volver a publicar desde cero.
        </p>
        <NewSubscriptionForm
          categories={categories}
          session={session}
          onCreated={refresh}
          onError={onError}
        />
      </section>

      <section className="card">
        <h2>Tus suscripciones</h2>
        {loading && <p className="muted">Cargando...</p>}
        {!loading && subscriptions.length === 0 && (
          <EmptyState
            icon={<RepeatIcon />}
            title="Aún no tienes servicios recurrentes"
            hint="Programa uno a la izquierda (limpieza semanal, mantenimiento mensual) y generamos cada visita automáticamente."
          />
        )}
        <ul className="request-list" data-testid="subscription-list">
          {subscriptions.map((subscription) => (
            <SubscriptionItem
              key={subscription.id}
              subscription={subscription}
              isOpen={openOccurrencesId === subscription.id}
              onToggleOccurrences={() =>
                setOpenOccurrencesId(
                  openOccurrencesId === subscription.id ? null : subscription.id
                )
              }
              onChanged={refresh}
              onError={onError}
            />
          ))}
        </ul>
      </section>
    </div>
  );
}

function NewSubscriptionForm({ categories, session, onCreated, onError }) {
  const [submitting, setSubmitting] = useState(false);
  const emptyForm = {
    categoryId: "",
    title: "",
    description: "",
    city: "",
    coverageZone: "",
    frequency: "weekly",
    budgetAmount: "",
    startDate: "",
    preferredTime: "",
  };
  const [form, setForm] = useState(emptyForm);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!form.categoryId) {
      onError("Selecciona una categoría.");
      return;
    }
    setSubmitting(true);
    try {
      await api.createSubscription({
        client_id: session.userId,
        category_id: form.categoryId,
        title: form.title.trim(),
        description: form.description.trim(),
        country_code: COUNTRY_CODE,
        city: form.city.trim(),
        coverage_zone: form.coverageZone.trim(),
        frequency: form.frequency,
        budget_amount: form.budgetAmount ? Number(form.budgetAmount) : null,
        start_date: form.startDate || null,
        preferred_time: form.preferredTime.trim() || null,
      });
      setForm(emptyForm);
      onCreated();
    } catch (err) {
      onError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="stack" data-testid="new-subscription-form">
      <label>
        <span className="field-label">Categoría</span>
        <select
          required
          value={form.categoryId}
          onChange={(e) => setForm({ ...form, categoryId: e.target.value })}
          data-testid="subscription-category-select"
        >
          <option value="">Selecciona una categoría</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.parent_id ? `— ${category.name}` : category.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="field-label">Título</span>
        <input
          required
          minLength={4}
          maxLength={140}
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          placeholder="Limpieza semanal del departamento"
          data-testid="subscription-title-input"
        />
      </label>
      <label>
        <span className="field-label">Descripción</span>
        <textarea
          required
          minLength={10}
          maxLength={2000}
          rows={2}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          placeholder="Qué necesitas en cada visita"
          data-testid="subscription-description-input"
        />
      </label>
      <div className="row">
        <label>
          <span className="field-label">Ciudad</span>
          <input
            required
            value={form.city}
            onChange={(e) => setForm({ ...form, city: e.target.value })}
            placeholder="CDMX"
            data-testid="subscription-city-input"
          />
        </label>
        <label>
          <span className="field-label">Zona de cobertura</span>
          <input
            required
            value={form.coverageZone}
            onChange={(e) => setForm({ ...form, coverageZone: e.target.value })}
            placeholder="Roma Norte"
            data-testid="subscription-zone-input"
          />
        </label>
      </div>
      <div className="row">
        <label>
          <span className="field-label">Frecuencia</span>
          <select
            value={form.frequency}
            onChange={(e) => setForm({ ...form, frequency: e.target.value })}
            data-testid="subscription-frequency-select"
          >
            {Object.entries(FREQUENCY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="field-label">Primera visita (opcional)</span>
          <input
            type="date"
            value={form.startDate}
            onChange={(e) => setForm({ ...form, startDate: e.target.value })}
            data-testid="subscription-start-input"
          />
        </label>
      </div>
      <div className="row">
        <label>
          <span className="field-label">Presupuesto por visita (opcional)</span>
          <input
            type="number"
            min="0"
            value={form.budgetAmount}
            onChange={(e) => setForm({ ...form, budgetAmount: e.target.value })}
            placeholder="450"
            data-testid="subscription-budget-input"
          />
        </label>
        <label>
          <span className="field-label">Horario preferido (opcional)</span>
          <input
            value={form.preferredTime}
            onChange={(e) => setForm({ ...form, preferredTime: e.target.value })}
            placeholder="10:00"
            data-testid="subscription-time-input"
          />
        </label>
      </div>
      <button
        className="btn btn-primary"
        type="submit"
        disabled={submitting}
        data-testid="subscription-submit-btn"
      >
        {submitting ? "Creando suscripción..." : "Crear servicio recurrente"}
      </button>
    </form>
  );
}

function SubscriptionItem({ subscription, isOpen, onToggleOccurrences, onChanged, onError }) {
  const [busy, setBusy] = useState(false);

  async function runAction(action) {
    setBusy(true);
    try {
      await action();
      onChanged();
    } catch (err) {
      onError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const isActive = subscription.status === "active";
  const isCancelled = subscription.status === "cancelled";

  return (
    <li className="match-item" data-testid={`subscription-item-${subscription.id}`}>
      <div className="space-between">
        <div>
          <strong>{subscription.title}</strong>
          <p className="muted">
            {subscription.category_name} · {FREQUENCY_LABELS[subscription.frequency]} ·{" "}
            {subscription.coverage_zone}
          </p>
        </div>
        <span className={`badge badge-${subscription.status}`}>
          {SUBSCRIPTION_STATUS_LABELS[subscription.status] || subscription.status}
        </span>
      </div>

      <div className="sub-meta">
        <span>
          Próxima visita: <strong>{subscription.next_run_date}</strong>
        </span>
        <span>
          Visitas generadas: <strong>{subscription.occurrences_count}</strong>
        </span>
        {subscription.budget_amount != null && (
          <span>
            Presupuesto: <strong>${subscription.budget_amount}</strong>
          </span>
        )}
      </div>

      <div className="row sub-actions">
        {isActive && (
          <button
            className="btn btn-primary"
            disabled={busy}
            onClick={() => runAction(() => api.generateOccurrence(subscription.id))}
            data-testid={`subscription-generate-${subscription.id}`}
          >
            {busy ? "Generando..." : "Generar próxima visita"}
          </button>
        )}
        {isActive && (
          <button
            className="btn btn-secondary"
            disabled={busy}
            onClick={() => runAction(() => api.pauseSubscription(subscription.id))}
            data-testid={`subscription-pause-${subscription.id}`}
          >
            Pausar
          </button>
        )}
        {subscription.status === "paused" && (
          <button
            className="btn btn-secondary"
            disabled={busy}
            onClick={() => runAction(() => api.resumeSubscription(subscription.id))}
            data-testid={`subscription-resume-${subscription.id}`}
          >
            Reanudar
          </button>
        )}
        {!isCancelled && (
          <button
            className="btn btn-ghost"
            disabled={busy}
            onClick={() => runAction(() => api.cancelSubscription(subscription.id))}
            data-testid={`subscription-cancel-${subscription.id}`}
          >
            Cancelar
          </button>
        )}
        {subscription.occurrences_count > 0 && (
          <button
            className="btn btn-ghost"
            onClick={onToggleOccurrences}
            data-testid={`subscription-occurrences-${subscription.id}`}
          >
            {isOpen ? "Ocultar visitas" : "Ver visitas"}
          </button>
        )}
      </div>

      {isOpen && <OccurrencesList subscriptionId={subscription.id} onError={onError} />}
    </li>
  );
}

function OccurrencesList({ subscriptionId, onError }) {
  const [occurrences, setOccurrences] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const response = await api.listOccurrences(subscriptionId);
        setOccurrences(response.items);
      } catch (err) {
        onError(err.message);
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subscriptionId]);

  if (loading) return <p className="muted">Cargando visitas...</p>;
  if (occurrences.length === 0) return <p className="muted">Sin visitas generadas todavía.</p>;

  return (
    <ul className="occurrence-list" data-testid={`occurrences-${subscriptionId}`}>
      {occurrences.map((occurrence, index) => (
        <li key={occurrence.id} className="occurrence-item">
          <span>Visita #{occurrences.length - index}</span>
          <strong>{occurrence.scheduled_date}</strong>
        </li>
      ))}
    </ul>
  );
}
