// Estado vacío reutilizable: ícono de trazo + título + una pista de la
// acción que lo llenaría. `icon` es un nodo (ver components/icons.jsx), no
// un emoji — la interfaz de trabajo usa el mismo lenguaje de trazo técnico
// que el resto del sistema.
export function EmptyState({ icon, title, hint, testId }) {
  return (
    <div className="empty-state" data-testid={testId}>
      {icon && (
        <span className="empty-state-icon" aria-hidden="true">
          {icon}
        </span>
      )}
      <strong>{title}</strong>
      {hint && <p>{hint}</p>}
    </div>
  );
}
