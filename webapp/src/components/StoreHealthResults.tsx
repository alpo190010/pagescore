"use client";

import { useMemo } from "react";
import {
  ArrowRightIcon,
  ArrowsClockwiseIcon,
  StorefrontIcon,
} from "@phosphor-icons/react";
import {
  type CategoryScores,
  type DimensionSignals,
  type StoreAnalysisData,
  buildLeaks,
  scoreColorText,
  scoreColorTintBg,
} from "@/lib/analysis";
import Button from "@/components/ui/Button";
import IssueCard from "@/components/analysis/IssueCard";

/* ══════════════════════════════════════════════════════════════
   StoreHealthResults — Deep store-wide analysis view
   Shown when the user switches to the Store Health tab on /scan/[domain].
   Renders the 7 store-wide dimensions as full IssueCards, plus refresh
   and a CTA back to the product view.
   ══════════════════════════════════════════════════════════════ */

interface StoreHealthResultsProps {
  storeAnalysis: StoreAnalysisData;
  domain: string;
  storeName: string;
  onRefresh?: () => void | Promise<void>;
  refreshing?: boolean;
  onBackToProducts: () => void;
}

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

export default function StoreHealthResults({
  storeAnalysis,
  domain,
  storeName,
  onRefresh,
  refreshing = false,
  onBackToProducts,
}: StoreHealthResultsProps) {
  /* ── Build LeakCards from store-wide categories (worst-first via buildLeaks) ── */
  const leaks = useMemo(
    () =>
      buildLeaks(
        (storeAnalysis.categories ?? {}) as CategoryScores,
        storeAnalysis.tips ?? [],
      ),
    [storeAnalysis],
  );

  const { score, signals, updatedAt } = storeAnalysis;
  const relative = formatRelative(updatedAt);

  return (
    <div className="h-full overflow-y-auto bg-[var(--bg)]">
      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-8">
        {/* ═══ Header card ═══ */}
        <section
          className="rounded-2xl border p-5 sm:p-6"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border)",
            boxShadow: "var(--shadow-subtle)",
          }}
        >
          <div className="flex items-start gap-4 flex-wrap">
            <div
              className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
              style={{ background: "var(--brand)", color: "var(--on-primary)" }}
            >
              <StorefrontIcon size={24} weight="fill" />
            </div>

            <div className="flex-1 min-w-0">
              <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-[var(--on-surface)]">
                Store Health
              </h1>
              <p className="text-sm text-[var(--on-surface-variant)] mt-1 break-words">
                <span className="capitalize font-medium text-[var(--on-surface)]">
                  {storeName || domain}
                </span>
                <span className="mx-1.5" aria-hidden="true">·</span>
                <span>{domain}</span>
                {relative && (
                  <>
                    <span className="mx-1.5" aria-hidden="true">·</span>
                    <span>Last scanned {relative}</span>
                  </>
                )}
              </p>
            </div>

            <div
              className="rounded-xl px-4 py-2 text-2xl font-extrabold font-display tabular-nums shrink-0"
              style={{
                background: scoreColorTintBg(score),
                color: scoreColorText(score),
              }}
              aria-label={`Overall store score ${score} out of 100`}
            >
              {score}
              <span className="text-sm font-semibold opacity-60">/100</span>
            </div>

            {onRefresh && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => { if (!refreshing) onRefresh(); }}
                disabled={refreshing}
                aria-label="Re-run store-wide scan"
              >
                <ArrowsClockwiseIcon
                  size={14}
                  weight="bold"
                  className={refreshing ? "animate-spin" : ""}
                />
                {refreshing ? "Refreshing…" : "Refresh scan"}
              </Button>
            )}
          </div>

          <p className="text-sm text-[var(--on-surface-variant)] mt-4 leading-relaxed">
            Storefront-level dimensions — scored once per store, shared across every product.
            These reflect your entire shopping experience: checkout, shipping, trust, page speed,
            AI discoverability, accessibility, and social commerce.
          </p>
        </section>

        {/* ═══ IssueCard grid ═══ */}
        <section>
          <div className="border-l-[3px] border-[var(--brand)] pl-5 mb-5 sm:mb-6">
            <h2 className="text-xl sm:text-2xl font-extrabold text-[var(--on-surface)] tracking-tight font-display">
              Dimensions
            </h2>
            <p className="text-[var(--on-surface-variant)] text-sm mt-1">
              {leaks.length} store-wide dimension{leaks.length !== 1 ? "s" : ""} analyzed.
              Click any to see the signals and recommended fixes.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {leaks.map((leak, i) => (
              <IssueCard
                key={leak.key}
                leak={leak}
                index={i}
                onClick={() => {}}
                expandable={true}
                locked={false}
                signals={signals as DimensionSignals | undefined}
              />
            ))}
          </div>
        </section>

        {/* ═══ CTA — back to products ═══ */}
        <div className="flex justify-center pt-2 pb-6">
          <Button
            type="button"
            variant="gradient"
            size="md"
            shape="pill"
            onClick={onBackToProducts}
          >
            Check individual products
            <ArrowRightIcon size={16} weight="bold" />
          </Button>
        </div>
      </div>
    </div>
  );
}
