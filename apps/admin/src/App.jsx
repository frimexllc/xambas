import { useEffect, useState } from "react";
import { api, setAuthToken } from "./lib/api.js";
import { clearSession, loadSession, saveSession } from "./lib/session.js";
import "./App.css";

const TABS = [
  { id: "categories", label: "Categorias" },
  { id: "users", label: "Usuarios" },
  { id: "providers", label: "Proveedores" },
  { id: "requests", label: "Solicitudes" },
  { id: "reviews", label: "Resenas" },
  { id: "content", label: "Contenido del sitio" },
  { id: "business", label: "Negocio" },
  { id: "admins", label: "Administradores" },
];

export default function App() {
  const [session, setSession] = useState(() => loadSession());
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("categories");

  useEffect(() => {
    setAuthToken(session?.token || null);
  }, [session]);

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
            <h1>Xambas Admin</h1>
            <p>Panel de administracion</p>
          </div>
        </div>
        {session && (
          <div className="header-right">
            <span className="muted">
              {session.name} · {session.role}
            </span>
            <button className="btn btn-ghost" onClick={handleLogout}>
              Cerrar sesion
            </button>
          </div>
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
          <div className="dashboard">
            <nav className="tabs">
              {TABS.filter((t) => t.id !== "admins" || session.role === "super_admin").map((t) => (
                <button
                  key={t.id}
                  className={t.id === tab ? "tab active" : "tab"}
                  onClick={() => setTab(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </nav>
            <div className="tab-content">
              {tab === "categories" && <CategoriesPanel onError={setError} />}
              {tab === "users" && <UsersPanel onError={setError} />}
              {tab === "providers" && <ProvidersPanel onError={setError} />}
              {tab === "requests" && <RequestsPanel onError={setError} />}
              {tab === "reviews" && <ReviewsPanel onError={setError} />}
              {tab === "content" && <ContentPanel onError={setError} />}
              {tab === "business" && <BusinessPanel onError={setError} />}
              {tab === "admins" && <AdminsPanel onError={setError} />}
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        Xambas Admin · conectado a <code>{import.meta.env.VITE_API_BASE_URL}</code>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Autenticacion: bootstrap del primer admin o login
// ---------------------------------------------------------------------------

function AuthFlow({ onAuthenticated, onError }) {
  const [hasAdmins, setHasAdmins] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "" });

  useEffect(() => {
    api
      .getAdminStatus()
      .then((response) => setHasAdmins(response.has_admins))
      .catch((err) => onError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    try {
      const result = hasAdmins
        ? await api.loginAdmin({ email: form.email.trim(), password: form.password })
        : await api.bootstrapAdmin({
            name: form.name.trim(),
            email: form.email.trim(),
            password: form.password,
          });
      onAuthenticated({
        adminId: result.admin.id,
        name: result.admin.name,
        role: result.admin.role,
        token: result.session.token,
      });
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (hasAdmins === null) {
    return <p className="muted">Cargando...</p>;
  }

  return (
    <section className="card auth-card">
      <h2>{hasAdmins ? "Inicia sesion" : "Crea el primer administrador"}</h2>
      <p className="muted">
        {hasAdmins
          ? "Ingresa con tu correo y contrasena de administrador."
          : "Aun no existe ningun administrador. Esta cuenta sera super_admin."}
      </p>
      <form onSubmit={handleSubmit} className="stack">
        {!hasAdmins && (
          <label>
            Nombre
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Tu nombre"
            />
          </label>
        )}
        <label>
          Correo
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="admin@xambas.mx"
          />
        </label>
        <label>
          Contrasena
          <input
            type="password"
            required
            minLength={8}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            placeholder="Minimo 8 caracteres"
          />
        </label>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Procesando..." : hasAdmins ? "Entrar" : "Crear cuenta"}
        </button>
      </form>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Categorias
// ---------------------------------------------------------------------------

function CategoriesPanel({ onError }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: "", pricingMode: "quote", riskLevel: "standard" });

  async function refresh() {
    setLoading(true);
    try {
      const response = await api.listCategories();
      setCategories(response.items);
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

  async function handleCreate(event) {
    event.preventDefault();
    try {
      await api.createCategory({
        name: form.name.trim(),
        attributes_schema: {},
        pricing_mode: form.pricingMode,
        risk_level: form.riskLevel,
      });
      setForm({ name: "", pricingMode: "quote", riskLevel: "standard" });
      refresh();
    } catch (err) {
      onError(err.message);
    }
  }

  async function handleUpdate(categoryId, fields) {
    try {
      await api.updateCategory(categoryId, fields);
      refresh();
    } catch (err) {
      onError(err.message);
    }
  }

  return (
    <div className="grid-2">
      <section className="card">
        <h2>Nueva categoria</h2>
        <form onSubmit={handleCreate} className="stack">
          <label>
            Nombre
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Jardineria"
            />
          </label>
          <label>
            Modo de precio
            <select
              value={form.pricingMode}
              onChange={(e) => setForm({ ...form, pricingMode: e.target.value })}
            >
              <option value="fixed">Fijo</option>
              <option value="quote">Cotizacion</option>
              <option value="both">Ambos</option>
            </select>
          </label>
          <label>
            Nivel de riesgo
            <select
              value={form.riskLevel}
              onChange={(e) => setForm({ ...form, riskLevel: e.target.value })}
            >
              <option value="standard">Estandar</option>
              <option value="regulated">Regulado</option>
            </select>
          </label>
          <button className="btn btn-primary" type="submit">
            Crear categoria
          </button>
        </form>
      </section>

      <section className="card">
        <h2>Categorias existentes ({categories.length})</h2>
        {loading && <p className="muted">Cargando...</p>}
        <ul className="data-list">
          {categories.map((category) => (
            <li key={category.id} className="data-item">
              <div className="space-between">
                <strong>{category.parent_id ? `— ${category.name}` : category.name}</strong>
                <span className="badge badge-neutral">{category.pricing_mode}</span>
              </div>
              <div className="row">
                <select
                  value={category.risk_level}
                  onChange={(e) => handleUpdate(category.id, { risk_level: e.target.value })}
                >
                  <option value="standard">Estandar</option>
                  <option value="regulated">Regulado</option>
                </select>
                <select
                  value={category.pricing_mode}
                  onChange={(e) => handleUpdate(category.id, { pricing_mode: e.target.value })}
                >
                  <option value="fixed">Fijo</option>
                  <option value="quote">Cotizacion</option>
                  <option value="both">Ambos</option>
                </select>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Usuarios
// ---------------------------------------------------------------------------

function UsersPanel({ onError }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      const response = await api.listUsers();
      setUsers(response.items);
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

  async function toggleActive(user) {
    try {
      await api.updateUser(user.id, { is_active: !user.is_active });
      refresh();
    } catch (err) {
      onError(err.message);
    }
  }

  async function updateKyc(userId, kycStatus) {
    try {
      await api.updateUser(userId, { kyc_status: kycStatus });
      refresh();
    } catch (err) {
      onError(err.message);
    }
  }

  return (
    <section className="card">
      <h2>Usuarios ({users.length})</h2>
      {loading && <p className="muted">Cargando...</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Correo</th>
              <th>Rol</th>
              <th>KYC</th>
              <th>Activo</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.email}</td>
                <td>{user.role}</td>
                <td>
                  <select value={user.kyc_status} onChange={(e) => updateKyc(user.id, e.target.value)}>
                    <option value="pending">Pendiente</option>
                    <option value="in_review">En revision</option>
                    <option value="verified">Verificado</option>
                    <option value="rejected">Rechazado</option>
                  </select>
                </td>
                <td>
                  <span className={user.is_active ? "badge badge-accepted" : "badge badge-rejected"}>
                    {user.is_active ? "activo" : "inactivo"}
                  </span>
                </td>
                <td>
                  <button className="btn btn-secondary" onClick={() => toggleActive(user)}>
                    {user.is_active ? "Desactivar" : "Reactivar"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Proveedores
// ---------------------------------------------------------------------------

function ProvidersPanel({ onError }) {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      const response = await api.listProviders();
      setProviders(response.items);
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

  async function update(providerProfileId, fields) {
    try {
      await api.updateProvider(providerProfileId, fields);
      refresh();
    } catch (err) {
      onError(err.message);
    }
  }

  return (
    <section className="card">
      <h2>Proveedores ({providers.length})</h2>
      {loading && <p className="muted">Cargando...</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Negocio</th>
              <th>Tier</th>
              <th>Rating</th>
              <th>Seguro</th>
              <th>Licencia</th>
              <th>Activo</th>
            </tr>
          </thead>
          <tbody>
            {providers.map((provider) => (
              <tr key={provider.id}>
                <td>{provider.business_name}</td>
                <td>
                  <select
                    value={provider.tier}
                    onChange={(e) => update(provider.id, { tier: e.target.value })}
                  >
                    <option value="nuevo">Nuevo</option>
                    <option value="verificado">Verificado</option>
                    <option value="premium">Premium</option>
                  </select>
                </td>
                <td>
                  {provider.rating_avg.toFixed(1)} ({provider.jobs_completed})
                </td>
                <td>
                  <input
                    type="checkbox"
                    checked={provider.insurance_verified}
                    onChange={(e) => update(provider.id, { insurance_verified: e.target.checked })}
                  />
                </td>
                <td>
                  <input
                    type="checkbox"
                    checked={provider.license_verified}
                    onChange={(e) => update(provider.id, { license_verified: e.target.checked })}
                  />
                </td>
                <td>
                  <button
                    className="btn btn-secondary"
                    onClick={() => update(provider.id, { is_active: !provider.is_active })}
                  >
                    {provider.is_active ? "Desactivar" : "Reactivar"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Solicitudes (solo lectura)
// ---------------------------------------------------------------------------

function RequestsPanel({ onError }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listServiceRequests()
      .then((response) => setRequests(response.items))
      .catch((err) => onError(err.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="card">
      <h2>Solicitudes de servicio ({requests.length})</h2>
      {loading && <p className="muted">Cargando...</p>}
      <ul className="data-list">
        {requests.map((request) => (
          <li key={request.id} className="data-item">
            <div className="space-between">
              <div>
                <strong>{request.title}</strong>
                <p className="muted">
                  {request.category_name} · {request.city}
                </p>
              </div>
              <span className={`badge badge-${request.status}`}>{request.status}</span>
            </div>
          </li>
        ))}
        {!loading && requests.length === 0 && <p className="muted">Aun no hay solicitudes.</p>}
      </ul>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Resenas (moderacion)
// ---------------------------------------------------------------------------

function ReviewsPanel({ onError }) {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      const response = await api.listReviews();
      setReviews(response.items);
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

  async function handleDelete(reviewId) {
    try {
      await api.deleteReview(reviewId);
      refresh();
    } catch (err) {
      onError(err.message);
    }
  }

  return (
    <section className="card">
      <h2>Resenas ({reviews.length})</h2>
      {loading && <p className="muted">Cargando...</p>}
      <ul className="data-list">
        {reviews.map((review) => (
          <li key={review.id} className="data-item">
            <div className="space-between">
              <span>
                {"★".repeat(review.rating)}
                {"☆".repeat(5 - review.rating)}
              </span>
              <button className="btn btn-danger" onClick={() => handleDelete(review.id)}>
                Eliminar
              </button>
            </div>
            {review.comment && <p>{review.comment}</p>}
          </li>
        ))}
        {!loading && reviews.length === 0 && <p className="muted">Aun no hay resenas.</p>}
      </ul>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Contenido del sitio (marca + landing)
// ---------------------------------------------------------------------------

function ContentPanel({ onError }) {
  const [content, setContent] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .getSiteContent()
      .then(setContent)
      .catch((err) => onError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function updateBrand(field, value) {
    setContent((prev) => ({ ...prev, brand: { ...prev.brand, [field]: value } }));
  }

  function updateLanding(field, value) {
    setContent((prev) => ({ ...prev, landing: { ...prev.landing, [field]: value } }));
  }

  function updateStep(index, field, value) {
    setContent((prev) => {
      const steps = [...prev.landing.how_it_works];
      steps[index] = { ...steps[index], [field]: value };
      return { ...prev, landing: { ...prev.landing, how_it_works: steps } };
    });
  }

  function addStep() {
    setContent((prev) => ({
      ...prev,
      landing: {
        ...prev.landing,
        how_it_works: [...prev.landing.how_it_works, { title: "", description: "" }],
      },
    }));
  }

  function removeStep(index) {
    setContent((prev) => ({
      ...prev,
      landing: {
        ...prev.landing,
        how_it_works: prev.landing.how_it_works.filter((_, i) => i !== index),
      },
    }));
  }

  async function handleSave(event) {
    event.preventDefault();
    setSaving(true);
    try {
      const updated = await api.updateSiteContent({
        brand: content.brand,
        landing: content.landing,
      });
      setContent(updated);
    } catch (err) {
      onError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!content) return <p className="muted">Cargando...</p>;

  return (
    <form onSubmit={handleSave} className="stack">
      <section className="card">
        <h2>Marca</h2>
        <div className="row">
          <label>
            Nombre de marca
            <input
              value={content.brand.brand_name}
              onChange={(e) => updateBrand("brand_name", e.target.value)}
            />
          </label>
          <label>
            Logo (URL)
            <input
              value={content.brand.logo_url || ""}
              onChange={(e) => updateBrand("logo_url", e.target.value)}
              placeholder="https://..."
            />
          </label>
        </div>
        <label>
          Tagline
          <input value={content.brand.tagline} onChange={(e) => updateBrand("tagline", e.target.value)} />
        </label>
        <div className="row">
          <label>
            Color primario
            <input
              type="color"
              value={content.brand.primary_color}
              onChange={(e) => updateBrand("primary_color", e.target.value)}
            />
          </label>
          <label>
            Color secundario
            <input
              type="color"
              value={content.brand.secondary_color}
              onChange={(e) => updateBrand("secondary_color", e.target.value)}
            />
          </label>
        </div>
      </section>

      <section className="card">
        <h2>Landing</h2>
        <label>
          Titulo del hero
          <input
            value={content.landing.hero_title}
            onChange={(e) => updateLanding("hero_title", e.target.value)}
          />
        </label>
        <label>
          Subtitulo del hero
          <textarea
            rows={2}
            value={content.landing.hero_subtitle}
            onChange={(e) => updateLanding("hero_subtitle", e.target.value)}
          />
        </label>
        <label>
          Imagen del hero (URL)
          <input
            value={content.landing.hero_image_url || ""}
            onChange={(e) => updateLanding("hero_image_url", e.target.value)}
            placeholder="https://..."
          />
        </label>

        <h3>Como funciona</h3>
        {content.landing.how_it_works.map((step, index) => (
          <div key={index} className="step-editor">
            <input
              value={step.title}
              onChange={(e) => updateStep(index, "title", e.target.value)}
              placeholder="Titulo del paso"
            />
            <input
              value={step.description}
              onChange={(e) => updateStep(index, "description", e.target.value)}
              placeholder="Descripcion"
            />
            <button type="button" className="btn btn-ghost" onClick={() => removeStep(index)}>
              Quitar
            </button>
          </div>
        ))}
        <button type="button" className="btn btn-secondary" onClick={addStep}>
          + Agregar paso
        </button>
      </section>

      <button className="btn btn-primary" type="submit" disabled={saving}>
        {saving ? "Guardando..." : "Guardar cambios"}
      </button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Configuracion de negocio
// ---------------------------------------------------------------------------

function BusinessPanel({ onError }) {
  const [business, setBusiness] = useState(null);
  const [paymentsText, setPaymentsText] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .getBusinessSettings()
      .then((response) => {
        setBusiness(response.business);
        setPaymentsText(JSON.stringify(response.business.payments_enabled, null, 2));
      })
      .catch((err) => onError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSave(event) {
    event.preventDefault();
    setSaving(true);
    try {
      let paymentsEnabled;
      try {
        paymentsEnabled = JSON.parse(paymentsText);
      } catch {
        onError('El campo de metodos de pago debe ser JSON valido, ej: {"MX": ["stripe"]}');
        setSaving(false);
        return;
      }
      const response = await api.updateBusinessSettings({ ...business, payments_enabled: paymentsEnabled });
      setBusiness(response.business);
    } catch (err) {
      onError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!business) return <p className="muted">Cargando...</p>;

  return (
    <form onSubmit={handleSave} className="card stack">
      <h2>Configuracion de negocio</h2>
      <label>
        Comision (%)
        <input
          type="number"
          min="0"
          max="100"
          step="0.1"
          value={business.commission_rate_pct}
          onChange={(e) => setBusiness({ ...business, commission_rate_pct: Number(e.target.value) })}
        />
      </label>
      <div className="row">
        <label>
          Maximo de matches sugeridos
          <input
            type="number"
            min="1"
            max="50"
            value={business.matching_max_results}
            onChange={(e) => setBusiness({ ...business, matching_max_results: Number(e.target.value) })}
          />
        </label>
        <label>
          Score minimo para sugerir
          <input
            type="number"
            min="0"
            max="100"
            value={business.matching_min_score}
            onChange={(e) => setBusiness({ ...business, matching_min_score: Number(e.target.value) })}
          />
        </label>
      </div>
      <label>
        Metodos de pago habilitados por pais (JSON)
        <textarea
          rows={4}
          value={paymentsText}
          onChange={(e) => setPaymentsText(e.target.value)}
          style={{ fontFamily: "monospace" }}
        />
      </label>
      <button className="btn btn-primary" type="submit" disabled={saving}>
        {saving ? "Guardando..." : "Guardar configuracion"}
      </button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Administradores (solo super_admin)
// ---------------------------------------------------------------------------

function AdminsPanel({ onError }) {
  const [admins, setAdmins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "editor" });

  async function refresh() {
    setLoading(true);
    try {
      const response = await api.listAdmins();
      setAdmins(response.items);
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

  async function handleCreate(event) {
    event.preventDefault();
    try {
      await api.createAdmin({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
        role: form.role,
      });
      setForm({ name: "", email: "", password: "", role: "editor" });
      refresh();
    } catch (err) {
      onError(err.message);
    }
  }

  return (
    <div className="grid-2">
      <section className="card">
        <h2>Nuevo administrador</h2>
        <form onSubmit={handleCreate} className="stack">
          <label>
            Nombre
            <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </label>
          <label>
            Correo
            <input
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </label>
          <label>
            Contrasena
            <input
              type="password"
              required
              minLength={8}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </label>
          <label>
            Rol
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="editor">Editor</option>
              <option value="super_admin">Super admin</option>
            </select>
          </label>
          <button className="btn btn-primary" type="submit">
            Crear administrador
          </button>
        </form>
      </section>
      <section className="card">
        <h2>Administradores ({admins.length})</h2>
        {loading && <p className="muted">Cargando...</p>}
        <ul className="data-list">
          {admins.map((admin) => (
            <li key={admin.id} className="data-item">
              <div className="space-between">
                <div>
                  <strong>{admin.name}</strong>
                  <p className="muted">{admin.email}</p>
                </div>
                <span className="badge badge-neutral">{admin.role}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
