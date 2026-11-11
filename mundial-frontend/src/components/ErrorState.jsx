// error card with a retry button
export default function ErrorState({ text, onRetry }) {
  return (
    <div className="glass-card p-8 text-center" role="alert">
      <p className="text-miss mb-4">{text}</p>
      {onRetry && <button onClick={onRetry} className="btn-secondary">Spróbuj ponownie</button>}
    </div>
  );
}
