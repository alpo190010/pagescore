"use client";

import { useState, useEffect, useRef, useMemo, memo } from "react";
import { useSession } from "next-auth/react";
import {
  ArrowsClockwiseIcon,
  CursorClickIcon,
  LightningIcon,
  MagnifyingGlassIcon,
  PackageIcon,
  ShieldCheckIcon,
  type Icon as PhosphorIcon,
} from "@phosphor-icons/react";
import {
  type FreeResult,
  type LeakCard,
  useCountUp,
  captureEvent,
  scoreColor,
  calculateDollarLossPerThousand,
  splitLeaksByScope,
} from "@/lib/analysis";
import {
  buildProductGroups,
  type ProductGroupView,
} from "@/lib/analysis/productChecks";
import { API_URL } from "@/lib/api";
import { authFetch } from "@/lib/auth-fetch";
import Button from "@/components/ui/Button";
import ScoreRing from "@/components/analysis/ScoreRing";
import PluginCTACard from "@/components/analysis/PluginCTACard";
import CTACard from "@/components/analysis/CTACard";
import ChecksGroup from "@/components/checks/ChecksGroup";
import { severityFor, type Severity } from "@/components/checks/severity";

/* ══════════════════════════════════════════════════════════════
   AnalysisResults — per-product page health.

   Layout (top-to-bottom):
     1. Score ring + revenue summary
     2. "Score breakdown" grid — one card per thematic dimension
        group (DIMENSION_GROUPS), sorted worst→best, first selected
        by default. Click to switch the active group.
     3. "What's working" + "Issues found" lists for the active
        group. Severity chips (All / Critical / Major / Minor)
        filter the issues list. Visuals reuse the storewide
        ChecksGroup / CheckRow primitive.
     4. Analyze again CTA
   ══════════════════════════════════════════════════════════════ */

type SeverityFilter = "all" | Severity;

/* Per-thematic-group icons. Keyed by `DIMENSION_GROUPS[].id`. The
   icon sits inside the donut ring on each ScoreCard — the ring
   reads the score visually, the icon reads the category. */
const GROUP_ICONS: Record<string, PhosphorIcon> = {
  buying: PackageIcon,
  trust: ShieldCheckIcon,
  conversion: CursorClickIcon,
  discovery: MagnifyingGlassIcon,
  technical: LightningIcon,
};

interface AnalysisResultsProps {
  result: FreeResult;
  leaks: LeakCard[];
  domain: string;
  url: string;
  productName?: string;
  productUrl?: string;
  productImage?: string;
  onIssueClick: (key: string) => void;
  onAnalyzeAgain: () => void;
}

const AnalysisResults = memo(function AnalysisResults({
  result,
  leaks,
  domain,
  url,
  productName,
  productUrl,
  productImage,
  onIssueClick,
  onAnalyzeAgain,
}: AnalysisResultsProps) {
  const { status } = useSession();

  /* ── Plan-based gating ── */
  const [userPlan, setUserPlan] = useState<string>("free");
  useEffect(() => {
    if (status !== "authenticated") return;
    const controller = new AbortController();
    authFetch(`${API_URL}/user/plan`, { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (data?.plan) setUserPlan(data.plan); })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        console.warn("Failed to fetch user plan:", err);
      });
    return () => controller.abort();
  }, [status]);
  const isPaid = status === "authenticated" && userPlan !== "free";

  /* ── Staggered reveal ── */
  const [showCard, setShowCard] = useState(false);
  const [showRevenue, setShowRevenue] = useState(false);
  const [showLeaks, setShowLeaks] = useState(false);
  const issuesRef = useRef<HTMLDivElement>(null);

  /* ── Product-only leaks ── */
  const { productLeaks } = useMemo(() => splitLeaksByScope(leaks), [leaks]);

  /* ── Thematic group view (drives the Score breakdown grid) ── */
  const groups = useMemo(
    () => buildProductGroups(result, productLeaks),
    [result, productLeaks],
  );

  const totalMissing = useMemo(
    () =>
      groups.reduce(
        (sum, g) => sum + g.checks.filter((c) => !c.passed).length,
        0,
      ),
    [groups],
  );
  const everythingPassing = groups.length > 0 && totalMissing === 0;

  /* ── Active group selection ── */
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);
  useEffect(() => {
    if (groups.length > 0 && (!activeGroupId || !groups.some((g) => g.id === activeGroupId))) {
      setActiveGroupId(groups[0].id);
    }
  }, [groups, activeGroupId]);
  const activeGroup =
    groups.find((g) => g.id === activeGroupId) ?? groups[0] ?? null;

  /* ── Severity chip filter (resets when active group changes) ── */
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  useEffect(() => {
    setSeverityFilter("all");
  }, [activeGroupId]);

  /* ── Active group's working / missing partitions ── */
  const activeWorking = useMemo(
    () => (activeGroup ? activeGroup.checks.filter((c) => c.passed) : []),
    [activeGroup],
  );
  const activeMissing = useMemo(
    () => (activeGroup ? activeGroup.checks.filter((c) => !c.passed) : []),
    [activeGroup],
  );
  const severityCounts = useMemo(() => {
    const counts = { all: activeMissing.length, critical: 0, major: 0, minor: 0 };
    for (const c of activeMissing) counts[severityFor(c.weight)] += 1;
    return counts;
  }, [activeMissing]);
  const filteredMissing = useMemo(() => {
    if (severityFilter === "all") return activeMissing;
    return activeMissing.filter((c) => severityFor(c.weight) === severityFilter);
  }, [activeMissing, severityFilter]);

  /* ── Dollar loss for PluginCTACard ── */
  const dollarLoss = useMemo(
    () => calculateDollarLossPerThousand(result.categories, result.productPrice, result.productCategory),
    [result.categories, result.productPrice, result.productCategory],
  );

  useEffect(() => {
    setShowCard(true);
    const t1 = setTimeout(() => setShowRevenue(true), 1500);
    const t2 = setTimeout(() => setShowLeaks(true), 1800);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  const animatedScore = useCountUp(showCard ? result.score : 0);

  return (
    <div className="space-y-8">
      {/* ═══ SCORE RING + REVENUE SUMMARY ═══ */}
      {showCard && (
        <section style={{ animation: "fade-in-up 600ms var(--ease-out-quart) both" }}>
          <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-stretch">
            <ScoreRing
              score={result.score}
              animatedScore={animatedScore}
              domain={domain || url}
              productName={productName}
              productUrl={productUrl}
              productImage={productImage}
              summary={result.summary}
              categories={result.categories}
              leaksCount={leaks.length}
            />

            {showRevenue && (
              <PluginCTACard
                dollarLoss={dollarLoss}
                onViewBreakdown={() => issuesRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
              />
            )}
          </div>
        </section>
      )}

      {/* ═══ SCORE BREAKDOWN + ACTIVE GROUP DETAIL ═══ */}
      {showLeaks && groups.length > 0 && (
        <div
          ref={issuesRef}
          style={{ animation: "fade-in-up 600ms var(--ease-out-quart) both" }}
        >
          {/* Score breakdown grid */}
          <div className="mb-8">
            <h2 className="font-display font-extrabold text-xl sm:text-2xl tracking-tight text-[var(--ink)] mb-4">
              Score breakdown
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {groups.map((g) => (
                <ScoreCard
                  key={g.id}
                  group={g}
                  selected={g.id === activeGroupId}
                  onSelect={() => setActiveGroupId(g.id)}
                />
              ))}
            </div>
          </div>

          {/* Active group detail */}
          {activeGroup && (
            <div className="space-y-5">
              {/* Issues found header + severity chips */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h3 className="font-display font-extrabold text-lg sm:text-xl tracking-tight text-[var(--ink)]">
                    Issues found{" "}
                    <span
                      className="font-mono text-base font-bold tabular-nums"
                      style={{ color: "var(--ink-3)" }}
                    >
                      ({severityCounts.all})
                    </span>
                  </h3>
                  <p className="text-[12.5px] mt-0.5" style={{ color: "var(--ink-3)" }}>
                    {activeGroup.label} · {activeGroup.question}
                  </p>
                </div>
                <SeverityChips
                  counts={severityCounts}
                  active={severityFilter}
                  onChange={setSeverityFilter}
                />
              </div>

              {/* What's working — for the active group */}
              {activeWorking.length > 0 && (
                <ChecksGroup
                  heading="What's working"
                  count={activeWorking.length}
                  tone="pass"
                  items={activeWorking}
                />
              )}

              {/* Missing list — filtered by chip */}
              {filteredMissing.length > 0 ? (
                <ChecksGroup
                  heading={
                    severityFilter === "all"
                      ? "What's missing"
                      : `What's missing — ${capitalize(severityFilter)}`
                  }
                  count={filteredMissing.length}
                  tone="fail"
                  items={filteredMissing}
                />
              ) : severityCounts.all === 0 ? (
                <AllClearBanner label={activeGroup.label} />
              ) : (
                <EmptyFilter />
              )}

              {!isPaid && severityCounts.all > 0 && (
                <CTACard
                  leaksCount={leaks.length}
                  animationDelay={100}
                  onClick={() => {
                    onIssueClick(leaks[0]?.key || "");
                    captureEvent("cta_card_clicked", { url });
                  }}
                />
              )}
            </div>
          )}

          {/* Whole-product celebration when nothing is missing anywhere */}
          {everythingPassing && (
            <div className="mt-6">
              <AllClearBanner
                label="this product"
                body="Every signal we check is in good shape. Re-scan after your next change to keep it that way."
                strong
              />
            </div>
          )}
        </div>
      )}

      {/* ═══ ANALYZE AGAIN ═══ */}
      {showLeaks && (
        <section style={{ animation: "fade-in-up 600ms var(--ease-out-quart) 400ms both" }}>
          <div className="text-center mt-8">
            <Button
              type="button"
              variant="gradient"
              size="md"
              shape="card"
              onClick={onAnalyzeAgain}
              className="px-7 py-3.5 font-semibold polish-hover-lift"
            >
              <ArrowsClockwiseIcon size={16} weight="bold" />
              Analyze Again
            </Button>
          </div>
        </section>
      )}
    </div>
  );
});

export default AnalysisResults;

/* ══════════════════════════════════════════════════════════════
   ScoreCard — one tile in the Score breakdown grid. Mirrors the
   editorial paper aesthetic: cream surface, 1px rule, small
   donut-style score ring + display-font label + coral score.
   Selected state: ink border + raised shadow.
   ══════════════════════════════════════════════════════════════ */
function ScoreCard({
  group,
  selected,
  onSelect,
}: {
  group: ProductGroupView;
  selected: boolean;
  onSelect: () => void;
}) {
  const Icon = GROUP_ICONS[group.id] ?? PackageIcon;
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className="text-left rounded-[14px] border px-4 py-3 sm:py-3.5 flex items-center gap-3.5 transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ink)]/30"
      style={{
        background: selected ? "var(--bg-elev)" : "var(--paper)",
        borderColor: selected ? "var(--ink)" : "var(--rule-2)",
        boxShadow: selected
          ? "0 0 0 1px var(--ink), var(--shadow-subtle)"
          : "var(--shadow-subtle)",
      }}
    >
      <ScoreDonut score={group.avgScore}>
        <Icon size={16} weight="fill" aria-hidden />
      </ScoreDonut>
      <div className="flex-1 min-w-0">
        <div
          className="font-display font-bold text-[15px] leading-tight truncate"
          style={{ color: "var(--ink)" }}
        >
          {group.label}
        </div>
        <div
          className="font-mono text-[13px] mt-0.5 tabular-nums"
          style={{ color: scoreColor(group.avgScore) }}
        >
          {group.avgScore}/100
        </div>
      </div>
    </button>
  );
}

/* ── Donut score ring with optional centered icon (used inside ScoreCard) ── */
function ScoreDonut({
  score,
  children,
}: {
  score: number;
  children?: React.ReactNode;
}) {
  const size = 44;
  const stroke = 3.5;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const arc = (Math.max(0, Math.min(100, score)) / 100) * c;
  const color = scoreColor(score);
  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size, color }}
    >
      <svg width={size} height={size} aria-hidden>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="var(--rule-2)"
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={color}
          strokeWidth={stroke}
          fill="none"
          strokeDasharray={`${arc} ${c}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dasharray 600ms var(--ease-out-quart)" }}
        />
      </svg>
      {children && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          {children}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   SeverityChips — pill toggle for All / Critical / Major / Minor.
   Active chip is ink-filled; others are outlined and dim.
   ══════════════════════════════════════════════════════════════ */
function SeverityChips({
  counts,
  active,
  onChange,
}: {
  counts: { all: number; critical: number; major: number; minor: number };
  active: SeverityFilter;
  onChange: (next: SeverityFilter) => void;
}) {
  const items: { value: SeverityFilter; label: string; n: number }[] = [
    { value: "all", label: "All", n: counts.all },
    { value: "critical", label: "Critical", n: counts.critical },
    { value: "major", label: "Major", n: counts.major },
    { value: "minor", label: "Minor", n: counts.minor },
  ];
  return (
    <div className="flex items-center gap-2 flex-wrap" role="tablist" aria-label="Filter issues by severity">
      {items.map((item) => {
        const isActive = active === item.value;
        const disabled = item.n === 0 && item.value !== "all";
        return (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={isActive}
            disabled={disabled}
            onClick={() => onChange(item.value)}
            className="rounded-full px-3.5 py-1.5 text-[13px] font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ink)]/30"
            style={{
              background: isActive ? "var(--ink)" : "transparent",
              color: isActive ? "var(--paper)" : "var(--ink-2)",
              border: `1px solid ${isActive ? "var(--ink)" : "var(--rule-2)"}`,
            }}
          >
            {item.label} <span className="tabular-nums opacity-80">{item.n}</span>
          </button>
        );
      })}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   AllClearBanner — shown when the active group (or whole product)
   has zero failing checks. Mirrors StoreHealthDetail's "You're
   crushing it" treatment but at product/group scope.
   ══════════════════════════════════════════════════════════════ */
function AllClearBanner({
  label,
  body,
  strong,
}: {
  label: string;
  body?: string;
  strong?: boolean;
}) {
  return (
    <section
      role="status"
      className="rounded-[14px] flex items-center gap-3.5 px-5 py-4"
      style={{
        background: "var(--success-light)",
        border: "1px solid var(--success-border)",
      }}
    >
      <span
        className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 font-display font-extrabold text-base"
        style={{ background: "var(--success-text)", color: "var(--paper)" }}
        aria-hidden
      >
        ✓
      </span>
      <div className="min-w-0">
        <h4
          className={
            strong
              ? "font-display font-extrabold text-[18px] leading-tight"
              : "font-display font-bold text-[15px] leading-tight"
          }
          style={{ color: "var(--success-text)", letterSpacing: "-0.01em" }}
        >
          {strong
            ? `${capitalize(label)} is firing on all cylinders`
            : `Nothing missing in ${label}`}
        </h4>
        {body && (
          <p className="text-[13px] mt-1" style={{ color: "var(--ink-2)" }}>
            {body}
          </p>
        )}
      </div>
    </section>
  );
}

/* ══════════════════════════════════════════════════════════════
   EmptyFilter — shown when the chosen severity chip has no items
   in the active group (e.g. user clicked "Critical" but everything
   is major/minor). Encourages switching back to All.
   ══════════════════════════════════════════════════════════════ */
function EmptyFilter() {
  return (
    <p
      className="text-[13px] italic px-1"
      style={{ color: "var(--ink-3)" }}
    >
      No issues at this severity. Pick another chip to see the rest.
    </p>
  );
}

function capitalize(s: string): string {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1);
}
