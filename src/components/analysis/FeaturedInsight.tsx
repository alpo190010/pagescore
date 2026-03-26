"use client";

import { StarIcon, ArrowRightIcon } from "@phosphor-icons/react";
import { scoreColor, scoreColorText, type LeakCard } from "@/lib/analysis";

interface FeaturedInsightProps {
  leaks: LeakCard[];
  summary: string;
  onInsightClick: () => void;
  variant?: "compact" | "full";
}

export default function FeaturedInsight({
  leaks,
  summary,
  onInsightClick,
  variant = "compact",
}: FeaturedInsightProps) {
  const full = variant === "full";

  return (
    <div className={`bg-[var(--surface-container-low)] rounded-3xl ${full ? "p-8 sm:p-12" : "p-6 sm:p-10"} relative overflow-hidden`}>
      <div className={`grid md:grid-cols-2 ${full ? "gap-10" : "gap-8"} items-center relative z-10`}>
        {/* Left — badge, heading, body, link */}
        <div className={full ? "space-y-5" : "space-y-4"}>
          <div className={`inline-flex items-center gap-2 ${full ? "px-4" : "px-3"} py-1.5 rounded-full text-sm font-bold bg-[var(--brand-light)] text-[var(--brand)] border border-[var(--brand-border)]`}>
            <StarIcon size={14} weight="fill" color="var(--brand)" />
            Top Insight
          </div>
          <h2
            className={`${full ? "text-2xl sm:text-3xl" : "text-xl sm:text-2xl"} font-extrabold text-[var(--on-surface)] tracking-tight leading-tight`}
            style={{ fontFamily: "var(--font-manrope), Manrope, sans-serif" }}
          >
            {leaks[0]
              ? `Your "${leaks[0].category}" score of ${leaks[0].catScore} is the #1 revenue blocker.`
              : "Critical improvements identified."}
          </h2>
          <p className={`text-[var(--on-surface-variant)] ${full ? "text-base" : "text-sm"} leading-relaxed max-w-lg`}>
            {leaks[0]?.tip || summary}
          </p>
          <button
            type="button"
            onClick={onInsightClick}
            className={`cursor-pointer group inline-flex items-center gap-2 text-[var(--brand)] font-bold ${full ? "text-base" : "text-sm"}`}
          >
            Get the detailed fix
            <ArrowRightIcon className="w-5 h-5 group-hover:translate-x-1 transition-transform" weight="bold" />
          </button>
        </div>

        {/* Right — score breakdown bars */}
        <div className="space-y-3">
          {leaks.slice(0, 5).map((leak) => (
            <div key={leak.key} className="flex items-center gap-3">
              <span className={`text-sm font-semibold text-[var(--on-surface-variant)] ${full ? "w-24" : "w-20"} shrink-0 truncate`}>
                {leak.category}
              </span>
              <div className="flex-1 h-3 bg-[var(--surface-container)] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${leak.catScore}%`,
                    backgroundColor: scoreColor(leak.catScore),
                  }}
                />
              </div>
              <span
                className="text-sm font-bold w-8 text-right"
                style={{ color: scoreColorText(leak.catScore), fontVariantNumeric: "tabular-nums" }}
              >
                {leak.catScore}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
