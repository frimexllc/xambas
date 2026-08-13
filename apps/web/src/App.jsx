import { useEffect, useState } from "react";
import { api, CLIENT_URL, PROVIDER_URL } from "./lib/api.js";
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
    primary_color: "#1b3a5c",
    secondary_color: "#e8622c",
  },
  landing: {
    hero_title: "Tu casa, con orden de trabajo",
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
            <a className="btn btn-secondary" href={CLIENT_URL}>
              Publicar solicitud
            </a>
          </nav>

          <button className="nav-toggle" onClick={() => setMenuOpen((open) => !open)} aria-label="Menu">
            ☰
          </button>
        </div>
      </header>

      <section id="top" className="hero">
        <div>
          <span className="ticket-tag mono-label">
            <span className="dot" /> Orden de servicio abierta
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

        <div className="house-diagram">
          <div className="blueprint-frame">
            <span className="blueprint-corner-label">PLANO · CASA-01</span>
            <span className="blueprint-corner-label right">ESC 1:50</span>
            <HouseSchematic />
          </div>
        </div>
      </section>

      <section id="como-funciona" className="section">
        <div className="section-head">
          <div>
            <span className="mono-label" style={{ color: "var(--blueprint-2)" }}>
              Proceso
            </span>
            <h2>Como funciona</h2>
          </div>
          <p className="section-subtitle">Tres pasos, del primer mensaje al trabajo terminado.</p>
        </div>
        <div className="stub-row">
          {landing.how_it_works.map((step, index) => (
            <div className="stub" key={index}>
              <span className="stub-number">N.0{index + 1}</span>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="categorias" className="section section-muted">
        <div className="section-head">
          <div>
            <span className="mono-label" style={{ color: "var(--blueprint-2)" }}>
              Catalogo
            </span>
            <h2>Categorias populares</h2>
          </div>
          <p className="section-subtitle">Publica tu solicitud en la categoria que necesites.</p>
        </div>
        <div className="category-grid">
          {featured.map((category, index) => (
            <a key={category.id} className="category-card" href={CLIENT_URL}>
              <span className="category-code">N.{String(index + 1).padStart(2, "0")}</span>
              <span className="category-icon">{CATEGORY_ICONS[index % CATEGORY_ICONS.length]}</span>
              <span className="category-name">{category.name}</span>
            </a>
          ))}
          {featured.length === 0 && <p className="muted">Aun no hay categorias configuradas.</p>}
        </div>
      </section>

      <section className="cta">
        <div className="cta-inner">
          <div>
            <h2>Listo para abrir tu orden de servicio?</h2>
            <p>Publica tu solicitud gratis o registra tu negocio para empezar a recibir clientes.</p>
          </div>
          <div className="hero-actions">
            <a className="btn btn-primary btn-lg" href={CLIENT_URL}>
              Publicar solicitud
            </a>
            <a className="btn btn-outline btn-lg" href={PROVIDER_URL}>
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
          © {new Date().getFullYear()} {brand.brand_name.toUpperCase()} — PANEL DE ADMINISTRACION
          DISPONIBLE PARA EL EQUIPO INTERNO
        </p>
      </footer>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.4" />
      <path d="M5 8.2L7 10.2L11 6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function HouseSchematic() {
  return (
    <svg viewBox="0 0 480 360" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Plano de una casa con puntos de servicio">
      {/* suelo */}
      <line x1="40" y1="318" x2="440" y2="318" stroke="rgba(255,255,255,0.35)" strokeWidth="1.5" strokeDasharray="2 4" />

      {/* chimenea */}
      <rect x="308" y="88" width="20" height="48" stroke="white" strokeWidth="2" />

      {/* techo */}
      <path d="M96 156L240 62L384 156" stroke="white" strokeWidth="2.5" strokeLinejoin="round" />

      {/* muros */}
      <rect x="118" y="156" width="244" height="162" stroke="white" strokeWidth="2.5" />

      {/* puerta */}
      <rect x="216" y="228" width="48" height="90" stroke="white" strokeWidth="2" />
      <circle cx="253" cy="274" r="2.4" fill="white" />

      {/* ventanas */}
      <rect x="148" y="200" width="44" height="44" stroke="white" strokeWidth="2" />
      <line x1="170" y1="200" x2="170" y2="244" stroke="white" strokeWidth="1.4" />
      <line x1="148" y1="222" x2="192" y2="222" stroke="white" strokeWidth="1.4" />

      <rect x="288" y="200" width="44" height="44" stroke="white" strokeWidth="2" />
      <line x1="310" y1="200" x2="310" y2="244" stroke="white" strokeWidth="1.4" />
      <line x1="288" y1="222" x2="332" y2="222" stroke="white" strokeWidth="1.4" />

      {/* cotas */}
      <line x1="118" y1="332" x2="362" y2="332" stroke="rgba(255,255,255,0.3)" strokeWidth="1" />
      <text x="240" y="348" fill="rgba(255,255,255,0.55)" fontSize="10" fontFamily="IBM Plex Mono, monospace" textAnchor="middle">
        7.20 M
      </text>

      {/* pines numerados de servicio */}
      <ServicePin x={170} y={222} n="1" lx={170} ly={222} />
      <ServicePin x={318} y={112} n="2" lx={318} ly={112} />
      <ServicePin x={253} y={274} n="3" lx={253} ly={274} />
      <ServicePin x={90} y={300} n="4" lx={90} ly={300} />
    </svg>
  );
}

function ServicePin({ x, y, n }) {
  return (
    <g>
      <circle cx={x} cy={y} r="11" fill="#e8622c" stroke="white" strokeWidth="1.5" />
      <text x={x} y={y + 4} fill="white" fontSize="11" fontFamily="IBM Plex Mono, monospace" fontWeight="600" textAnchor="middle">
        {n}
      </text>
    </g>
  );
}
