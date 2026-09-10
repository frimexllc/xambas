import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

export function ChatPanel({ matchId, senderId, senderRole, onClose, onError }) {
  const [threadId, setThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [contactUnlocked, setContactUnlocked] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const thread = await api.getOrCreateThread(matchId);
      setThreadId(thread.id);
      setContactUnlocked(thread.contact_unlocked);
      const response = await api.listMessages(thread.id);
      setMessages(response.items);
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matchId]);

  async function handleSend(event) {
    event.preventDefault();
    if (!body.trim()) return;
    try {
      await api.sendMessage(threadId, { sender_id: senderId, sender_role: senderRole, body });
      setBody("");
      const response = await api.listMessages(threadId);
      setMessages(response.items);
    } catch (err) {
      onError(err.message);
    }
  }

  return (
    <div className="chat-panel">
      <div className="space-between">
        <strong>Chat con el proveedor</strong>
        <button className="btn btn-ghost" onClick={onClose}>
          Cerrar
        </button>
      </div>
      <p className={contactUnlocked ? "chat-lock unlocked" : "chat-lock"}>
        {contactUnlocked
          ? "🔓 Contacto desbloqueado: ya pueden compartir telefono, correo o direccion."
          : "🔒 Protegemos tu privacidad: telefono, correo y redes se ocultan hasta aceptar el trabajo."}
      </p>
      {loading && <p className="muted">Cargando mensajes...</p>}
      <ul className="message-list">
        {messages.map((message) => (
          <li
            key={message.id}
            className={message.sender_role === senderRole ? "message mine" : "message"}
          >
            <span>{message.body}</span>
            {message.flagged && (
              <span className="flag-note">Se oculto un intento de compartir contacto directo</span>
            )}
          </li>
        ))}
        {!loading && messages.length === 0 && <p className="muted">Aun no hay mensajes.</p>}
      </ul>
      <form onSubmit={handleSend} className="row">
        <input
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Escribe un mensaje..."
        />
        <button className="btn btn-primary" type="submit">
          Enviar
        </button>
      </form>
    </div>
  );
}
