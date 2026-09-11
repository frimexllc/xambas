// Estado vacío reutilizable: ícono + mensaje corto + una pista de la acción
// que lo llenaría. Sustituye a los "Aún no tienes..." sueltos en texto plano.
export function EmptyState({ icon = "📭", title, hint, testId }) {
  return (
    <div className="empty-state" data-testid={testId}>
      <span className="empty-state-icon" aria-hidden="true">
        {icon}
      </span>
      <strong>{title}</strong>
      {hint && <p>{hint}</p>}
    </div>
  );
}
