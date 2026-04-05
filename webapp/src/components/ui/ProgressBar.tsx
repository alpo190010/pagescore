interface ProgressBarProps {
  value: number;
  max: number;
  color?: string;
  trackClass?: string;
}

export default function ProgressBar({
  value,
  max,
  color = "var(--brand)",
  trackClass = "h-2",
}: ProgressBarProps) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;

  return (
    <div
      className={`${trackClass} bg-[var(--surface-container-high)] rounded-full overflow-hidden`}
    >
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, background: color }}
      />
    </div>
  );
}
