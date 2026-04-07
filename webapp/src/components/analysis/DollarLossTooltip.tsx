"use client";

import { InfoIcon } from "@phosphor-icons/react";
import Button from "@/components/ui/Button";
import Tooltip from "@/components/ui/Tooltip";

/* ══════════════════════════════════════════════════════════════
   DollarLossTooltip — (i) icon that explains dollar loss calc.
   Uses shared Tooltip primitive for hover display + arrow.

   Usage:
     <DollarLossTooltip />                     — default 16px, white icon
     <DollarLossTooltip size={13} variant="muted" />  — smaller, muted color
   ══════════════════════════════════════════════════════════════ */

interface DollarLossTooltipProps {
  /** Icon size in px. Default 16. */
  size?: number;
  /** "light" = white icon (on dark bg), "muted" = muted icon (on light bg). */
  variant?: "light" | "muted";
}

const TOOLTIP_CONTENT = (
  <div className="w-64">
    <p className="font-semibold text-white mb-1">How we calculate this</p>
    <p className="text-white/90">
      Based on product price, category conversion rate benchmarks (Shopify &amp;
      industry data), and page scores — estimating lost revenue per 1,000
      visitors vs. top stores in your category.
    </p>
  </div>
);

export default function DollarLossTooltip({
  size = 16,
  variant = "light",
}: DollarLossTooltipProps) {
  const iconClass =
    variant === "light"
      ? "text-white/40 hover:text-white/70"
      : "text-[var(--warning-text)] opacity-40 hover:opacity-70";

  return (
    <Tooltip content={TOOLTIP_CONTENT} side="bottom" sideOffset={8}>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="How we calculate this"
        className={`transition-colors ${iconClass} w-auto h-auto p-0 flex-shrink-0`}
      >
        <InfoIcon size={size} weight="regular" />
      </Button>
    </Tooltip>
  );
}
