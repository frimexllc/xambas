import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AiQuotePanel } from "./AiQuotePanel.jsx";
import { api } from "../lib/api.js";

vi.mock("../lib/api.js", () => ({
  api: {
    listEstimates: vi.fn(),
    createEstimate: vi.fn(),
    createServiceRequest: vi.fn(),
  },
}));

const SESSION = { userId: "client-1" };
const CATEGORIES = [{ id: "cat-1", name: "Plomeria", parent_id: null }];

const QUOTE = {
  id: "q1",
  scope: ["Cambiar llave", "Sellar fuga"],
  assumptions: [],
  images: [],
  price_min: 800,
  price_max: 1500,
  currency: "MXN",
  confidence: 0.72,
  suggested_title: "Reparación de fuga",
  suggested_description: "Fuga bajo el fregadero",
  category_id: "cat-1",
};

beforeEach(() => {
  vi.clearAllMocks();
  api.listEstimates.mockResolvedValue({ items: [] });
});

describe("AiQuotePanel", () => {
  it("muestra el historial de cotizaciones al montar", async () => {
    api.listEstimates.mockResolvedValue({ items: [QUOTE] });
    render(<AiQuotePanel session={SESSION} categories={CATEGORIES} onError={vi.fn()} />);

    expect(await screen.findByTestId("ai-quote-history-q1")).toBeInTheDocument();
    expect(api.listEstimates).toHaveBeenCalledWith("client-1");
  });

  it("sin fotos: avisa y no llama a la API", async () => {
    const onError = vi.fn();
    const user = userEvent.setup();
    render(<AiQuotePanel session={SESSION} categories={CATEGORIES} onError={onError} />);

    await user.selectOptions(screen.getByTestId("ai-quote-category-select"), "cat-1");
    await user.click(screen.getByTestId("ai-quote-submit-btn"));

    expect(onError).toHaveBeenCalledWith("Sube al menos una foto del trabajo.");
    expect(api.createEstimate).not.toHaveBeenCalled();
  });

  it("con categoría + foto: llama createEstimate y muestra el resultado", async () => {
    api.createEstimate.mockResolvedValue({ quote: QUOTE });
    const user = userEvent.setup();
    render(<AiQuotePanel session={SESSION} categories={CATEGORIES} onError={vi.fn()} />);

    await user.selectOptions(screen.getByTestId("ai-quote-category-select"), "cat-1");
    const file = new File([new Uint8Array([1, 2, 3])], "cocina.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByTestId("ai-quote-files-input"), file);
    await user.click(screen.getByTestId("ai-quote-submit-btn"));

    expect(api.createEstimate).toHaveBeenCalledTimes(1);
    const formData = api.createEstimate.mock.calls[0][0];
    expect(formData).toBeInstanceOf(FormData);
    expect(formData.get("category_id")).toBe("cat-1");
    expect(formData.get("client_id")).toBeNull(); // ya no se manda

    expect(await screen.findByTestId("ai-quote-result")).toBeInTheDocument();
    expect(screen.getByTestId("ai-quote-price")).toHaveTextContent("800");
  });
});
