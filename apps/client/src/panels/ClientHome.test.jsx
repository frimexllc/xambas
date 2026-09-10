import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClientHome } from "./ClientHome.jsx";
import { api } from "../lib/api.js";

// Sólo nos importa el ruteo de pestañas: stub de los paneles y del api.
vi.mock("../lib/api.js", () => ({
  api: { listCategories: vi.fn().mockResolvedValue({ items: [] }) },
}));
vi.mock("./RequestsPanel.jsx", () => ({ RequestsPanel: () => <div>panel:requests</div> }));
vi.mock("./RecurringPanel.jsx", () => ({ RecurringPanel: () => <div>panel:recurring</div> }));
vi.mock("./AiQuotePanel.jsx", () => ({ AiQuotePanel: () => <div>panel:ai-quote</div> }));
vi.mock("./MilestonesPanel.jsx", () => ({ MilestonesPanel: () => <div>panel:milestones</div> }));

beforeEach(() => vi.clearAllMocks());

describe("ClientHome", () => {
  it("arranca en la pestaña de solicitudes", async () => {
    render(<ClientHome session={{ userId: "u1" }} onError={vi.fn()} />);
    expect(await screen.findByText("panel:requests")).toBeInTheDocument();
    expect(api.listCategories).toHaveBeenCalledTimes(1);
  });

  it("cambia de panel al pulsar cada pestaña", async () => {
    const user = userEvent.setup();
    render(<ClientHome session={{ userId: "u1" }} onError={vi.fn()} />);

    await user.click(screen.getByTestId("tab-recurring"));
    expect(screen.getByText("panel:recurring")).toBeInTheDocument();
    expect(screen.queryByText("panel:requests")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("tab-ai-quote"));
    expect(screen.getByText("panel:ai-quote")).toBeInTheDocument();

    await user.click(screen.getByTestId("tab-milestones"));
    expect(screen.getByText("panel:milestones")).toBeInTheDocument();
  });
});
