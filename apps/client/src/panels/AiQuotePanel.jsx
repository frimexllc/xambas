import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { COUNTRY_CODE } from "../constants.js";
import { EmptyState } from "../components/EmptyState.jsx";
import { PhotoDropzone } from "../components/PhotoDropzone.jsx";
import { CameraIcon, CheckIcon } from "../components/icons.jsx";

// Cotización con IA: sube fotos y recibe alcance + precio estimado (Groq visión).

export function AiQuotePanel({ session, categories, onError }) {
  const [categoryId, setCategoryId] = useState("");
  const [notes, setNotes] = useState("");
  const [files, setFiles] = useState([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [quote, setQuote] = useState(null);
  const [history, setHistory] = useState([]);

  async function refreshHistory() {
    try {
      const response = await api.listEstimates(session.userId);
      setHistory(response.items);
    } catch (err) {
      onError(err.message);
    }
  }

  useEffect(() => {
    refreshHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleAnalyze(event) {
    event.preventDefault();
    if (!categoryId) return onError("Selecciona una categoría.");
    if (files.length === 0) return onError("Sube al menos una foto del trabajo.");
    setAnalyzing(true);
    setQuote(null);
    try {
      const formData = new FormData();
      formData.append("category_id", categoryId);
      if (notes.trim()) formData.append("notes", notes.trim());
      files.forEach((file) => formData.append("files", file));
      const response = await api.createEstimate(formData);
      setQuote(response.quote);
      refreshHistory();
    } catch (err) {
      onError(err.message);
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div className="grid-2" data-testid="ai-quote-panel">
      <section className="card">
        <h2>Cotización con IA</h2>
        <p className="muted">
          Sube fotos del trabajo y nuestra IA estima el alcance y un rango de precio en segundos,
          antes de contactar a ningún proveedor. Sin sorpresas, sin llamadas de venta.
        </p>
        <form onSubmit={handleAnalyze} className="stack" data-testid="ai-quote-form">
          <label>
            <span className="field-label">Categoría</span>
            <select
              required
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              data-testid="ai-quote-category-select"
            >
              <option value="">Selecciona una categoría</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.parent_id ? `— ${category.name}` : category.name}
                </option>
              ))}
            </select>
          </label>
          <div>
            <span className="field-label">Fotos del trabajo</span>
            <PhotoDropzone
              files={files}
              onChange={setFiles}
              maxFiles={5}
              accept="image/jpeg,image/png,image/webp"
              testId="ai-quote-files-input"
            />
          </div>
          <label>
            <span className="field-label">Notas (opcional)</span>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Describe detalles útiles: medidas, materiales, urgencia..."
              data-testid="ai-quote-notes-input"
            />
          </label>
          <button
            className="btn btn-primary"
            type="submit"
            disabled={analyzing}
            data-testid="ai-quote-submit-btn"
          >
            {analyzing ? "Analizando fotos con IA..." : "Analizar y estimar precio"}
          </button>
        </form>
      </section>

      <section className="card">
        {quote ? (
          <QuoteResult quote={quote} session={session} onError={onError} />
        ) : (
          <>
            <h2>Tus cotizaciones</h2>
            {history.length === 0 && (
              <EmptyState
                icon={<CameraIcon />}
                title="Aún no has generado cotizaciones"
                hint="Sube fotos del trabajo a la izquierda y recibe un alcance y precio estimado en segundos."
              />
            )}
            <ul className="request-list" data-testid="ai-quote-history">
              {history.map((item) => (
                <li key={item.id}>
                  <button
                    className="request-item"
                    onClick={() => setQuote(item)}
                    data-testid={`ai-quote-history-${item.id}`}
                  >
                    <div>
                      <strong>{item.suggested_title}</strong>
                      <p className="muted">
                        {item.category_name || "Sin categoría"} ·{" "}
                        <span className="mono">
                          ${item.price_min}–${item.price_max} {item.currency}
                        </span>
                      </p>
                    </div>
                    <span className="badge badge-ready">{Math.round(item.confidence * 100)}%</span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}

function QuoteResult({ quote, session, onError }) {
  return (
    <div className="stack" data-testid="ai-quote-result">
      <div className="space-between">
        <h2>Estimación de IA</h2>
        <span className="confidence-chip">{Math.round(quote.confidence * 100)}% confianza</span>
      </div>

      <div className="readout-panel">
        <span className="mono-label accent">Rango estimado</span>
        <div className="quote-price" data-testid="ai-quote-price">
          ${quote.price_min.toLocaleString()}–${quote.price_max.toLocaleString()}{" "}
          <span className="unit">{quote.currency}</span>
        </div>
      </div>

      <div>
        <span className="field-label">Alcance estimado</span>
        <ul className="scope-list">
          {quote.scope.map((item, index) => (
            <li key={index}>
              <CheckIcon />
              {item}
            </li>
          ))}
        </ul>
      </div>

      {quote.assumptions.length > 0 && (
        <div>
          <span className="field-label">Supuestos</span>
          <ul className="scope-list muted-list">
            {quote.assumptions.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {quote.images.length > 0 && (
        <div>
          <span className="field-label">Fotos</span>
          <div className="quote-thumbs" style={{ marginTop: 8 }}>
            {quote.images.map((image) => (
              <div key={image.path} className="quote-thumb-frame">
                <img src={image.url} alt="foto del trabajo" className="quote-thumb" />
              </div>
            ))}
          </div>
        </div>
      )}

      <PublishFromQuote quote={quote} session={session} onError={onError} />
    </div>
  );
}

function PublishFromQuote({ quote, session, onError }) {
  const [city, setCity] = useState("");
  const [coverageZone, setCoverageZone] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [publishedId, setPublishedId] = useState(null);

  async function handlePublish(event) {
    event.preventDefault();
    if (!quote.category_id) return onError("Esta cotización no tiene categoría para publicar.");
    setPublishing(true);
    try {
      const response = await api.createServiceRequest({
        client_id: session.userId,
        category_id: quote.category_id,
        title: quote.suggested_title,
        description: quote.suggested_description,
        country_code: COUNTRY_CODE,
        city: city.trim(),
        coverage_zone: coverageZone.trim(),
        budget_amount: quote.price_min || null,
      });
      setPublishedId(response.request.id);
    } catch (err) {
      onError(err.message);
    } finally {
      setPublishing(false);
    }
  }

  if (publishedId) {
    return (
      <p className="hint" data-testid="ai-quote-published">
        Solicitud publicada con esta estimación. Revísala en la pestaña "Solicitudes".
      </p>
    );
  }

  return (
    <form onSubmit={handlePublish} className="publish-form stack" data-testid="ai-quote-publish-form">
      <h3>Publicar solicitud con esta estimación</h3>
      <p className="muted">
        Usaremos el alcance, el título y el precio estimado. Solo dinos dónde es el trabajo.
      </p>
      <div className="row">
        <label>
          <span className="field-label">Ciudad</span>
          <input
            required
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="CDMX"
            data-testid="ai-quote-city-input"
          />
        </label>
        <label>
          <span className="field-label">Zona de cobertura</span>
          <input
            required
            value={coverageZone}
            onChange={(e) => setCoverageZone(e.target.value)}
            placeholder="Roma Norte"
            data-testid="ai-quote-zone-input"
          />
        </label>
      </div>
      <button
        className="btn btn-secondary"
        type="submit"
        disabled={publishing}
        data-testid="ai-quote-publish-btn"
      >
        {publishing ? "Publicando..." : "Publicar solicitud"}
      </button>
    </form>
  );
}
