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
  listMatchesForProvider: (providerUserId) =>
    request(`/matching/providers/${providerUserId}/matches`),
  acceptMatch: (matchId, providerUserId) =>
    request(`/matching/matches/${matchId}/accept`, {
      method: "POST",
      body: JSON.stringify({ provider_user_id: providerUserId }),
    }),
  getServiceRequest: (requestId) => request(`/matching/service-requests/${requestId}`),

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
  getProviderReputation: (providerProfileId) =>
    request(`/reputation/providers/${providerProfileId}`),

  // billing / comision
  getCommissionTiers: () => request("/billing/tiers"),
  getCommissionQuote: (providerProfileId, jobAmount) =>
    request(
      `/billing/commission/quote?provider_profile_id=${providerProfileId}&job_amount=${jobAmount}`
    ),

  // stripe connect / pagos
  getConnectStatus: (providerProfileId) =>
    request(`/billing/connect/status?provider_profile_id=${providerProfileId}`),
  createConnectOnboarding: (providerProfileId) =>
    request("/billing/connect/onboarding-link", {
      method: "POST",
      body: JSON.stringify({ provider_profile_id: providerProfileId }),
    }),
  listPaymentsForProvider: (providerUserId) =>
    request(`/billing/payments?provider_user_id=${providerUserId}`),
};

export { BASE_URL };
