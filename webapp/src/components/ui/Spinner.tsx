interface SpinnerProps {
  className?: string;
}

export default function Spinner({ className = "w-10 h-10" }: SpinnerProps) {
  return (
    <div
      className={`mx-auto rounded-full border-[3px] border-[var(--border)] border-t-[var(--brand)] animate-spin ${className}`}
      aria-label="Loading"
    />
  );
}
