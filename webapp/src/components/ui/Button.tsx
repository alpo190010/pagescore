import { forwardRef, type ButtonHTMLAttributes, type CSSProperties } from "react";
import { Slot } from "@radix-ui/react-slot";

/* ── Variant / Size / Shape tokens ── */

type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "coral"
  | "danger"
  | "on-dark"
  | "gradient";
type ButtonSize = "xs" | "sm" | "md" | "lg" | "icon";
type ButtonShape = "rounded" | "pill" | "card";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  shape?: ButtonShape;
  /** Render the child element instead of <button>, merging all props onto it. */
  asChild?: boolean;
}

/* ── Base classes ──
   Editorial aesthetic: medium weight (not bold), subtle transitions, tight tracking. */

const base =
  "inline-flex items-center justify-center gap-2 font-medium tracking-tight transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed polish-focus-ring";

/* ── Variant classes ──
   primary:   flat ink on paper (editorial CTA) — soft brand shadow + 1px lift on hover
   secondary: paper + hairline rule border
   ghost:     transparent, lifts on hover
   coral:     accent coral — reserved for critical / urgent flows
   danger:    alias for `coral` (kept for back-compat with earlier call sites)
   on-dark:   white pill — used inside dark CTA cards (dollar-loss)
   gradient:  retained for back-compat (ink gradient) */

const variants: Record<ButtonVariant, string> = {
  primary:
    "bg-[var(--ink)] text-[var(--paper)] shadow-[var(--shadow-brand-md)] hover:-translate-y-px hover:opacity-[.94] active:scale-[.98] active:translate-y-0",
  secondary:
    "bg-[var(--paper)] text-[var(--ink)] border border-[var(--rule-2)] hover:bg-[var(--bg-elev)] hover:border-[var(--ink)] active:scale-[.98]",
  ghost:
    "text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--bg-elev)] active:scale-[.98]",
  coral:
    "bg-[var(--accent)] text-[var(--accent-ink)] shadow-[var(--shadow-brand-md)] hover:bg-[var(--accent-dim)] active:scale-[.98]",
  danger:
    "bg-[var(--accent)] text-[var(--accent-ink)] shadow-[var(--shadow-brand-md)] hover:bg-[var(--accent-dim)] active:scale-[.98]",
  "on-dark":
    "bg-white text-[var(--ink)] font-bold hover:bg-white/90 active:scale-[.98]",
  gradient:
    "text-[var(--paper)] hover:brightness-110 active:scale-[.98]",
};

/* ── Size classes (DS · Components spec) ── */

const sizes: Record<ButtonSize, string> = {
  xs: "px-3 py-1.5 text-xs",
  sm: "px-4 py-2 text-[13px]",
  md: "px-[22px] py-[11px] text-sm",
  lg: "px-7 py-3.5 text-[15px]",
  icon: "w-10 h-10 p-0",
};

/* ── Shape classes ──
   Editorial default: pill (border-radius 999) — matches landing CTAs. */

const shapes: Record<ButtonShape, string> = {
  rounded: "rounded-full",
  pill: "rounded-full",
  card: "rounded-xl",
};

/* ── Component ── */

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      shape = "rounded",
      asChild = false,
      className = "",
      style,
      ...props
    },
    ref,
  ) => {
    const classes = `${base} ${variants[variant]} ${sizes[size]} ${shapes[shape]} ${className}`;

    // Gradient variant needs an inline style for the CSS custom-property background.
    const mergedStyle: CSSProperties | undefined =
      variant === "gradient"
        ? { background: "var(--gradient-primary)", ...style }
        : style;

    const Comp = asChild ? Slot : "button";

    return (
      <Comp
        ref={ref}
        className={classes}
        style={mergedStyle}
        {...props}
      />
    );
  },
);

Button.displayName = "Button";
export default Button;
export type { ButtonVariant, ButtonSize, ButtonShape };
