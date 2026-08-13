const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
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
  // identity
  bootstrap: (payload) =>
    request("/identity/bootstrap", { method: "POST", body: JSON.stringify(payload) }),
  getUser: (userId) => request(`/identity/users/${userId}`),
  requestOtp: (payload) =>
    request("/identity/otp/request", { method: "POST", body: JSON.stringify(payload) }),
  verifyOtp: (payload) =>
    request("/identity/otp/verify", { method: "POST", body: JSON.stringify(payload) }),

  // matching
  listCategories: (parentId) =>
    request(`/matching/categories${parentId ? `?parent_id=${parentId}` : ""}`),
  createServiceRequest: (payload) =>
    request("/matching/service-requests", { method: "POST", body: JSON.stringify(payload) }),
  listServiceRequests: (clientId) =>
    request(`/matching/service-requests?client_id=${clientId}`),
  getServiceRequest: (requestId) => request(`/matching/service-requests/${requestId}`),
  rerunMatching: (requestId) =>
    request(`/matching/service-requests/${requestId}/run`, { method: "POST" }),

  // messaging
  getOrCreateThread: (matchId) =>
    request("/messaging/threads", { method: "POST", body: JSON.stringify({ match_id: matchId }) }),
  listMessages: (threadId) => request(`/messaging/threads/${threadId}/messages`),
  sendMessage: (threadId, payload) =>
    request(`/messaging/threads/${threadId}/messages`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // reputation
  createReview: (payload) =>
    request("/reputation/reviews", { method: "POST", body: JSON.stringify(payload) }),
  getProviderReputation: (providerProfileId) =>
    request(`/reputation/providers/${providerProfileId}`),

  // pagos en custodia
  createPayment: (payload) =>
    request("/billing/payments", { method: "POST", body: JSON.stringify(payload) }),
  getPayment: (paymentId) => request(`/billing/payments/${paymentId}`),
  listPaymentsForClient: (clientId) => request(`/billing/payments?client_id=${clientId}`),
  confirmCompletion: (paymentId, clientId) =>
    request(`/billing/payments/${paymentId}/confirm-completion?client_id=${clientId}`, {
      method: "POST",
    }),

  // servicios recurrentes / suscripciones
  listSubscriptions: (clientId) =>
    request(`/recurring/subscriptions?client_id=${clientId}`),
  createSubscription: (payload) =>
    request("/recurring/subscriptions", { method: "POST", body: JSON.stringify(payload) }),
  pauseSubscription: (subscriptionId) =>
    request(`/recurring/subscriptions/${subscriptionId}/pause`, { method: "POST" }),
  resumeSubscription: (subscriptionId) =>
    request(`/recurring/subscriptions/${subscriptionId}/resume`, { method: "POST" }),
  cancelSubscription: (subscriptionId) =>
    request(`/recurring/subscriptions/${subscriptionId}/cancel`, { method: "POST" }),
  generateOccurrence: (subscriptionId) =>
    request(`/recurring/subscriptions/${subscriptionId}/generate`, { method: "POST" }),
  listOccurrences: (subscriptionId) =>
    request(`/recurring/subscriptions/${subscriptionId}/occurrences`),

  // cotización con IA (Groq visión)
  createEstimate: async (formData) => {
    let response;
    try {
      response = await fetch(`${BASE_URL}/ai-quote/estimate`, {
        method: "POST",
        body: formData,
      });
    } catch (networkError) {
      throw new Error(`No se pudo conectar con la API en ${BASE_URL}. (${networkError.message})`);
    }
    const raw = await response.text();
    const data = raw ? JSON.parse(raw) : null;
    if (!response.ok) {
      const detail = data?.detail;
      const message = typeof detail === "string" ? detail : JSON.stringify(detail ?? data);
      throw new Error(message || `Error ${response.status}`);
    }
    return data;
  },
  listEstimates: (clientId) => request(`/ai-quote/estimates?client_id=${clientId}`),
  getEstimate: (quoteId) => request(`/ai-quote/estimates/${quoteId}`),
};

export { BASE_URL };
