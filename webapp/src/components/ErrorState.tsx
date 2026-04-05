interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div
      className="text-center py-12 rounded-2xl border border-[var(--outline-variant)]"
      style={{ background: "var(--surface-container-lowest)" }}
    >
      <p className="text-sm text-[var(--error)] font-medium mb-4" role="alert">
        {message}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="px-6 py-2 rounded-xl text-sm font-semibold text-white cursor-pointer"
        style={{ background: "var(--brand)" }}
      >
        Retry
      </button>
    </div>
  );
}
