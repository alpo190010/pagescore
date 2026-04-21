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
  const { score, categories, tips, signals, updatedAt } = storeAnalysis;
  const relative = formatRelative(updatedAt);

  const storeKeys = Array.from(STORE_WIDE_DIMENSIONS).filter(
    (k) => categories[k as keyof typeof categories] !== undefined,
  );

  if (storeKeys.length === 0) return null;

  return (
    <section
      className="rounded-2xl border p-4 mb-4"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border)",
        boxShadow: "var(--shadow-subtle)",
      }}
    >
      {/* ── Header ── */}
      <div className="flex items-center gap-3 mb-3">
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
          style={{ background: "var(--brand)", color: "var(--on-primary)" }}
        >
          <StorefrontIcon size={20} weight="fill" />
        </div>
        <div className="flex-1 min-w-0">
          <h3
            className="text-sm font-bold leading-tight font-display"
            style={{
              color: "var(--on-surface)",
            }}
          >
            Store Health
          </h3>
          <p className="text-[11px] mt-0.5 flex items-center gap-1.5 flex-wrap" style={{ color: "var(--on-surface-variant)" }}>
            <span>Store-wide scores · applies to all products</span>
            {relative && (
              <>
                <span aria-hidden="true">·</span>
                <span>Last scanned {relative}</span>
              </>
            )}
            {onRefresh && (
              <button
                type="button"
                onClick={() => { if (!refreshing) onRefresh(); }}
                disabled={refreshing}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-[var(--brand)] hover:underline disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Re-run store-wide scan"
              >
                <ArrowsClockwiseIcon
                  size={11}
                  weight="bold"
                  className={refreshing ? "animate-spin" : ""}
                />
                {refreshing ? "Refreshing…" : "Refresh"}
              </button>
            )}
          </p>
        </div>
        <div
          className="rounded-xl px-2.5 py-1 text-sm font-extrabold tabular-nums font-display"
          style={{
            background: scoreColorTintBg(score),
            color: scoreColorText(score),
          }}
        >
          {score}
        </div>
      </div>

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

      {/* ── Tips ── */}
      {tips && tips.length > 0 && (
        <div className="mt-3 pt-3 border-t" style={{ borderColor: "var(--border)" }}>
          <p
            className="text-[10px] font-semibold uppercase tracking-wide mb-1.5"
            style={{ color: "var(--on-surface-variant)" }}
          >
            Store-wide tips
          </p>
          <ul className="space-y-1">
            {tips.slice(0, 5).map((tip, i) => (
              <li
                key={i}
                className="text-[11px] leading-snug pl-3 relative break-words"
                style={{ color: "var(--on-surface-variant)" }}
              >
                <span
                  className="absolute left-0 top-[5px] w-1 h-1 rounded-full"
                  style={{ background: "var(--brand)" }}
                />
                {tip}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
