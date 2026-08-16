import { useEffect, useState } from "react";
import { api } from "./lib/api.js";
import { clearSession, loadSession, saveSession } from "./lib/session.js";
import "./App.css";

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
            <h1>Xambas Proveedores</h1>
            <p>Recibe y gestiona tus oportunidades de trabajo</p>
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
          <ProviderHome session={session} onError={setError} />
        )}
      </main>

      <footer className="app-footer">
        Xambas Proveedor · Fase 0 · conectado a <code>{import.meta.env.VITE_API_BASE_URL}</code>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Autenticacion: bootstrap con perfil de proveedor + verificacion OTP
// ---------------------------------------------------------------------------

function AuthFlow({ onAuthenticated, onError }) {
  const [step, setStep] = useState("register"); // register | otp
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState({
    email: "",
    phone: "",
    businessName: "",
    categoryIds: [],
    coverageZones: "",
    insuranceVerified: false,
    licenseVerified: false,
  });
  const [otpState, setOtpState] = useState(null);
  const [code, setCode] = useState("");

  useEffect(() => {
    api
      .listCategories()
      .then((response) => setCategories(response.items))
      .catch((err) => onError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function toggleCategory(categoryId) {
    setForm((prev) => {
      const has = prev.categoryIds.includes(categoryId);
      return {
        ...prev,
        categoryIds: has
          ? prev.categoryIds.filter((id) => id !== categoryId)
          : [...prev.categoryIds, categoryId],
      };
    });
  }

  async function handleRegister(event) {
    event.preventDefault();
    if (form.categoryIds.length === 0) {
      onError("Selecciona al menos una categoria de servicio.");
      return;
    }
    setLoading(true);
    try {
      const result = await api.bootstrap({
        email: form.email.trim(),
        phone: form.phone.trim(),
        role: "provider",
        locale: "es-MX",
        provider_profile: {
          business_name: form.businessName.trim(),
          categories: form.categoryIds,
          coverage_zones: form.coverageZones
            .split(",")
            .map((zone) => zone.trim())
            .filter(Boolean),
          insurance_verified: form.insuranceVerified,
          license_verified: form.licenseVerified,
        },
      });
      const userId = result.user.id;
      const otp = await api.requestOtp({ user_id: userId, purpose: "registration", channel: "sms" });
      setOtpState({
        userId,
        challengeId: otp.challenge_id,
        debugCode: otp.debug_code,
        providerProfileId: result.provider_profile.id,
      });
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
        device_name: "xambas-provider-web",
      });
      onAuthenticated({
        userId: result.user.id,
        email: result.user.email,
        phone: result.user.phone,
        token: result.session.token,
        providerProfileId: otpState.providerProfileId,
        businessName: form.businessName.trim(),
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
    <section className="card auth-card wide">
      <h2>Registra tu negocio</h2>
      <p className="muted">Completa tu perfil para empezar a recibir solicitudes de clientes.</p>
      <form onSubmit={handleRegister} className="stack">
        <label>
          Correo
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="negocio@correo.com"
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
        <label>
          Nombre del negocio
          <input
            required
            minLength={2}
            value={form.businessName}
            onChange={(e) => setForm({ ...form, businessName: e.target.value })}
            placeholder="Plomeria Express"
          />
        </label>
        <div>
          <span className="field-label">Categorias que ofreces</span>
          <div className="chip-grid">
            {categories.map((category) => (
              <label key={category.id} className="chip">
                <input
                  type="checkbox"
                  checked={form.categoryIds.includes(category.id)}
                  onChange={() => toggleCategory(category.id)}
                />
                {category.name}
              </label>
            ))}
          </div>
        </div>
        <label>
          Zonas de cobertura (separadas por coma)
          <input
            required
            value={form.coverageZones}
            onChange={(e) => setForm({ ...form, coverageZones: e.target.value })}
            placeholder="CDMX-Centro, CDMX-Sur"
          />
        </label>
        <div className="row">
          <label className="chip">
            <input
              type="checkbox"
              checked={form.insuranceVerified}
              onChange={(e) => setForm({ ...form, insuranceVerified: e.target.checked })}
            />
            Cuento con seguro
          </label>
          <label className="chip">
            <input
              type="checkbox"
              checked={form.licenseVerified}
              onChange={(e) => setForm({ ...form, licenseVerified: e.target.checked })}
            />
            Cuento con licencia/certificacion
          </label>
        </div>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Creando..." : "Continuar"}
        </button>
      </form>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Home del proveedor: oportunidades + reputacion
// ---------------------------------------------------------------------------

function ProviderHome({ session, onError }) {
  const [matches, setMatches] = useState([]);
  const [reputation, setReputation] = useState(null);
  const [commissionTiers, setCommissionTiers] = useState(null);
  const [commissionQuote, setCommissionQuote] = useState(null);
  const [connectStatus, setConnectStatus] = useState(null);
  const [payments, setPayments] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [milestonePlans, setMilestonePlans] = useState([]);
  const [connecting, setConnecting] = useState(false);
  const [activeMatchId, setActiveMatchId] = useState(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      const [matchesResponse, reputationResponse, tiersResponse, quoteResponse, connectResponse, paymentsResponse, dashboardResponse, plansResponse] =
        await Promise.all([
          api.listMatchesForProvider(session.userId),
          api.getProviderReputation(session.providerProfileId),
          api.getCommissionTiers(),
          api.getCommissionQuote(session.providerProfileId, 1000),
          api.getConnectStatus(session.providerProfileId),
          api.listPaymentsForProvider(session.userId),
          api.getDashboard(session.userId, session.providerProfileId),
          api.listMilestonePlansForProvider(session.userId),
        ]);
      setMatches(matchesResponse.items);
      setReputation(reputationResponse);
      setCommissionTiers(tiersResponse);
      setCommissionQuote(quoteResponse);
      setConnectStatus(connectResponse);
      setPayments(paymentsResponse.items);
      setDashboard(dashboardResponse);
      setMilestonePlans(plansResponse.items);
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

  async function handleAccept(matchId) {
    try {
      await api.acceptMatch(matchId, session.userId);
      refresh();
    } catch (err) {
      onError(err.message);
    }
  }

  async function handleConnectOnboarding() {
    setConnecting(true);
    try {
      const response = await api.createConnectOnboarding(session.providerProfileId);
      window.open(response.onboarding_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      onError(err.message);
    } finally {
      setConnecting(false);
    }
  }

  return (
    <div className="stack">
      {dashboard && (
        <section className="card" data-testid="provider-dashboard">
          <h2>Tu panel</h2>
          <div className="metrics-strip">
            <div className="metric" data-testid="metric-tier">
              <span className="metric-value">{dashboard.metrics.tier}</span>
              <span className="metric-label">Nivel · {dashboard.metrics.commission_pct}% comisión</span>
            </div>
            <div className="metric">
              <span className="metric-value">{dashboard.metrics.rating_avg.toFixed(1)}</span>
              <span className="metric-label">Calificación</span>
            </div>
            <div className="metric">
              <span className="metric-value">{dashboard.metrics.accepted_jobs}</span>
              <span className="metric-label">Trabajos aceptados</span>
            </div>
            <div className="metric">
              <span className="metric-value">{dashboard.metrics.active_opportunities}</span>
              <span className="metric-label">Oportunidades activas</span>
            </div>
            <div className="metric" data-testid="metric-earnings">
              <span className="metric-value">${dashboard.metrics.earnings_released.toLocaleString()}</span>
              <span className="metric-label">Ingresos liberados</span>
            </div>
            <div className="metric">
              <span className="metric-value">${dashboard.metrics.earnings_in_escrow.toLocaleString()}</span>
              <span className="metric-label">En custodia</span>
            </div>
          </div>
        </section>
      )}

      {dashboard && dashboard.recurring_visits.length > 0 && (
        <section className="card" data-testid="provider-recurring">
          <h2>Visitas recurrentes asignadas</h2>
          <p className="muted">
            Clientes con un servicio recurrente en tu zona. Confirma la visita aceptando el trabajo.
          </p>
          <ul className="data-list">
            {dashboard.recurring_visits.map((visit) => (
              <li key={visit.request_id} className="data-item" data-testid={`recurring-visit-${visit.request_id}`}>
                <div className="space-between">
                  <div>
                    <strong>{visit.title}</strong>
                    <p className="muted">
                      {FREQUENCY_LABELS[visit.frequency] || visit.frequency} · próxima {visit.scheduled_date}
                    </p>
                  </div>
                  {visit.match_status === "suggested" ? (
                    <button
                      className="btn btn-primary"
                      onClick={() => handleAccept(visit.match_id)}
                      data-testid={`recurring-accept-${visit.request_id}`}
                    >
                      Confirmar visita
                    </button>
                  ) : (
                    <StatusBadge status={visit.match_status} />
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {milestonePlans.length > 0 && (
        <section className="card" data-testid="provider-milestones">
          <h2>Pagos por etapas</h2>
          <p className="muted">
            Sube evidencia fotográfica de cada etapa. El cliente libera el pago de esa fase al aprobarla.
          </p>
          <ul className="match-list">
            {milestonePlans.map((plan) => (
              <ProviderMilestonePlan
                key={plan.id}
                plan={plan}
                providerUserId={session.userId}
                onChanged={refresh}
                onError={onError}
              />
            ))}
          </ul>
        </section>
      )}

      <div className="grid-2">
      <section className="card">
        <h2>Tus oportunidades</h2>
        {loading && <p className="muted">Cargando...</p>}
        {!loading && matches.length === 0 && (
          <p className="muted">
            Aun no tienes solicitudes asignadas. Apareceras aqui en cuanto un cliente publique algo
            que coincida con tus categorias y zona de cobertura.
          </p>
        )}
        <ul className="match-list">
          {matches.map((match) => (
            <li key={match.id} className="match-item">
              <div className="space-between">
                <div>
                  <strong>Solicitud #{match.request_id.slice(-6)}</strong>
                  <p className="muted">Score: {match.score} · {match.reasons.join(", ")}</p>
                </div>
                <StatusBadge status={match.status} />
              </div>
              <div className="row">
                {match.status === "suggested" && (
                  <button className="btn btn-primary" onClick={() => handleAccept(match.id)}>
                    Aceptar trabajo
                  </button>
                )}
                <button className="btn btn-secondary" onClick={() => setActiveMatchId(match.id)}>
                  Chatear con el cliente
                </button>
              </div>
              {activeMatchId === match.id && (
                <ChatPanel
                  matchId={match.id}
                  senderId={session.userId}
                  senderRole="provider"
                  onClose={() => setActiveMatchId(null)}
                  onError={onError}
                />
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Tu reputacion</h2>
        {reputation ? (
          <>
            <div className="reputation-summary">
              <span className="reputation-score">{reputation.rating_avg.toFixed(1)}</span>
              <div>
                <div>{"★".repeat(Math.round(reputation.rating_avg))}{"☆".repeat(5 - Math.round(reputation.rating_avg))}</div>
                <p className="muted">{reputation.jobs_completed} trabajos completados</p>
              </div>
            </div>
            <ul className="review-list">
              {reputation.reviews.map((review) => (
                <li key={review.id} className="review-item">
                  <div className="space-between">
                    <span>{"★".repeat(review.rating)}{"☆".repeat(5 - review.rating)}</span>
                    <span className="muted">{new Date(review.created_at).toLocaleDateString()}</span>
                  </div>
                  {review.comment && <p>{review.comment}</p>}
                </li>
              ))}
              {reputation.reviews.length === 0 && (
                <p className="muted">Aun no tienes resenas. Completa tu primer trabajo para recibir una.</p>
              )}
            </ul>
          </>
        ) : (
          <p className="muted">Cargando reputacion...</p>
        )}
      </section>

      <section className="card">
        <h2>Tu comision</h2>
        <p className="muted">
          Solo pagas cuando ganas el trabajo, nunca por cada contacto. Entre mas trabajos
          completes y mejor calificacion mantengas, mas baja tu comision.
        </p>
        {commissionQuote && (
          <div className="commission-highlight">
            <span className={`badge badge-tier-${commissionQuote.provider_tier}`}>
              Nivel {commissionQuote.provider_tier}
            </span>
            <span className="commission-pct">{commissionQuote.provider_commission_pct}%</span>
            <span className="muted">de comision sobre cada trabajo pagado</span>
          </div>
        )}
        {commissionTiers && (
          <table className="tier-table">
            <thead>
              <tr>
                <th>Nivel</th>
                <th>Comision</th>
                <th>Requisito</th>
              </tr>
            </thead>
            <tbody>
              {commissionTiers.tiers.map((tier) => (
                <tr
                  key={tier.tier}
                  className={commissionQuote?.provider_tier === tier.tier ? "tier-current" : ""}
                >
                  <td>{tier.tier}</td>
                  <td>{tier.commission_rate_pct}%</td>
                  <td className="muted">{tier.requirements}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h2>Cobros</h2>
        {connectStatus && !connectStatus.stripe_connect_account_id && (
          <div className="connect-callout">
            <p className="muted">
              Para poder recibir tus pagos necesitas conectar una cuenta de pagos (Stripe). Es
              gratis y toma unos minutos.
            </p>
            <button className="btn btn-primary" onClick={handleConnectOnboarding} disabled={connecting}>
              {connecting ? "Abriendo..." : "Conectar cuenta de pagos"}
            </button>
          </div>
        )}
        {connectStatus && connectStatus.stripe_connect_account_id && !connectStatus.payouts_enabled && (
          <div className="connect-callout">
            <p className="muted">
              Tu cuenta de pagos esta creada pero aun le falta informacion. Termina la verificacion
              para poder recibir transferencias.
            </p>
            <button className="btn btn-secondary" onClick={handleConnectOnboarding} disabled={connecting}>
              {connecting ? "Abriendo..." : "Completar verificacion"}
            </button>
          </div>
        )}
        {connectStatus && connectStatus.payouts_enabled && (
          <p className="chat-lock unlocked">✔ Tu cuenta de pagos esta verificada y lista para recibir transferencias.</p>
        )}

        <h3>Historial de pagos</h3>
        {payments.length === 0 && <p className="muted">Aun no tienes pagos registrados.</p>}
        <ul className="data-list">
          {payments.map((payment) => (
            <li key={payment.id} className="data-item">
              <div className="space-between">
                <strong>${payment.provider_receives.toFixed(2)} {payment.currency.toUpperCase()}</strong>
                <span className={`badge payment-status-${payment.status}`}>
                  {PAYMENT_STATUS_LABELS[payment.status] || payment.status}
                </span>
              </div>
              <p className="muted">Trabajo de ${payment.job_amount.toFixed(2)} · comision {payment.provider_commission_pct}%</p>
            </li>
          ))}
        </ul>
      </section>
      </div>
    </div>
  );
}

const FREQUENCY_LABELS = {
  weekly: "Semanal",
  biweekly: "Quincenal",
  monthly: "Mensual",
};

function ProviderMilestonePlan({ plan, providerUserId, onChanged, onError }) {
  const [busyId, setBusyId] = useState(null);

  async function handleSubmit(milestoneId, fileList) {
    if (!fileList || fileList.length === 0) return;
    setBusyId(milestoneId);
    try {
      const formData = new FormData();
      Array.from(fileList).slice(0, 5).forEach((file) => formData.append("files", file));
      await api.submitMilestoneEvidence(plan.id, milestoneId, providerUserId, formData);
      onChanged();
    } catch (err) {
      onError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <li className="match-item" data-testid={`provider-plan-${plan.id}`}>
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
              <span className={`badge badge-${milestone.status}`}>{MS_LABELS[milestone.status]}</span>
            </div>
            {milestone.evidence.length > 0 && (
              <div className="quote-thumbs">
                {milestone.evidence.map((ev) => (
                  <img key={ev.path} src={ev.url} alt="evidencia" className="quote-thumb" />
                ))}
              </div>
            )}
            {milestone.status === "pending" && (
              <label className="btn btn-secondary evidence-btn">
                {busyId === milestone.id ? "Subiendo..." : "Subir evidencia"}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  multiple
                  hidden
                  data-testid={`provider-evidence-${milestone.id}`}
                  onChange={(e) => handleSubmit(milestone.id, e.target.files)}
                />
              </label>
            )}
          </li>
        ))}
      </ul>
    </li>
  );
}

const MS_LABELS = { pending: "Pendiente", submitted: "Evidencia enviada", released: "Pagada" };

const PAYMENT_STATUS_LABELS = {
  pending: "Pendiente de pago",
  held_in_escrow: "En custodia (pagado)",
  released: "Liberado a tu cuenta",
  refunded: "Reembolsado",
  failed: "Fallido",
  cancelled: "Cancelado",
};

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
        <strong>Chat con el cliente</strong>
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

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}
