"use client";

import { useState } from "react";
import { CaretDownIcon, CaretUpIcon, CheckCircleIcon, XCircleIcon, StorefrontIcon, ArrowsClockwiseIcon } from "@phosphor-icons/react";
import Button from "@/components/ui/Button";
import {
  type StoreAnalysisData,
  scoreColorTintBg,
  scoreColorText,
  CATEGORY_LABELS,
  CATEGORY_SVG,
  STORE_WIDE_DIMENSIONS,
} from "@/lib/analysis";

/* ══════════════════════════════════════════════════════════════
   StoreHealth — Store-wide dimension scores (7 dimensions)
   Renders above the ProductGrid on /scan/[domain] pages.
   ══════════════════════════════════════════════════════════════ */

interface StoreHealthProps {
  storeAnalysis: StoreAnalysisData;
  /** Handler to force a fresh store-wide scan (bypasses 7-day cache). */
  onRefresh?: () => void | Promise<void>;
  /** Whether a refresh is currently in flight. */
  refreshing?: boolean;
}

/** Relative-time formatter. Returns strings like "just now", "3h ago", "2w ago". */
function formatRelative(iso: string | undefined): string | null {
  if (!iso) return null;
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return null;
  const diffSec = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (diffSec < 60) return "just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  const diffWk = Math.floor(diffDay / 7);
  if (diffWk < 5) return `${diffWk}w ago`;
  const diffMo = Math.floor(diffDay / 30);
  return `${diffMo}mo ago`;
}

/** Format signal key → human label: "hasShopPay" → "Has Shop Pay" */
function formatSignalKey(key: string): string {
  return key
    .replace(/^(has|is|uses)/, (m) => m + " ")
    .replace(/([A-Z])/g, " $1")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^./, (c) => c.toUpperCase());
}

export default function StoreHealth({ storeAnalysis, onRefresh, refreshing = false }: StoreHealthProps) {
  const [expandedDimension, setExpandedDimension] = useState<string | null>(null);
  const [cardExpanded, setCardExpanded] = useState<boolean>(false);
  const { score, categories, signals, updatedAt } = storeAnalysis;
  const relative = formatRelative(updatedAt);

  const storeKeys = Array.from(STORE_WIDE_DIMENSIONS).filter(
    (k) => categories[k as keyof typeof categories] !== undefined,
  );

  if (storeKeys.length === 0) return null;

  return (
    <section className="bg-[var(--surface)] border-b border-[var(--border)]">
      {/* ── Header row (single line; clickable to collapse/expand) ── */}
      <button
        type="button"
        onClick={() => setCardExpanded((v) => !v)}
        aria-expanded={cardExpanded}
        aria-controls="store-health-body"
        className="w-full flex items-center gap-3 text-left px-4 py-3 hover:bg-[var(--surface-container-low)] transition-colors"
      >
        <div
          className="w-7 h-7 rounded-xl flex items-center justify-center shrink-0"
          style={{ background: "var(--brand)", color: "var(--on-primary)" }}
        >
          <StorefrontIcon size={16} weight="fill" />
        </div>
        <h3
          className="flex-1 min-w-0 text-sm font-bold leading-tight font-display truncate"
          style={{ color: "var(--on-surface)" }}
        >
          Store Health
        </h3>
        <div
          className="rounded-xl px-2.5 py-1 text-sm font-extrabold tabular-nums font-display shrink-0"
          style={{
            background: scoreColorTintBg(score),
            color: scoreColorText(score),
          }}
          aria-label={`Store health score ${score} out of 100`}
        >
          {score}
        </div>
        {onRefresh && (
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.stopPropagation();
              if (!refreshing) onRefresh();
            }}
            onKeyDown={(e) => {
              if ((e.key === "Enter" || e.key === " ") && !refreshing) {
                e.stopPropagation();
                e.preventDefault();
                onRefresh();
              }
            }}
            aria-disabled={refreshing}
            aria-label="Re-run store-wide scan"
            title="Re-run store-wide scan"
            className={`w-7 h-7 rounded-lg inline-flex items-center justify-center shrink-0 transition-colors ${refreshing ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:bg-[var(--surface-container-high)]"}`}
            style={{ color: "var(--on-surface-variant)" }}
          >
            <ArrowsClockwiseIcon
              size={14}
              weight="bold"
              className={refreshing ? "animate-spin" : ""}
            />
          </span>
        )}
        <span
          className="shrink-0"
          style={{ color: "var(--on-surface-variant)" }}
          aria-hidden="true"
        >
          {cardExpanded ? (
            <CaretUpIcon size={14} weight="bold" />
          ) : (
            <CaretDownIcon size={14} weight="bold" />
          )}
        </span>
      </button>

      {cardExpanded && (
      <div id="store-health-body" className="px-4 pb-4">
      {/* ── Meta line (revealed when expanded) ── */}
      <p
        className="text-[11px] pb-2"
        style={{ color: "var(--on-surface-variant)" }}
      >
        Store-wide scores · applies to all products
        {relative && (
          <>
            <span className="mx-1" aria-hidden="true">·</span>
            <span>Last scanned {relative}</span>
          </>
        )}
      </p>
      {/* ── Dimension grid ── */}
      <div className="grid grid-cols-1 gap-1.5">
        {storeKeys.map((key) => {
          const dimScore = (categories as Record<string, number>)[key] ?? 0;
          const label = CATEGORY_LABELS[key] || key;
          const icon = CATEGORY_SVG[key];
          const dimSignals = signals?.[key as keyof typeof signals] as
            | Record<string, boolean>
            | undefined;
          const isExpanded = expandedDimension === key;
          const hasSignals = dimSignals && Object.keys(dimSignals).length > 0;

          return (
            <div key={key}>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setExpandedDimension(isExpanded ? null : key)}
                aria-expanded={isExpanded}
                className="w-full flex items-center gap-2 rounded-xl px-2.5 py-2 h-auto"
                style={{ cursor: hasSignals ? "pointer" : "default" }}
              >
                <span
                  className="w-6 h-6 rounded-xl flex items-center justify-center shrink-0"
                  style={{
                    background: scoreColorTintBg(dimScore),
                    color: scoreColorText(dimScore),
                  }}
                >
                  {icon}
                </span>
                <span
                  className="flex-1 text-left text-xs font-medium truncate"
                  style={{ color: "var(--on-surface)" }}
                >
                  {label}
                </span>
                <span
                  className="text-xs font-bold tabular-nums rounded px-1.5 py-0.5 font-display"
                  style={{
                    background: scoreColorTintBg(dimScore),
                    color: scoreColorText(dimScore),
                  }}
                >
                  {dimScore}
                </span>
                {hasSignals && (
                  <span style={{ color: "var(--on-surface-variant)" }}>
                    {isExpanded ? (
                      <CaretUpIcon size={12} weight="bold" />
                    ) : (
                      <CaretDownIcon size={12} weight="bold" />
                    )}
                  </span>
                )}
              </Button>

              {/* ── Signal checklist (expanded) ── */}
              {isExpanded && hasSignals && (
                <div className="pl-11 pr-2 pb-2 space-y-1">
                  {Object.entries(dimSignals!).map(([sigKey, sigVal]) => (
                    <div
                      key={sigKey}
                      className="flex items-center gap-1.5 text-[11px]"
                      style={{ color: "var(--on-surface-variant)" }}
                    >
                      {sigVal ? (
                        <CheckCircleIcon
                          size={13}
                          weight="fill"
                          style={{ color: "var(--success-text)" }}
                        />
                      ) : (
                        <XCircleIcon
                          size={13}
                          weight="fill"
                          style={{ color: "var(--error-text)" }}
                        />
                      )}
                      <span className="truncate">{formatSignalKey(sigKey)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      </div>
      )}
    </section>
  );
}
