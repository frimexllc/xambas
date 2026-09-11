import { useState } from "react";
import { api } from "../lib/api.js";

// Autenticación del cliente: registro (bootstrap) o login de una cuenta
// existente; ambos caminos terminan en verificación OTP.
export function AuthFlow({ onAuthenticated, onError }) {
  const [mode, setMode] = useState("register"); // register | login
  const [step, setStep] = useState("form"); // form | otp
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ email: "", phone: "" });
  const [identifier, setIdentifier] = useState("");
  const [otpState, setOtpState] = useState(null); // { userId, challengeId, debugCode, target }
  const [code, setCode] = useState("");

  function switchMode(next) {
    setMode(next);
    setStep("form");
    setOtpState(null);
    setCode("");
  }

  async function handleRegister(event) {
    event.preventDefault();
    setLoading(true);
    try {
      const result = await api.bootstrap({
        email: form.email.trim(),
        phone: form.phone.trim(),
        role: "client",
        locale: "es-MX",
      });
      const userId = result.user.id;
      const otp = await api.requestOtp({ user_id: userId, purpose: "registration", channel: "sms" });
      setOtpState({
        userId,
        challengeId: otp.challenge_id,
        debugCode: otp.debug_code,
        target: otp.delivery_target || form.phone,
      });
      setStep("otp");
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin(event) {
    event.preventDefault();
    setLoading(true);
    try {
      const result = await api.login({ identifier: identifier.trim() });
      setOtpState({
        userId: result.user_id,
        challengeId: result.challenge_id,
        debugCode: result.debug_code,
        target: result.delivery_target,
      });
      setStep("otp");
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(event) {
    event.preventDefault();
    setLoading(true);
    try {
      const result = await api.verifyOtp({
        user_id: otpState.userId,
        challenge_id: otpState.challengeId,
        code: code.trim(),
        device_name: "xambas-client-web",
      });
      onAuthenticated({
        userId: result.user.id,
        email: result.user.email,
        phone: result.user.phone,
        token: result.session.token,
      });
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (step === "otp") {
    return (
      <section className="card auth-card">
        <span className="mono-label accent auth-kicker">Verificación · OTP</span>
        <h2>Verifica tu telefono</h2>
        <p className="muted">
          Enviamos un codigo por SMS a <strong>{otpState?.target}</strong>.
        </p>
        {otpState?.debugCode && (
          <p className="hint">
            Modo desarrollo: tu codigo es <strong className="mono">{otpState.debugCode}</strong>
          </p>
        )}
        <form onSubmit={handleVerify} className="stack">
          <label>
            <span className="field-label">Código de 6 dígitos</span>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={10}
              required
              placeholder="123456"
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "Verificando..." : "Verificar y entrar"}
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => switchMode(mode)}>
            ← Empezar de nuevo
          </button>
        </form>
      </section>
    );
  }

  if (mode === "login") {
    return (
      <section className="card auth-card">
        <span className="mono-label accent auth-kicker">Acceso · Cliente</span>
        <h2>Inicia sesion</h2>
        <p className="muted">Te enviaremos un codigo al telefono de tu cuenta.</p>
        <form onSubmit={handleLogin} className="stack">
          <label>
            <span className="field-label">Teléfono o correo</span>
            <input
              required
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="+5215500000000"
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "Enviando codigo..." : "Enviar codigo"}
          </button>
        </form>
        <p className="muted auth-switch">
          ¿No tienes cuenta?{" "}
          <button type="button" className="link-btn" onClick={() => switchMode("register")}>
            Crear una
          </button>
        </p>
      </section>
    );
  }

  return (
    <section className="card auth-card">
      <span className="mono-label accent auth-kicker">Registro · Cliente</span>
      <h2>Crea tu cuenta de cliente</h2>
      <p className="muted">Publica lo que necesitas y te conectamos con proveedores verificados.</p>
      <form onSubmit={handleRegister} className="stack">
        <label>
          <span className="field-label">Correo</span>
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="tu@correo.com"
          />
        </label>
        <label>
          <span className="field-label">Teléfono (con lada)</span>
          <input
            required
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            placeholder="+5215500000000"
          />
        </label>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Creando..." : "Continuar"}
        </button>
      </form>
      <p className="muted auth-switch">
        ¿Ya tienes cuenta?{" "}
        <button type="button" className="link-btn" onClick={() => switchMode("login")}>
          Inicia sesion
        </button>
      </p>
    </section>
  );
}
