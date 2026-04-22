"use client";

import { ArrowRightIcon } from "@phosphor-icons/react";
import {
  type StoreAnalysisData,
  CATEGORY_LABELS,
  CATEGORY_PROBLEMS,
  CATEGORY_REVENUE_IMPACT,
  CATEGORY_SVG,
  DIMENSION_IMPACT_WEIGHTS,
  calculateConversionLoss,
  domainToBrand,
  scoreColorText,
  scoreColorTintBg,
} from "@/lib/analysis";

/* ══════════════════════════════════════════════════════════════
   StoreHealthDetail — Right-pane detail view for one store-wide
   dimension. Renders when the user lands on the scan page with
   the Store Health tab active and no product selected: the default
   is the worst-scoring dimension, sourced from storeAnalysis.
   ══════════════════════════════════════════════════════════════ */

interface StoreHealthDetailProps {
  dimensionKey: string;
  storeAnalysis: StoreAnalysisData;
  storeName: string;
}

export default function StoreHealthDetail({
  dimensionKey,
  storeAnalysis,
  storeName,
}: StoreHealthDetailProps) {
  const score =
    (storeAnalysis.categories as Record<string, number>)[dimensionKey] ?? 0;
  const label = CATEGORY_LABELS[dimensionKey] ?? dimensionKey;
  const icon = CATEGORY_SVG[dimensionKey];
  const impact = CATEGORY_REVENUE_IMPACT[dimensionKey] ?? "";
  const weight = DIMENSION_IMPACT_WEIGHTS[dimensionKey] ?? 0;
  const problem =
    score < 40
      ? CATEGORY_PROBLEMS[dimensionKey]?.low
      : CATEGORY_PROBLEMS[dimensionKey]?.mid;
  const conversionLoss = calculateConversionLoss(score, dimensionKey);

  return (
    <div
      className="h-full w-full px-6 sm:px-10 py-8 sm:py-12"
      style={{
        animation: "fade-in-up 400ms var(--ease-out-quart) both",
      }}
    >
      <div className="max-w-2xl mx-auto flex flex-col gap-8">
        {/* ── Breadcrumb ── */}
        <div
          className="font-mono text-[10px] uppercase tracking-[0.14em]"
          style={{ color: "var(--ink-3)" }}
        >
          {domainToBrand(storeName)} · Store Health · {label}
        </div>

        {/* ── Header: icon + label + score ── */}
        <header className="flex items-start gap-5">
          <span
            className="w-14 h-14 rounded-[14px] flex items-center justify-center shrink-0"
            style={{
              background: scoreColorTintBg(score),
              color: scoreColorText(score),
            }}
            aria-hidden="true"
          >
            <span className="scale-[1.6] flex">{icon}</span>
          </span>
          <div className="flex-1 min-w-0">
            <h1
              className="font-display font-extrabold text-3xl sm:text-4xl leading-[1.05]"
              style={{ color: "var(--ink)", letterSpacing: "-0.02em" }}
            >
              {label}
            </h1>
            {impact && (
              <p
                className="mt-1.5 text-[13px] font-medium"
                style={{ color: "var(--ink-3)" }}
              >
                {impact} revenue impact
              </p>
            )}
          </div>
          <div
            className="flex flex-col items-end shrink-0"
            style={{ color: scoreColorText(score) }}
          >
            <span
              className="font-display font-extrabold text-5xl sm:text-6xl leading-none tabular-nums"
              style={{ letterSpacing: "-0.03em" }}
            >
              {score}
            </span>
            <span
              className="text-[11px] font-medium mt-1"
              style={{ color: "var(--ink-3)" }}
            >
              /100
            </span>
          </div>
        </header>

        {/* ── Issue ── */}
        {problem && (
          <section
            className="rounded-2xl border px-6 py-5"
            style={{
              background: "var(--paper)",
              borderColor: "var(--rule-2)",
              boxShadow: "var(--shadow-subtle)",
            }}
          >
            <h2
              className="font-mono text-[10px] uppercase tracking-[0.14em] mb-2"
              style={{ color: "var(--ink-3)" }}
            >
              The issue
            </h2>
            <p
              className="text-[15px] leading-[1.55]"
              style={{ color: "var(--ink)" }}
            >
              {problem}
            </p>
          </section>
        )}

        {/* ── Metrics row ── */}
        <section className="grid grid-cols-2 gap-3">
          <div
            className="rounded-2xl border px-5 py-4"
            style={{
              background: "var(--paper)",
              borderColor: "var(--rule-2)",
              boxShadow: "var(--shadow-subtle)",
            }}
          >
            <div
              className="font-mono text-[10px] uppercase tracking-[0.14em] mb-2"
              style={{ color: "var(--ink-3)" }}
            >
              Est. conversion loss
            </div>
            <div
              className="font-display font-extrabold text-3xl leading-none tabular-nums"
              style={{ color: "var(--accent)", letterSpacing: "-0.02em" }}
            >
              {conversionLoss}
              <span
                className="text-lg ml-0.5"
                style={{ color: "var(--ink-3)" }}
              >
                %
              </span>
            </div>
          </div>
          <div
            className="rounded-2xl border px-5 py-4"
            style={{
              background: "var(--paper)",
              borderColor: "var(--rule-2)",
              boxShadow: "var(--shadow-subtle)",
            }}
          >
            <div
              className="font-mono text-[10px] uppercase tracking-[0.14em] mb-2"
              style={{ color: "var(--ink-3)" }}
            >
              Impact weight
            </div>
            <div
              className="font-display font-extrabold text-3xl leading-none tabular-nums"
              style={{ color: "var(--ink)", letterSpacing: "-0.02em" }}
            >
              {weight.toFixed(2)}
            </div>
          </div>
        </section>

        {/* ── Store-level tips ── */}
        {storeAnalysis.tips && storeAnalysis.tips.length > 0 && (
          <section>
            <h2
              className="font-mono text-[10px] uppercase tracking-[0.14em] mb-3"
              style={{ color: "var(--ink-3)" }}
            >
              Where to start
            </h2>
            <ul className="flex flex-col gap-2.5">
              {storeAnalysis.tips.slice(0, 5).map((tip, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3 rounded-xl border px-4 py-3"
                  style={{
                    background: "var(--paper)",
                    borderColor: "var(--rule-2)",
                  }}
                >
                  <span
                    className="font-mono text-[11px] font-semibold shrink-0 mt-0.5 tabular-nums"
                    style={{ color: "var(--accent)" }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <p
                    className="text-[13.5px] leading-[1.5] flex-1"
                    style={{ color: "var(--ink-2)" }}
                  >
                    {tip}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* ── Hint footer ── */}
        <div
          className="flex items-center gap-2 text-[12px] pt-2"
          style={{ color: "var(--ink-3)" }}
        >
          <ArrowRightIcon size={12} weight="bold" />
          <span>
            Pick a product on the left to see its own conversion score.
          </span>
        </div>
      </div>
    </div>
  );
}
