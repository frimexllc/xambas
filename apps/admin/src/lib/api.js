const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

let currentToken = null;

export function setAuthToken(token) {
  currentToken = token;
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (currentToken) {
    headers.Authorization = `Bearer ${currentToken}`;
  }

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
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
  // admin auth
  getAdminStatus: () => request("/admin/status"),
  bootstrapAdmin: (payload) =>
    request("/admin/auth/bootstrap", { method: "POST", body: JSON.stringify(payload) }),
  loginAdmin: (payload) =>
    request("/admin/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  getMe: () => request("/admin/auth/me"),
  listAdmins: () => request("/admin/admins"),
  createAdmin: (payload) =>
    request("/admin/admins", { method: "POST", body: JSON.stringify(payload) }),

  // categorias
  listCategories: () => request("/matching/categories"),
  createCategory: (payload) =>
    request("/admin/categories", { method: "POST", body: JSON.stringify(payload) }),
  updateCategory: (categoryId, payload) =>
    request(`/admin/categories/${categoryId}`, { method: "PATCH", body: JSON.stringify(payload) }),

  // usuarios y proveedores
  listUsers: () => request("/admin/users"),
  updateUser: (userId, payload) =>
    request(`/admin/users/${userId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  listProviders: () => request("/admin/providers"),
  updateProvider: (providerProfileId, payload) =>
    request(`/admin/providers/${providerProfileId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  // solicitudes y resenas
  listServiceRequests: () => request("/admin/service-requests"),
  listReviews: () => request("/admin/reviews"),
  deleteReview: (reviewId) => request(`/admin/reviews/${reviewId}`, { method: "DELETE" }),

  // contenido del sitio y negocio
  getSiteContent: () => request("/content/site"),
  updateSiteContent: (payload) =>
    request("/content/site", { method: "PUT", body: JSON.stringify(payload) }),
  getBusinessSettings: () => request("/content/business"),
  updateBusinessSettings: (payload) =>
    request("/content/business", { method: "PUT", body: JSON.stringify(payload) }),
};

export { BASE_URL };
