import type { HTMLAttributes } from "react";

/* DS score/state chip.
   Serif 800, uppercase, rounded-full — used for scored states (Good / Needs
   work / Critical) and transient states (Scanning, Ready). For admin plan /
   role metadata use the <PlanBadge> / <RoleBadge> primitives in MetaBadges.tsx. */

export type BadgeVariant = "ok" | "warn" | "err" | "muted" | "scanning";
export type BadgeSize = "sm" | "md";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: BadgeSize;
}

const base =
  "inline-flex items-center gap-1.5 rounded-full font-serif uppercase tracking-[0.02em]";

const sizes: Record<BadgeSize, string> = {
  sm: "px-2 py-0.5 text-[9px] font-semibold",
  md: "px-2.5 py-1 text-[10px] font-extrabold",
};

const variants: Record<BadgeVariant, string> = {
  ok: "bg-[var(--success-light)] text-[var(--success-text)]",
  warn: "bg-[var(--warning-light)] text-[var(--warning-text)]",
  err: "bg-[var(--error-light)] text-[var(--error-text)]",
  muted:
    "bg-[color-mix(in_srgb,var(--ink-3)_12%,transparent)] text-[var(--ink-3)]",
  scanning:
    "bg-[color-mix(in_srgb,var(--ink)_6%,transparent)] text-[var(--ink)]",
};

export default function Badge({
  variant = "muted",
  size = "md",
  className = "",
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}
      {...props}
    >
      {variant === "scanning" && (
        <span
          aria-hidden
          className="inline-block h-3 w-3 rounded-full border-[1.5px] border-[currentColor] border-t-transparent animate-spin"
        />
      )}
      {children ?? (variant === "scanning" ? "Scanning" : null)}
    </span>
  );
}
