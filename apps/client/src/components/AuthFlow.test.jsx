import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthFlow } from "./AuthFlow.jsx";
import { api } from "../lib/api.js";

vi.mock("../lib/api.js", () => ({
  api: {
    bootstrap: vi.fn(),
    requestOtp: vi.fn(),
    verifyOtp: vi.fn(),
    login: vi.fn(),
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AuthFlow", () => {
  it("registro → OTP → verificación entrega userId y token", async () => {
    api.bootstrap.mockResolvedValue({ user: { id: "u1" } });
    api.requestOtp.mockResolvedValue({ challenge_id: "c1", debug_code: "123456" });
    api.verifyOtp.mockResolvedValue({
      user: { id: "u1", email: "a@b.com", phone: "+521" },
      session: { token: "tok-1" },
    });
    const onAuthenticated = vi.fn();
    const user = userEvent.setup();

    render(<AuthFlow onAuthenticated={onAuthenticated} onError={vi.fn()} />);

    await user.type(screen.getByPlaceholderText("tu@correo.com"), "a@b.com");
    await user.type(screen.getByPlaceholderText("+5215500000000"), "+521");
    await user.click(screen.getByRole("button", { name: /continuar/i }));

    // paso OTP: muestra el debug_code en modo dev
    expect(await screen.findByText("123456")).toBeInTheDocument();
    expect(api.bootstrap).toHaveBeenCalledWith(
      expect.objectContaining({ email: "a@b.com", role: "client" })
    );

    await user.type(screen.getByPlaceholderText("123456"), "123456");
    await user.click(screen.getByRole("button", { name: /verificar y entrar/i }));

    expect(onAuthenticated).toHaveBeenCalledWith({
      userId: "u1",
      email: "a@b.com",
      phone: "+521",
      token: "tok-1",
    });
  });

  it("login: identificador → OTP → sesión", async () => {
    api.login.mockResolvedValue({
      user_id: "u9",
      challenge_id: "c9",
      debug_code: "654321",
      delivery_target: "+52155****99",
    });
    api.verifyOtp.mockResolvedValue({
      user: { id: "u9", email: "x@y.com", phone: "+521" },
      session: { token: "tok-login" },
    });
    const onAuthenticated = vi.fn();
    const user = userEvent.setup();

    render(<AuthFlow onAuthenticated={onAuthenticated} onError={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: /inicia sesion/i }));

    await user.type(screen.getByPlaceholderText("+5215500000000"), "+5215551234599");
    await user.click(screen.getByRole("button", { name: /enviar codigo/i }));

    expect(await screen.findByText("654321")).toBeInTheDocument();
    expect(api.login).toHaveBeenCalledWith({ identifier: "+5215551234599" });
    expect(api.bootstrap).not.toHaveBeenCalled();

    await user.type(screen.getByPlaceholderText("123456"), "654321");
    await user.click(screen.getByRole("button", { name: /verificar y entrar/i }));

    expect(onAuthenticated).toHaveBeenCalledWith(
      expect.objectContaining({ userId: "u9", token: "tok-login" })
    );
  });

  it("propaga el error de bootstrap sin avanzar al paso OTP", async () => {
    api.bootstrap.mockRejectedValue(new Error("ya existe un usuario con ese email"));
    const onError = vi.fn();
    const user = userEvent.setup();

    render(<AuthFlow onAuthenticated={vi.fn()} onError={onError} />);
    await user.type(screen.getByPlaceholderText("tu@correo.com"), "a@b.com");
    await user.type(screen.getByPlaceholderText("+5215500000000"), "+521");
    await user.click(screen.getByRole("button", { name: /continuar/i }));

    expect(onError).toHaveBeenCalledWith("ya existe un usuario con ese email");
    expect(screen.queryByPlaceholderText("123456")).not.toBeInTheDocument();
  });
});
