import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, setAuthToken } from "./api.js";

function mockFetchOnce(body, ok = true) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status: ok ? 200 : 400,
    text: async () => JSON.stringify(body),
  });
}

describe("api client", () => {
  beforeEach(() => {
    setAuthToken(null);
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("no manda Authorization cuando no hay token", async () => {
    mockFetchOnce({ items: [] });
    await api.listCategories();
    const [, options] = global.fetch.mock.calls[0];
    expect(options.headers.Authorization).toBeUndefined();
    expect(options.headers["Content-Type"]).toBe("application/json");
  });

  it("adjunta Authorization: Bearer tras setAuthToken", async () => {
    setAuthToken("tok-123");
    mockFetchOnce({ items: [] });
    await api.listSubscriptions("u1");
    const [, options] = global.fetch.mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer tok-123");
  });

  it("setAuthToken(null) limpia el header", async () => {
    setAuthToken("tok-123");
    setAuthToken(null);
    mockFetchOnce({ items: [] });
    await api.listSubscriptions("u1");
    const [, options] = global.fetch.mock.calls[0];
    expect(options.headers.Authorization).toBeUndefined();
  });

  it("createEstimate manda el Bearer en el multipart", async () => {
    setAuthToken("tok-xyz");
    mockFetchOnce({ quote: { id: "q1" } });
    await api.createEstimate(new FormData());
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toMatch(/\/ai-quote\/estimate$/);
    expect(options.headers.Authorization).toBe("Bearer tok-xyz");
    // no forzamos Content-Type: el navegador pone el boundary del multipart
    expect(options.headers["Content-Type"]).toBeUndefined();
  });

  it("propaga el detail del error de la API", async () => {
    mockFetchOnce({ detail: "token de sesion invalido o revocado" }, false);
    await expect(api.listSubscriptions("u1")).rejects.toThrow(
      "token de sesion invalido o revocado"
    );
  });
});
