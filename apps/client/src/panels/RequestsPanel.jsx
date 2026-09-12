import { useEffect, useState } from "react";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { api } from "../lib/api.js";
import { getStripe, getStripeAppearance } from "../lib/stripe.js";
import { COUNTRY_CODE } from "../constants.js";
import { StatusBadge } from "../components/StatusBadge.jsx";
import { ChatPanel } from "../components/ChatPanel.jsx";
import { EmptyState } from "../components/EmptyState.jsx";
import { ClipboardIcon, SealIcon } from "../components/icons.jsx";

// Pestaña "Solicitudes": alta de solicitud + lista + detalle (matches, chat,
// pago en custodia, plan por etapas y reseña).

export function RequestsPanel({ session, categories, onError }) {
  const [requests, setRequests] = useState([]);
  const [selectedRequestId, setSelectedRequestId] = useState(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      const response = await api.listServiceRequests(session.userId);
      setRequests(response.items);
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

  if (selectedRequestId) {
    return (
      <RequestDetail
        session={session}
        requestId={selectedRequestId}
        onBack={() => {
          setSelectedRequestId(null);
          refresh();
        }}
        onError={onError}
      />
    );
  }

  return (
    <div className="grid-2">
      <section className="card">
        <h2>Nueva solicitud de servicio</h2>
        <NewRequestForm
          categories={categories}
          session={session}
          onCreated={(requestId) => setSelectedRequestId(requestId)}
          onError={onError}
        />
      </section>

      <section className="card">
        <h2>Tus solicitudes</h2>
        {loading && <p className="muted">Cargando...</p>}
        {!loading && requests.length === 0 && (
          <EmptyState
            icon={<ClipboardIcon />}
            title="Aún no tienes solicitudes"
            hint="Publica la primera a la izquierda y te conectamos con proveedores verificados en tu zona."
          />
        )}
        <ul className="request-list">
          {requests.map((request) => (
            <li key={request.id}>
              <button
                className="request-item"
                onClick={() => setSelectedRequestId(request.id)}
                data-testid={`request-item-${request.id}`}
              >
                <div>
                  <strong>{request.title}</strong>
                  <p className="muted">{request.category_name} · {request.city}</p>
                </div>
                <StatusBadge status={request.status} />
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function NewRequestForm({ categories, session, onCreated, onError }) {
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    categoryId: "",
    title: "",
    description: "",
    city: "",
    coverageZone: "",
    budgetAmount: "",
  });

  async function handleSubmit(event) {
    event.preventDefault();
    if (!form.categoryId) {
      onError("Selecciona una categoria.");
      return;
    }
    setSubmitting(true);
    try {
      const response = await api.createServiceRequest({
        client_id: session.userId,
        category_id: form.categoryId,
        title: form.title.trim(),
        description: form.description.trim(),
        country_code: COUNTRY_CODE,
        city: form.city.trim(),
        coverage_zone: form.coverageZone.trim(),
        budget_amount: form.budgetAmount ? Number(form.budgetAmount) : null,
      });
      onCreated(response.request.id);
    } catch (err) {
      onError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="stack">
      <label>
        <span className="field-label">Categoría</span>
        <select
          required
          value={form.categoryId}
          onChange={(e) => setForm({ ...form, categoryId: e.target.value })}
        >
          <option value="">Selecciona una categoria</option>
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
          placeholder="Fuga de agua en la cocina"
        />
      </label>
      <label>
        <span className="field-label">Descripción</span>
        <textarea
          required
          minLength={10}
          maxLength={2000}
          rows={3}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          placeholder="Cuentanos que necesitas, desde cuando y cualquier detalle util"
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
          />
        </label>
        <label>
          <span className="field-label">Zona de cobertura</span>
          <input
            required
            value={form.coverageZone}
            onChange={(e) => setForm({ ...form, coverageZone: e.target.value })}
            placeholder="CDMX-Centro"
          />
        </label>
      </div>
      <label>
        <span className="field-label">Presupuesto aproximado (opcional)</span>
        <input
          type="number"
          min="0"
          value={form.budgetAmount}
          onChange={(e) => setForm({ ...form, budgetAmount: e.target.value })}
          placeholder="500"
        />
      </label>
      <button className="btn btn-primary" type="submit" disabled={submitting}>
        {submitting ? "Buscando proveedores..." : "Publicar y buscar proveedores"}
      </button>
    </form>
  );
}

function RequestDetail({ session, requestId, onBack, onError }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeMatchId, setActiveMatchId] = useState(null);
  const [reviewMatchId, setReviewMatchId] = useState(null);
  const [paymentMatchId, setPaymentMatchId] = useState(null);
  const [milestoneMatchId, setMilestoneMatchId] = useState(null);

  async function refresh() {
    setLoading(true);
    try {
      const response = await api.getServiceRequest(requestId);
      setData(response);
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestId]);

  async function handleRerun() {
    try {
      await api.rerunMatching(requestId);
      refresh();
    } catch (err) {
      onError(err.message);
    }
  }

  if (loading || !data) {
    return <p className="muted">Cargando solicitud...</p>;
  }

  const { request, matches } = data;

  return (
    <div className="stack">
      <button className="btn btn-ghost" onClick={onBack}>
        ← Volver
      </button>

      <section className="card">
        <div className="space-between">
          <div>
            <h2>{request.title}</h2>
            <p className="muted">
              {request.category_name} · {request.city} ({request.coverage_zone})
            </p>
          </div>
          <StatusBadge status={request.status} />
        </div>
        <p>{request.description}</p>
        <button className="btn btn-secondary" onClick={handleRerun}>
          Volver a buscar proveedores
        </button>
      </section>

      <section className="card">
        <h3>Proveedores sugeridos ({matches.length})</h3>
        {matches.length === 0 && (
          <p className="muted">Aun no hay proveedores disponibles en tu zona para esta categoria.</p>
        )}
        <ul className="match-list">
          {matches.map((match) => (
            <li key={match.id} className="match-item">
              <div className="space-between">
                <div>
                  <strong>{match.provider_business_name}</strong>
                  <p className="muted">
                    <span className="mono">{match.score} pts</span> · {match.reasons.join(", ")}
                  </p>
                </div>
                <StatusBadge status={match.status} />
              </div>
              <div className="row">
                <button className="btn btn-secondary" onClick={() => setActiveMatchId(match.id)}>
                  Chatear
                </button>
                {match.status === "accepted" && (
                  <button className="btn btn-primary" onClick={() => setPaymentMatchId(match.id)}>
                    Pagar y reservar
                  </button>
                )}
                {match.status === "accepted" && (
                  <button
                    className="btn btn-secondary"
                    onClick={() => setMilestoneMatchId(match.id)}
                    data-testid={`create-milestones-${match.id}`}
                  >
                    Plan por etapas
                  </button>
                )}
                {match.status === "accepted" && (
                  <button className="btn btn-secondary" onClick={() => setReviewMatchId(match)}>
                    Dejar resena
                  </button>
                )}
              </div>
              {activeMatchId === match.id && (
                <ChatPanel
                  matchId={match.id}
                  senderId={session.userId}
                  senderRole="client"
                  onClose={() => setActiveMatchId(null)}
                  onError={onError}
                />
              )}
              {paymentMatchId === match.id && (
                <PaymentPanel
                  match={match}
                  session={session}
                  onClose={() => setPaymentMatchId(null)}
                  onError={onError}
                />
              )}
              {milestoneMatchId === match.id && (
                <MilestonePlanCreator
                  matchId={match.id}
                  session={session}
                  onClose={() => setMilestoneMatchId(null)}
                  onError={onError}
                />
              )}
              {reviewMatchId?.id === match.id && (
                <ReviewForm
                  requestId={request.id}
                  clientId={session.userId}
                  match={match}
                  onDone={() => setReviewMatchId(null)}
                  onError={onError}
                />
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

// Pago en custodia (Stripe): deposito, estado y liberacion al confirmar.

const PAYMENT_STATUS_LABELS = {
  pending: "Pendiente de pago",
  held_in_escrow: "En custodia (pagado)",
  released: "Liberado al proveedor",
  refunded: "Reembolsado",
  failed: "Fallido",
  cancelled: "Cancelado",
};

function PaymentPanel({ match, session, onClose, onError }) {
  const [payment, setPayment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [jobAmount, setJobAmount] = useState("");
  const [creating, setCreating] = useState(false);
  const [checkout, setCheckout] = useState(null); // { clientSecret, publishableKey }
  const [confirming, setConfirming] = useState(false);

  async function loadExisting() {
    setLoading(true);
    try {
      const response = await api.listPaymentsForClient(session.userId);
      const active = response.items.find(
        (item) =>
          item.match_id === match.id && !["refunded", "cancelled", "failed"].includes(item.status)
      );
      setPayment(active || null);
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadExisting();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [match.id]);

  async function handleCreatePayment(event) {
    event.preventDefault();
    const amount = Number(jobAmount);
    if (!amount || amount <= 0) {
      onError("Ingresa un monto valido para el trabajo.");
      return;
    }
    setCreating(true);
    try {
      const response = await api.createPayment({
        match_id: match.id,
        client_id: session.userId,
        job_amount: amount,
      });
      setPayment(response.payment);
      if (response.client_secret) {
        setCheckout({ clientSecret: response.client_secret, publishableKey: response.publishable_key });
      }
    } catch (err) {
      onError(err.message);
    } finally {
      setCreating(false);
    }
  }

  async function handlePaid() {
    setCheckout(null);
    await refreshPaymentStatus();
  }

  async function refreshPaymentStatus() {
    if (!payment) return;
    try {
      const updated = await api.getPayment(payment.id);
      setPayment(updated);
    } catch (err) {
      onError(err.message);
    }
  }

  async function handleConfirmCompletion() {
    if (!payment) return;
    setConfirming(true);
    try {
      const updated = await api.confirmCompletion(payment.id, session.userId);
      setPayment(updated);
    } catch (err) {
      onError(err.message);
    } finally {
      setConfirming(false);
    }
  }

  return (
    <div className="payment-panel">
      <div className="space-between">
        <strong>Pago del trabajo</strong>
        <button className="btn btn-ghost" onClick={onClose}>
          Cerrar
        </button>
      </div>

      {loading && <p className="muted">Cargando...</p>}

      {!loading && !payment && !checkout && (
        <form onSubmit={handleCreatePayment} className="stack">
          <p className="muted">
            Acuerda el precio final con el proveedor por chat y captura aqui el monto para pagar de
            forma segura. El dinero queda retenido hasta que confirmes que el trabajo esta terminado.
          </p>
          <label>
            <span className="field-label">Monto acordado (MXN)</span>
            <input
              type="number"
              min="1"
              step="0.01"
              required
              value={jobAmount}
              onChange={(e) => setJobAmount(e.target.value)}
              placeholder="1200"
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={creating}>
            {creating ? "Generando pago..." : "Continuar al pago"}
          </button>
        </form>
      )}

      {checkout && (
        <Elements
          stripe={getStripe(checkout.publishableKey)}
          options={{ clientSecret: checkout.clientSecret, appearance: getStripeAppearance() }}
        >
          <CheckoutForm onPaid={handlePaid} onError={onError} />
        </Elements>
      )}

      {!loading && payment && !checkout && (
        <div className="stack">
          <div className="payment-summary">
            <div className="space-between">
              <span>Monto del trabajo</span>
              <strong className="mono">${payment.job_amount.toFixed(2)} {payment.currency.toUpperCase()}</strong>
            </div>
            <div className="space-between">
              <span>Tarifa de servicio</span>
              <span className="mono">${payment.client_fee_amount.toFixed(2)}</span>
            </div>
            <div className="space-between">
              <span>Total pagado</span>
              <strong className="mono">${payment.client_total.toFixed(2)}</strong>
            </div>
            <div className="space-between">
              <span>Estado</span>
              <span className={`badge payment-status-${payment.status}`}>
                {PAYMENT_STATUS_LABELS[payment.status] || payment.status}
              </span>
            </div>
          </div>

          {payment.status === "pending" && (
            <button className="btn btn-secondary" onClick={refreshPaymentStatus}>
              Actualizar estado del pago
            </button>
          )}

          {payment.status === "held_in_escrow" && (
            <button className="btn btn-primary" onClick={handleConfirmCompletion} disabled={confirming}>
              {confirming ? "Liberando pago..." : "Confirmar trabajo terminado y liberar pago"}
            </button>
          )}

          {payment.status === "released" && (
            <span className="trust-seal">
              <SealIcon size={18} />
              Pago liberado al proveedor
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function CheckoutForm({ onPaid, onError }) {
  const stripe = useStripe();
  const elements = useElements();
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!stripe || !elements) return;
    setSubmitting(true);
    try {
      const { error, paymentIntent } = await stripe.confirmPayment({
        elements,
        redirect: "if_required",
      });
      if (error) {
        onError(error.message || "No se pudo confirmar el pago.");
        return;
      }
      if (paymentIntent && (paymentIntent.status === "succeeded" || paymentIntent.status === "processing")) {
        onPaid();
      } else {
        onError("El pago no se completo. Intenta de nuevo.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="stack">
      <PaymentElement />
      <button className="btn btn-primary" type="submit" disabled={!stripe || submitting}>
        {submitting ? "Procesando pago..." : "Pagar de forma segura"}
      </button>
    </form>
  );
}

function ReviewForm({ requestId, clientId, match, onDone, onError }) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.createReview({
        request_id: requestId,
        provider_profile_id: match.provider_profile_id,
        client_id: clientId,
        rating: Number(rating),
        comment: comment.trim() || null,
      });
      onDone();
    } catch (err) {
      onError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="review-form stack">
      <label>
        Calificacion
        <select value={rating} onChange={(e) => setRating(e.target.value)}>
          {[5, 4, 3, 2, 1].map((value) => (
            <option key={value} value={value}>
              {"★".repeat(value)}
              {"☆".repeat(5 - value)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Comentario (opcional)
        <textarea
          rows={2}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Como fue tu experiencia?"
        />
      </label>
      <button className="btn btn-primary" type="submit" disabled={submitting}>
        {submitting ? "Enviando..." : "Enviar resena"}
      </button>
    </form>
  );
}

// Pagos por etapas (hitos): crear el plan desde un trabajo aceptado.

function MilestonePlanCreator({ matchId, session, onClose, onError }) {
  const [rows, setRows] = useState([{ title: "", amount: "" }]);
  const [saving, setSaving] = useState(false);
  const [created, setCreated] = useState(false);

  function updateRow(index, field, value) {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, [field]: value } : r)));
  }

  async function handleCreate(event) {
    event.preventDefault();
    const milestones = rows
      .filter((r) => r.title.trim() && Number(r.amount) > 0)
      .map((r) => ({ title: r.title.trim(), amount: Number(r.amount) }));
    if (milestones.length === 0) return onError("Agrega al menos una etapa con título y monto.");
    setSaving(true);
    try {
      await api.createMilestonePlan({ match_id: matchId, client_id: session.userId, currency: "MXN", milestones });
      setCreated(true);
    } catch (err) {
      onError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (created) {
    return (
      <div className="payment-panel">
        <p className="hint" data-testid="milestone-plan-created">
          Plan por etapas creado. Gestiónalo en la pestaña "Pagos por etapas".
        </p>
        <button className="btn btn-ghost" onClick={onClose}>Cerrar</button>
      </div>
    );
  }

  return (
    <form onSubmit={handleCreate} className="payment-panel stack" data-testid="milestone-creator">
      <div className="space-between">
        <strong>Nuevo plan por etapas</strong>
        <button type="button" className="btn btn-ghost" onClick={onClose}>Cerrar</button>
      </div>
      <p className="muted">Divide el trabajo en fases; el proveedor sube evidencia y tú liberas cada pago.</p>
      {rows.map((row, index) => (
        <div className="row" key={index}>
          <input
            placeholder="Etapa (ej. Anticipo)"
            value={row.title}
            onChange={(e) => updateRow(index, "title", e.target.value)}
            data-testid={`milestone-title-${index}`}
          />
          <input
            type="number"
            min="1"
            placeholder="Monto"
            value={row.amount}
            onChange={(e) => updateRow(index, "amount", e.target.value)}
            data-testid={`milestone-amount-${index}`}
          />
        </div>
      ))}
      <div className="row">
        <button type="button" className="btn btn-ghost" onClick={() => setRows([...rows, { title: "", amount: "" }])}>
          + Añadir etapa
        </button>
        <button className="btn btn-primary" type="submit" disabled={saving} data-testid="milestone-create-btn">
          {saving ? "Creando..." : "Crear plan"}
        </button>
      </div>
    </form>
  );
}
