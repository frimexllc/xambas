import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RequestsPanel } from "./RequestsPanel.jsx";
import { api } from "../lib/api.js";

vi.mock("../lib/api.js", () => ({
  api: {
    listServiceRequests: vi.fn(),
    createServiceRequest: vi.fn(),
    getServiceRequest: vi.fn(),
    rerunMatching: vi.fn(),
  },
}));

const SESSION = { userId: "client-1" };
const CATEGORIES = [{ id: "cat-1", name: "Plomeria", parent_id: null }];

beforeEach(() => {
  vi.clearAllMocks();
  api.listServiceRequests.mockResolvedValue({ items: [] });
});

describe("RequestsPanel", () => {
  it("muestra las solicitudes existentes", async () => {
    api.listServiceRequests.mockResolvedValue({
      items: [{ id: "r1", title: "Fuga en cocina", category_name: "Plomeria", city: "CDMX", status: "matched" }],
    });
    render(<RequestsPanel session={SESSION} categories={CATEGORIES} onError={vi.fn()} />);

    expect(await screen.findByText("Fuga en cocina")).toBeInTheDocument();
  });

  it("crea una solicitud y navega al detalle", async () => {
    api.createServiceRequest.mockResolvedValue({ request: { id: "r-new" } });
    api.getServiceRequest.mockResolvedValue({
      request: {
        id: "r-new",
        title: "Fuga en cocina",
        category_name: "Plomeria",
        city: "CDMX",
        coverage_zone: "Centro",
        description: "Gotea sin parar",
        status: "matched",
      },
      matches: [],
    });
    const user = userEvent.setup();
    render(<RequestsPanel session={SESSION} categories={CATEGORIES} onError={vi.fn()} />);

    await user.selectOptions(screen.getByRole("combobox"), "cat-1");
    await user.type(screen.getByPlaceholderText("Fuga de agua en la cocina"), "Fuga en cocina");
    await user.type(
      screen.getByPlaceholderText(/Cuentanos que necesitas/i),
      "Gotea sin parar desde ayer"
    );
    await user.type(screen.getByPlaceholderText("CDMX"), "CDMX");
    await user.type(screen.getByPlaceholderText("CDMX-Centro"), "Centro");
    await user.click(screen.getByRole("button", { name: /publicar y buscar proveedores/i }));

    expect(api.createServiceRequest).toHaveBeenCalledWith(
      expect.objectContaining({ category_id: "cat-1", title: "Fuga en cocina", country_code: "MX" })
    );
    // el detalle carga la solicitud recién creada
    expect(await screen.findByText("Proveedores sugeridos (0)")).toBeInTheDocument();
    expect(api.getServiceRequest).toHaveBeenCalledWith("r-new");
  });

  it("sin categoría: avisa y no publica", async () => {
    const onError = vi.fn();
    const user = userEvent.setup();
    render(<RequestsPanel session={SESSION} categories={CATEGORIES} onError={onError} />);

    await user.type(screen.getByPlaceholderText("Fuga de agua en la cocina"), "Algo");
    await user.type(screen.getByPlaceholderText(/Cuentanos que necesitas/i), "Descripcion larga aqui");
    await user.type(screen.getByPlaceholderText("CDMX"), "CDMX");
    await user.type(screen.getByPlaceholderText("CDMX-Centro"), "Centro");
    await user.click(screen.getByRole("button", { name: /publicar y buscar proveedores/i }));

    expect(api.createServiceRequest).not.toHaveBeenCalled();
  });
});
