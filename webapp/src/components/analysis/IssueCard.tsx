"use client";

import { useState } from "react";
import {
  CaretRightIcon,
  CaretDownIcon,
  CheckCircleIcon,
  XCircleIcon,
  StarIcon,
  CameraIcon,
  VideoCameraIcon,
  FunnelIcon,
  ArrowFatUpIcon,
} from "@phosphor-icons/react";
import { CATEGORY_SVG, type LeakCard, type SocialProofSignals } from "@/lib/analysis";

interface IssueCardProps {
  leak: LeakCard;
  index: number;
  onClick: () => void;
  variant?: "compact" | "full";
  /** When true, card expands inline with full details instead of triggering onClick */
  expandable?: boolean;
  /** Social proof signals for detailed breakdown */
  signals?: SocialProofSignals;
}

/* ── Signal checklist item ── */
function SignalRow({ label, icon, present, detail }: { label: string; icon: React.ReactNode; present: boolean; detail?: string }) {
  return (
    <div className="flex items-start gap-2.5 py-1.5">
      <div className="shrink-0 mt-0.5">
        {present
          ? <CheckCircleIcon size={16} weight="fill" color="var(--success)" />
          : <XCircleIcon size={16} weight="fill" color="var(--error)" />
        }
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-[var(--on-surface-variant)] opacity-60">{icon}</span>
          <span className={`text-sm font-medium ${present ? "text-[var(--on-surface)]" : "text-[var(--on-surface-variant)]"}`}>
            {label}
          </span>
        </div>
        {detail && (
          <p className="text-xs text-[var(--on-surface-variant)] mt-0.5">{detail}</p>
        )}
      </div>
    </div>
  );
}

export default function IssueCard({
  leak,
  index,
  onClick,
  variant = "compact",
  expandable = false,
  signals,
}: IssueCardProps) {
  const full = variant === "full";
  const [expanded, setExpanded] = useState(false);

  const impactStyle = {
    HIGH: { textColor: "var(--error-text)" },
    MED: { textColor: "var(--warning-text)" },
    LOW: { textColor: "var(--success-text)" },
  }[leak.impact as "HIGH" | "MED" | "LOW"] || { textColor: "var(--on-surface)" };

  const handleClick = () => {
    if (expandable) {
      setExpanded((prev) => !prev);
    } else {
      onClick();
    }
  };

  return (
    <div
      className={`group text-left bg-[var(--surface)] rounded-[1.5rem] ${full ? "p-6 sm:p-7" : "p-5 sm:p-6"} flex flex-col border border-[var(--outline-variant)]/20 ${expanded ? "border-[var(--brand)]/40" : "hover:border-[var(--brand)]/40"} transition-all duration-300 ${expanded ? "" : "hover:-translate-y-1"} hover:shadow-[var(--shadow-card-hover)]`}
      style={{
        boxShadow: "var(--shadow-subtle)",
        animation: `fade-in-up 400ms ease-out ${index * 70}ms both`,
      }}
    >
      {/* ── Clickable header ── */}
      <button
        type="button"
        onClick={handleClick}
        className="cursor-pointer text-left w-full"
      >
        <div className={full ? "space-y-5" : "space-y-4"}>
          {/* Icon + Score */}
          <div className="flex justify-between items-start">
            <div className={`${full ? "w-12 h-12" : "w-11 h-11"} bg-[var(--surface-container-high)] rounded-2xl flex items-center justify-center text-[var(--on-surface-variant)] group-hover:text-[var(--brand)] group-hover:scale-110 transition-all duration-300`}>
              {CATEGORY_SVG[leak.key] || CATEGORY_SVG.title}
            </div>
            <div className="text-right">
              <div className="text-[9px] font-bold text-[var(--on-surface-variant)] tracking-[0.15em] uppercase">Score</div>
              <div
                className="text-xl font-extrabold"
                style={{ color: impactStyle.textColor, fontVariantNumeric: "tabular-nums" }}
              >
                {leak.catScore}<span className="text-xs font-semibold opacity-50">/100</span>
              </div>
            </div>
          </div>

          {/* Category + Problem */}
          <div className="space-y-2">
            <h3 className={`${full ? "text-lg sm:text-xl" : "text-base sm:text-lg"} font-bold text-[var(--on-surface)] tracking-tight leading-snug`}>
              {leak.category}
            </h3>
            <p className="text-sm text-[var(--on-surface-variant)] leading-relaxed line-clamp-3">
              {leak.problem}
            </p>
          </div>
        </div>

        {/* Bottom: Revenue + Arrow/Chevron */}
        <div className={`${full ? "mt-6 pt-5" : "mt-5 pt-4"} border-t border-[var(--surface-container)] flex justify-between items-center`}>
          <div>
            <div className="text-[9px] font-bold text-[var(--on-surface-variant)] uppercase tracking-[0.15em]">Potential Gain</div>
            <div className={`${full ? "text-base sm:text-lg" : "text-base"} font-extrabold text-[var(--success)]`}>
              {leak.revenue}
            </div>
          </div>
          {expandable ? (
            <CaretDownIcon
              className={`w-5 h-5 text-[var(--on-surface-variant)] group-hover:text-[var(--brand)] transition-all duration-200 ${expanded ? "rotate-180" : ""}`}
              weight="bold"
            />
          ) : (
            <CaretRightIcon
              className="w-5 h-5 text-[var(--on-surface-variant)] group-hover:text-[var(--brand)] group-hover:translate-x-1 transition-all duration-200"
              weight="bold"
            />
          )}
        </div>
      </button>

      {/* ── Expandable details panel ── */}
      {expandable && (
        <div
          className="grid transition-[grid-template-rows] duration-300 ease-[cubic-bezier(0.165,0.84,0.44,1)]"
          style={{ gridTemplateRows: expanded ? "1fr" : "0fr" }}
        >
          <div className="overflow-hidden">
            <div className="pt-5 mt-5 border-t border-[var(--surface-container)] space-y-5">
              {/* Fix recommendation */}
              {leak.tip && (
                <div className="rounded-xl bg-[var(--success-light)] p-4">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--success-text)] mb-1.5">
                    Recommended Fix
                  </p>
                  <p className="text-sm text-[var(--on-surface)] leading-relaxed">
                    {leak.tip}
                  </p>
                </div>
              )}

              {/* Signal breakdown */}
              {signals && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--on-surface-variant)] mb-2">
                    What We Found
                  </p>
                  <div className="rounded-xl bg-[var(--surface-container-low)] p-4 space-y-0.5">
                    <SignalRow
                      label={signals.reviewApp ? `Review app: ${signals.reviewApp}` : "No review app detected"}
                      icon={<StarIcon size={14} weight="fill" />}
                      present={signals.reviewApp !== null}
                    />
                    <SignalRow
                      label={signals.starRating !== null ? `Star rating: ${signals.starRating}/5` : "No star rating found"}
                      icon={<StarIcon size={14} weight="fill" />}
                      present={signals.starRating !== null}
                      detail={signals.starRating !== null && (signals.starRating < 4.2 || signals.starRating > 4.7)
                        ? `Optimal range is 4.2–4.7 stars`
                        : undefined}
                    />
                    <SignalRow
                      label={signals.reviewCount !== null ? `${signals.reviewCount} reviews` : "No review count found"}
                      icon={<StarIcon size={14} weight="regular" />}
                      present={signals.reviewCount !== null && signals.reviewCount >= 5}
                      detail={signals.reviewCount !== null && signals.reviewCount < 5
                        ? "Products with 5+ reviews see 270% higher conversion"
                        : signals.reviewCount !== null && signals.reviewCount < 30
                          ? "Aim for 30+ reviews for maximum impact"
                          : undefined}
                    />
                    <SignalRow
                      label="Photo reviews"
                      icon={<CameraIcon size={14} weight="fill" />}
                      present={signals.hasPhotoReviews}
                      detail={!signals.hasPhotoReviews ? "Photo reviews boost conversion by 106%" : undefined}
                    />
                    <SignalRow
                      label="Video reviews"
                      icon={<VideoCameraIcon size={14} weight="fill" />}
                      present={signals.hasVideoReviews}
                    />
                    <SignalRow
                      label="Star rating above fold"
                      icon={<ArrowFatUpIcon size={14} weight="fill" />}
                      present={signals.starRatingAboveFold}
                      detail={!signals.starRatingAboveFold ? "56% of shoppers check reviews before anything else" : undefined}
                    />
                    <SignalRow
                      label="Review filtering & sorting"
                      icon={<FunnelIcon size={14} weight="fill" />}
                      present={signals.hasReviewFiltering}
                      detail={!signals.hasReviewFiltering ? "Shoppers who filter reviews are 2x more likely to convert" : undefined}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
