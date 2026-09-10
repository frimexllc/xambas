import { useState } from "react";
import { api } from "../lib/api.js";

// Autenticacion: bootstrap + verificacion OTP.
export function AuthFlow({ onAuthenticated, onError }) {
  const [step, setStep] = useState("register"); // register | otp
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ email: "", phone: "" });
  const [otpState, setOtpState] = useState(null); // { userId, challengeId, debugCode }
  const [code, setCode] = useState("");

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
      setOtpState({ userId, challengeId: otp.challenge_id, debugCode: otp.debug_code });
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
        <h2>Verifica tu telefono</h2>
        <p className="muted">
          Enviamos un codigo por SMS a <strong>{form.phone}</strong>.
        </p>
        {otpState?.debugCode && (
          <p className="hint">
            Modo desarrollo: tu codigo es <strong>{otpState.debugCode}</strong>
          </p>
        )}
        <form onSubmit={handleVerify} className="stack">
          <label>
            Codigo de 6 digitos
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
        </form>
      </section>
    );
  }

  return (
    <section className="card auth-card">
      <h2>Crea tu cuenta de cliente</h2>
      <p className="muted">Publica lo que necesitas y te conectamos con proveedores verificados.</p>
      <form onSubmit={handleRegister} className="stack">
        <label>
          Correo
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="tu@correo.com"
          />
        </label>
        <label>
          Telefono (con lada)
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
    </section>
  );
}
