interface SkeletonProps {
  className?: string;
}

export default function Skeleton({ className = "h-20 rounded-2xl" }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse ${className}`}
      style={{ background: "var(--surface-container-low)" }}
    />
  );
}
