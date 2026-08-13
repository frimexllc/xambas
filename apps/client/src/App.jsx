import { useEffect, useState } from "react";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { api } from "./lib/api.js";
import { getStripe } from "./lib/stripe.js";
import { clearSession, loadSession, saveSession } from "./lib/session.js";
import "./App.css";

const COUNTRY_CODE = "MX";

export default function App() {
  const [session, setSession] = useState(() => loadSession());
  const [error, setError] = useState(null);

  function handleAuthenticated(newSession) {
    saveSession(newSession);
    setSession(newSession);
  }

  function handleLogout() {
    clearSession();
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
        {session && (
          <button className="btn btn-ghost" onClick={handleLogout}>
            Cerrar sesion
          </button>
        )}
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

// ---------------------------------------------------------------------------
// Autenticacion: bootstrap + verificacion OTP
// ---------------------------------------------------------------------------

function AuthFlow({ onAuthenticated, onError }) {
  const [step, setStep] = useState("register"); // register | otp
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ email: "", phone: "" });
  const [otpState, setOtpState] = useState(null); // { userId, challengeId, debugCode }
  const [code, setCode] = useState("");

  async function handleRegister(event) {
    event.preventDefault();
    setLoading(true);
    try {
      const result = await api.bootstrap({
        email: form.email.trim(),
        phone: form.phone.trim(),
        role: "client",
        locale: "es-MX",
      });
      const userId = result.user.id;
      const otp = await api.requestOtp({ user_id: userId, purpose: "registration", channel: "sms" });
      setOtpState({ userId, challengeId: otp.challenge_id, debugCode: otp.debug_code });
      setStep("otp");
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(event) {
    event.preventDefault();
    setLoading(true);
    try {
      const result = await api.verifyOtp({
        user_id: otpState.userId,
        challenge_id: otpState.challengeId,
        code: code.trim(),
        device_name: "xambas-client-web",
      });
      onAuthenticated({
        userId: result.user.id,
        email: result.user.email,
        phone: result.user.phone,
        token: result.session.token,
      });
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (step === "otp") {
    return (
      <section className="card auth-card">
        <h2>Verifica tu telefono</h2>
        <p className="muted">
          Enviamos un codigo por SMS a <strong>{form.phone}</strong>.
        </p>
        {otpState?.debugCode && (
          <p className="hint">
            Modo desarrollo: tu codigo es <strong>{otpState.debugCode}</strong>
          </p>
        )}
        <form onSubmit={handleVerify} className="stack">
          <label>
            Codigo de 6 digitos
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={10}
              required
              placeholder="123456"
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "Verificando..." : "Verificar y entrar"}
          </button>
        </form>
      </section>
    );
  }

  return (
    <section className="card auth-card">
      <h2>Crea tu cuenta de cliente</h2>
      <p className="muted">Publica lo que necesitas y te conectamos con proveedores verificados.</p>
      <form onSubmit={handleRegister} className="stack">
        <label>
          Correo
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="tu@correo.com"
          />
        </label>
        <label>
          Telefono (con lada)
          <input
            required
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            placeholder="+5215500000000"
          />
        </label>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Creando..." : "Continuar"}
        </button>
      </form>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Home del cliente: categorias, nueva solicitud, historial
// ---------------------------------------------------------------------------

function ClientHome({ session, onError }) {
  const [categories, setCategories] = useState([]);
  const [requests, setRequests] = useState([]);
  const [selectedRequestId, setSelectedRequestId] = useState(null);
  const [view, setView] = useState("requests");
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      const [categoriesResponse, requestsResponse] = await Promise.all([
        api.listCategories(),
        api.listServiceRequests(session.userId),
      ]);
      setCategories(categoriesResponse.items);
      setRequests(requestsResponse.items);
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
    <div className="stack">
      <nav className="tab-bar" data-testid="client-tabs">
        <button
          type="button"
          className={`tab ${view === "requests" ? "tab-active" : ""}`}
          onClick={() => setView("requests")}
          data-testid="tab-requests"
        >
          Solicitudes
        </button>
        <button
          type="button"
          className={`tab ${view === "recurring" ? "tab-active" : ""}`}
          onClick={() => setView("recurring")}
          data-testid="tab-recurring"
        >
          Servicios recurrentes
        </button>
      </nav>

      {view === "requests" ? (
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
              <p className="muted">Aun no has creado ninguna solicitud.</p>
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
      ) : (
        <RecurringPanel session={session} categories={categories} onError={onError} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Servicios recurrentes: suscripciones y visitas programadas
// ---------------------------------------------------------------------------

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

function RecurringPanel({ session, categories, onError }) {
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
          <p className="muted">Aún no tienes servicios recurrentes.</p>
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
        Categoría
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
        Título
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
        Descripción
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
          Ciudad
          <input
            required
            value={form.city}
            onChange={(e) => setForm({ ...form, city: e.target.value })}
            placeholder="CDMX"
            data-testid="subscription-city-input"
          />
        </label>
        <label>
          Zona de cobertura
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
          Frecuencia
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
          Primera visita (opcional)
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
          Presupuesto por visita (opcional)
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
          Horario preferido (opcional)
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
        Categoria
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
        Titulo
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
        Descripcion
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
          Ciudad
          <input
            required
            value={form.city}
            onChange={(e) => setForm({ ...form, city: e.target.value })}
            placeholder="CDMX"
          />
        </label>
        <label>
          Zona de cobertura
          <input
            required
            value={form.coverageZone}
            onChange={(e) => setForm({ ...form, coverageZone: e.target.value })}
            placeholder="CDMX-Centro"
          />
        </label>
      </div>
      <label>
        Presupuesto aproximado (opcional)
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

// ---------------------------------------------------------------------------
// Detalle de solicitud: matches, chat y resena
// ---------------------------------------------------------------------------

function RequestDetail({ session, requestId, onBack, onError }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeMatchId, setActiveMatchId] = useState(null);
  const [reviewMatchId, setReviewMatchId] = useState(null);
  const [paymentMatchId, setPaymentMatchId] = useState(null);

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
                  <p className="muted">Score: {match.score} · {match.reasons.join(", ")}</p>
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

function ChatPanel({ matchId, senderId, senderRole, onClose, onError }) {
  const [threadId, setThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [contactUnlocked, setContactUnlocked] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const thread = await api.getOrCreateThread(matchId);
      setThreadId(thread.id);
      setContactUnlocked(thread.contact_unlocked);
      const response = await api.listMessages(thread.id);
      setMessages(response.items);
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matchId]);

  async function handleSend(event) {
    event.preventDefault();
    if (!body.trim()) return;
    try {
      await api.sendMessage(threadId, { sender_id: senderId, sender_role: senderRole, body });
      setBody("");
      const response = await api.listMessages(threadId);
      setMessages(response.items);
    } catch (err) {
      onError(err.message);
    }
  }

  return (
    <div className="chat-panel">
      <div className="space-between">
        <strong>Chat con el proveedor</strong>
        <button className="btn btn-ghost" onClick={onClose}>
          Cerrar
        </button>
      </div>
      <p className={contactUnlocked ? "chat-lock unlocked" : "chat-lock"}>
        {contactUnlocked
          ? "\ud83d\udd13 Contacto desbloqueado: ya pueden compartir telefono, correo o direccion."
          : "\ud83d\udd12 Protegemos tu privacidad: telefono, correo y redes se ocultan hasta aceptar el trabajo."}
      </p>
      {loading && <p className="muted">Cargando mensajes...</p>}
      <ul className="message-list">
        {messages.map((message) => (
          <li
            key={message.id}
            className={message.sender_role === senderRole ? "message mine" : "message"}
          >
            <span>{message.body}</span>
            {message.flagged && (
              <span className="flag-note">Se oculto un intento de compartir contacto directo</span>
            )}
          </li>
        ))}
        {!loading && messages.length === 0 && <p className="muted">Aun no hay mensajes.</p>}
      </ul>
      <form onSubmit={handleSend} className="row">
        <input
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Escribe un mensaje..."
        />
        <button className="btn btn-primary" type="submit">
          Enviar
        </button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pago en custodia (Stripe): deposito, estado y liberacion al confirmar
// ---------------------------------------------------------------------------

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
            Monto acordado (MXN)
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
          options={{ clientSecret: checkout.clientSecret }}
        >
          <CheckoutForm onPaid={handlePaid} onError={onError} />
        </Elements>
      )}

      {!loading && payment && !checkout && (
        <div className="stack">
          <div className="payment-summary">
            <div className="space-between">
              <span>Monto del trabajo</span>
              <strong>${payment.job_amount.toFixed(2)} {payment.currency.toUpperCase()}</strong>
            </div>
            <div className="space-between">
              <span>Tarifa de servicio</span>
              <span>${payment.client_fee_amount.toFixed(2)}</span>
            </div>
            <div className="space-between">
              <span>Total pagado</span>
              <strong>${payment.client_total.toFixed(2)}</strong>
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
            <p className="muted">
              Pago liberado al proveedor. Gracias por confirmar el trabajo.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

const PAYMENT_STATUS_LABELS = {
  pending: "Pendiente de pago",
  held_in_escrow: "En custodia (pagado)",
  released: "Liberado al proveedor",
  refunded: "Reembolsado",
  failed: "Fallido",
  cancelled: "Cancelado",
};

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

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}
