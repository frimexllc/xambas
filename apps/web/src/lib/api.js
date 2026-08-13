const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function request(path) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`);
  } catch (networkError) {
    throw new Error(
      `No se pudo conectar con la API en ${BASE_URL}. ¿Esta corriendo el backend? (${networkError.message})`
    );
  }

  const raw = await response.text();
  const data = raw ? JSON.parse(raw) : null;

  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === "string" ? detail : JSON.stringify(detail ?? data);
    throw new Error(message || `Error ${response.status}`);
  }

  return data;
}

export const api = {
  getSiteContent: () => request("/content/site"),
  listCategories: () => request("/matching/categories"),
};

export const CLIENT_URL = import.meta.env.VITE_CLIENT_URL || "http://localhost:4173";
export const PROVIDER_URL = import.meta.env.VITE_PROVIDER_URL || "http://localhost:4174";
