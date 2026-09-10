import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RecurringPanel } from "./RecurringPanel.jsx";
import { api } from "../lib/api.js";

vi.mock("../lib/api.js", () => ({
  api: {
    listSubscriptions: vi.fn(),
    createSubscription: vi.fn(),
    pauseSubscription: vi.fn(),
    resumeSubscription: vi.fn(),
    cancelSubscription: vi.fn(),
    generateOccurrence: vi.fn(),
    listOccurrences: vi.fn(),
  },
}));

const SESSION = { userId: "client-1" };
const CATEGORIES = [{ id: "cat-1", name: "Limpieza Basica", parent_id: "p1" }];

function activeSub(overrides = {}) {
  return {
    id: "sub-1",
    title: "Limpieza semanal",
    category_name: "Limpieza Basica",
    frequency: "weekly",
    coverage_zone: "Roma Norte",
    status: "active",
    next_run_date: "2026-09-15",
    occurrences_count: 0,
    budget_amount: 500,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  api.listSubscriptions.mockResolvedValue({ items: [] });
});

describe("RecurringPanel", () => {
  it("lista las suscripciones del cliente", async () => {
    api.listSubscriptions.mockResolvedValue({ items: [activeSub()] });
    render(<RecurringPanel session={SESSION} categories={CATEGORIES} onError={vi.fn()} />);

    expect(await screen.findByText("Limpieza semanal")).toBeInTheDocument();
    expect(api.listSubscriptions).toHaveBeenCalledWith("client-1");
  });

  it("crea una suscripción y refresca la lista", async () => {
    api.createSubscription.mockResolvedValue({ subscription: activeSub() });
    const user = userEvent.setup();
    render(<RecurringPanel session={SESSION} categories={CATEGORIES} onError={vi.fn()} />);

    await user.selectOptions(screen.getByTestId("subscription-category-select"), "cat-1");
    await user.type(screen.getByTestId("subscription-title-input"), "Limpieza semanal");
    await user.type(
      screen.getByTestId("subscription-description-input"),
      "Limpieza completa cada semana"
    );
    await user.type(screen.getByTestId("subscription-city-input"), "CDMX");
    await user.type(screen.getByTestId("subscription-zone-input"), "Roma Norte");
    await user.click(screen.getByTestId("subscription-submit-btn"));

    expect(api.createSubscription).toHaveBeenCalledWith(
      expect.objectContaining({
        category_id: "cat-1",
        title: "Limpieza semanal",
        country_code: "MX",
        frequency: "weekly",
      })
    );
    // refresca: 1 al montar + 1 tras crear
    expect(api.listSubscriptions).toHaveBeenCalledTimes(2);
  });

  it("no llama a la API si falta la categoría", async () => {
    const onError = vi.fn();
    const user = userEvent.setup();
    render(<RecurringPanel session={SESSION} categories={CATEGORIES} onError={onError} />);

    await user.type(screen.getByTestId("subscription-title-input"), "algo");
    await user.type(screen.getByTestId("subscription-description-input"), "descripcion larga");
    await user.type(screen.getByTestId("subscription-city-input"), "CDMX");
    await user.type(screen.getByTestId("subscription-zone-input"), "Centro");
    // el <select> requerido bloquea el submit del form; forzamos el click igual
    await user.click(screen.getByTestId("subscription-submit-btn"));

    expect(api.createSubscription).not.toHaveBeenCalled();
  });

  it("pausar una suscripción activa llama al endpoint correcto", async () => {
    api.listSubscriptions.mockResolvedValue({ items: [activeSub()] });
    api.pauseSubscription.mockResolvedValue({ subscription: activeSub({ status: "paused" }) });
    const user = userEvent.setup();
    render(<RecurringPanel session={SESSION} categories={CATEGORIES} onError={vi.fn()} />);

    const item = await screen.findByTestId("subscription-item-sub-1");
    await user.click(within(item).getByTestId("subscription-pause-sub-1"));

    expect(api.pauseSubscription).toHaveBeenCalledWith("sub-1");
  });
});
