/** A spinner with a message that screen readers announce. */
export function Loading({ message, detail }: { message: string; detail?: string }) {
  return (
    <div className="loading" role="status">
      <span className="spinner" aria-hidden="true" />
      <div>
        <strong>{message}</strong>
        {detail && <p className="hint">{detail}</p>}
      </div>
    </div>
  );
}
