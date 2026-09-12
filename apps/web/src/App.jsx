import { useEffect, useState } from "react";
import { api, CLIENT_URL, PROVIDER_URL } from "./lib/api.js";
import ThemeToggle from "./components/ThemeToggle.jsx";
import "./App.css";

const CATEGORY_ICONS = ["🔧", "💡", "🚰", "🧹", "🌿", "🎨", "🔩", "🛠️", "🪛", "🧰"];

const TRUST_ITEMS = [
  { label: "Pago retenido en custodia hasta terminar" },
  { label: "Chat con filtro anti-fuga de contacto" },
  { label: "Proveedores por nivel verificado" },
];

const FALLBACK_CONTENT = {
  brand: {
    brand_name: "Xambas",
    tagline: "Encuentra profesionales de confianza para tu hogar",
    logo_url: null,
    primary_color: "#007aff",
    secondary_color: "#007aff",
  },
  landing: {
    hero_title: "Tu hogar, en buenas manos",
    hero_subtitle:
      "Publica lo que necesitas, recibe propuestas de proveedores verificados y paga solo cuando el trabajo esta hecho.",
    hero_image_url: null,
    how_it_works: [
      { title: "Publica tu solicitud", description: "Describe el trabajo, la zona y cuando lo necesitas." },
      { title: "Recibe propuestas", description: "Proveedores verificados te contactan por chat protegido." },
      { title: "Paga con respaldo", description: "El pago queda en custodia hasta que confirmes que quedo listo." },
    ],
    featured_category_ids: [],
  },
};

export default function App() {
  const [content, setContent] = useState(null);
  const [categories, setCategories] = useState([]);
  const [error, setError] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    Promise.all([api.getSiteContent(), api.listCategories()])
      .then(([contentResponse, categoriesResponse]) => {
        setContent(contentResponse);
        setCategories(categoriesResponse.items);
      })
      .catch((err) => {
        setError(err.message);
        setContent(FALLBACK_CONTENT);
      });
  }, []);

  const active = content || FALLBACK_CONTENT;
  const { brand, landing } = active;

  const featured =
    landing.featured_category_ids && landing.featured_category_ids.length > 0
      ? categories.filter((category) => landing.featured_category_ids.includes(category.id))
      : categories.filter((category) => !category.parent_id).slice(0, 8);

  return (
    <div className="landing">
      {error && (
        <div className="banner banner-error">
          Mostrando contenido de respaldo — no se pudo cargar el contenido en vivo ({error}).
        </div>
      )}

      <header className="nav">
        <div className="nav-inner">
          <a className="brand" href="#top">
            {brand.logo_url ? (
              <img src={brand.logo_url} alt={brand.brand_name} className="brand-logo" />
            ) : (
              <span className="brand-mark">{brand.brand_name.charAt(0)}</span>
            )}
            {brand.brand_name}
          </a>

          <nav className={`nav-links ${menuOpen ? "open" : ""}`}>
            <a href="#como-funciona" onClick={() => setMenuOpen(false)}>
              Como funciona
            </a>
            <a href="#categorias" onClick={() => setMenuOpen(false)}>
              Categorias
            </a>
            <a className="btn btn-ghost" href={PROVIDER_URL}>
              Soy proveedor
            </a>
            <a className="btn btn-primary" href={CLIENT_URL}>
              Publicar solicitud
            </a>
          </nav>

          <div className="nav-actions">
            <ThemeToggle />
            <button className="nav-toggle" onClick={() => setMenuOpen((open) => !open)} aria-label="Menu">
              <MenuIcon />
            </button>
          </div>
        </div>
      </header>

      <section id="top" className="hero">
        <div>
          <span className="eyebrow">
            <span className="eyebrow-dot" /> Servicio verificado
          </span>
          <h1>{landing.hero_title}</h1>
          <p>{landing.hero_subtitle}</p>
          <div className="hero-actions">
            <a className="btn btn-primary btn-lg" href={CLIENT_URL}>
              Publicar una solicitud
            </a>
            <a className="btn btn-secondary btn-lg" href={PROVIDER_URL}>
              Ofrecer mis servicios
            </a>
          </div>
          <div className="hero-trust">
            {TRUST_ITEMS.map((item) => (
              <span className="hero-trust-item" key={item.label}>
                <CheckIcon />
                {item.label}
              </span>
            ))}
          </div>
        </div>

        <div className="hero-preview" aria-hidden="true">
          <div className="preview-card">
            <div className="preview-row">
              <span className="preview-dot" />
              <span className="preview-dot" />
              <span className="preview-dot" />
            </div>
            <div className="preview-title">Cotización con IA</div>
            <div className="preview-chip-row">
              <span className="preview-chip active">Plomería</span>
              <span className="preview-chip">Limpieza</span>
              <span className="preview-chip">Electricidad</span>
            </div>
            <div className="preview-price">
              <span>Rango estimado</span>
              <strong>$850–$1,450 MXN</strong>
            </div>
            <div className="preview-list">
              <div className="preview-list-item">
                <CheckIcon />
                Revisión y localización de la fuga
              </div>
              <div className="preview-list-item">
                <CheckIcon />
                Reemplazo de empaques
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="como-funciona" className="section">
        <div className="section-head">
          <div>
            <span className="eyebrow-label">Proceso</span>
            <h2>Como funciona</h2>
          </div>
          <p className="section-subtitle">Tres pasos, del primer mensaje al trabajo terminado.</p>
        </div>
        <div className="steps-row">
          {landing.how_it_works.map((step, index) => (
            <div className="step" key={index}>
              <span className="step-number">{index + 1}</span>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="categorias" className="section section-muted">
        <div className="section-head">
          <div>
            <span className="eyebrow-label">Catalogo</span>
            <h2>Categorias populares</h2>
          </div>
          <p className="section-subtitle">Publica tu solicitud en la categoria que necesites.</p>
        </div>
        <div className="category-grid">
          {featured.map((category, index) => (
            <a key={category.id} className="category-card" href={CLIENT_URL}>
              <span className="category-icon">{CATEGORY_ICONS[index % CATEGORY_ICONS.length]}</span>
              <span className="category-name">{category.name}</span>
            </a>
          ))}
          {featured.length === 0 && <p className="muted">Aun no hay categorias configuradas.</p>}
        </div>
      </section>

      <section className="cta">
        <div className="cta-inner">
          <h2>Listo para empezar?</h2>
          <p>Publica tu solicitud gratis o registra tu negocio para empezar a recibir clientes.</p>
          <div className="hero-actions" style={{ justifyContent: "center" }}>
            <a className="btn btn-primary btn-lg" href={CLIENT_URL}>
              Publicar solicitud
            </a>
            <a className="btn btn-secondary btn-lg" href={PROVIDER_URL}>
              Registrar mi negocio
            </a>
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="footer-inner">
          <div>
            <div className="brand">
              <span className="brand-mark">{brand.brand_name.charAt(0)}</span>
              {brand.brand_name}
            </div>
            <p className="muted">{brand.tagline}</p>
          </div>
          <div className="footer-links">
            <a href={CLIENT_URL}>Soy cliente</a>
            <a href={PROVIDER_URL}>Soy proveedor</a>
            <a href="#como-funciona">Como funciona</a>
          </div>
        </div>
        <p className="footer-note">
          © {new Date().getFullYear()} {brand.brand_name} — Panel de administracion disponible para el
          equipo interno
        </p>
      </footer>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9.5" fill="#34c759" />
      <path d="M8 12.3L10.6 15L16.5 8.8" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M4 7H20M4 12H20M4 17H20" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}
