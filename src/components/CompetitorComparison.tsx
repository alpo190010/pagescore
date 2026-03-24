"use client";

/* ── Types (local copy — component stays self-contained) ── */
interface CategoryScores {
  title: number;
  images: number;
  pricing: number;
  socialProof: number;
  cta: number;
  description: number;
  trust: number;
}

interface CompetitorComparisonProps {
  competitors: Array<{
    name: string;
    url: string;
    score: number;
    summary: string;
    categories: CategoryScores;
  }>;
  userCategories: CategoryScores;
  userScore: number;
  onBeatCompetitor?: (name: string) => void;
}

/* ── Constants ── */
const CATEGORY_LABELS: Record<string, string> = {
  title: "Title",
  images: "Images",
  pricing: "Pricing",
  socialProof: "Social Proof",
  cta: "CTA",
  description: "Description",
  trust: "Trust",
};

const CATEGORY_KEYS = Object.keys(CATEGORY_LABELS) as (keyof CategoryScores)[];

/* ── Score color helpers (0-10 category scale) ── */
function cellColor(val: number, isBest: boolean, isWorst: boolean): string {
  if (isBest) return "var(--success-text)";
  if (isWorst) return "var(--error-text)";
  return "var(--text-primary)";
}

function cellBg(isBest: boolean, isWorst: boolean): string {
  if (isBest) return "var(--success-light)";
  if (isWorst) return "var(--error-light)";
  return "transparent";
}

function overallScoreColor(score: number): string {
  if (score >= 70) return "var(--success)";
  if (score >= 40) return "var(--warning)";
  return "var(--error)";
}

/* ══════════════════════════════════════════════════════════ */

export default function CompetitorComparison({
  competitors,
  userCategories,
  userScore,
  onBeatCompetitor,
}: CompetitorComparisonProps) {
  /* ── Empty state ── */
  if (competitors.length === 0) {
    return (
      <section
        className="text-center mt-8 mb-4"
        style={{ animation: "fade-in-up 400ms ease-out both" }}
        aria-label="No competitors found"
      >
        <div
          className="max-w-md mx-auto w-full p-8 rounded-2xl bg-[var(--surface)] border border-[var(--border)]"
          style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}
        >
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl flex items-center justify-center bg-[var(--surface-dim)] border border-[var(--border)]">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M21 21l-4.35-4.35M11 6v5m0 0v5m0-5h5m-5 0H6" stroke="var(--text-tertiary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              <circle cx="11" cy="11" r="8" stroke="var(--text-tertiary)" strokeWidth="1.5"/>
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-2 text-[var(--text-primary)]">
            No comparable pages found
          </h3>
          <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
            We found competitor products but their pages weren&apos;t accessible
            for analysis. This can happen when competitor URLs have changed or are geo-restricted.
          </p>
        </div>
      </section>
    );
  }

  /* ── Build column data: You + competitors ── */
  const columns = [
    { name: "You", score: userScore, categories: userCategories, isUser: true },
    ...competitors.map((c) => ({
      name: c.name,
      score: c.score,
      categories: c.categories,
      isUser: false,
    })),
  ];

  /* ── Count wins for "You" column ── */
  const userWins = CATEGORY_KEYS.filter((key) => {
    const userVal = userCategories[key] ?? 0;
    return competitors.every((c) => userVal > (c.categories[key] ?? 0));
  }).length;
  const userLosses = CATEGORY_KEYS.filter((key) => {
    const userVal = userCategories[key] ?? 0;
    return competitors.some((c) => (c.categories[key] ?? 0) > userVal);
  }).length;

  /* ── Top competitor for CTA ── */
  const topCompetitor = competitors.reduce((best, c) =>
    c.score > best.score ? c : best
  );

  return (
    <section className="mt-8 mb-4 anim-phase-enter" aria-label="Competitor comparison">
      {/* Section heading */}
      <div className="flex items-center justify-between gap-3 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-[var(--brand-light)] border border-[var(--brand-border)]">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <rect x="3" y="12" width="4" height="9" rx="1" fill="var(--brand)" opacity="0.4"/>
              <rect x="10" y="4" width="4" height="17" rx="1" fill="var(--brand)"/>
              <rect x="17" y="8" width="4" height="13" rx="1" fill="var(--brand)" opacity="0.6"/>
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-bold text-[var(--text-primary)]">
              Competitive Breakdown
            </h2>
            <p className="text-sm text-[var(--text-secondary)]">
              {userWins > userLosses
                ? `You lead in ${userWins} of 7 categories`
                : userWins === userLosses
                  ? "You're neck and neck with competitors"
                  : `Competitors lead in ${userLosses} of 7 categories`}
            </p>
          </div>
        </div>
      </div>

      {/* ── Unified comparison table ── */}
      <div
        className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl overflow-hidden"
        style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}
      >
        {/* Scrollable wrapper for mobile */}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px]" role="table">
            {/* ── Column headers: overall scores ── */}
            <thead>
              <tr className="border-b-2 border-[var(--border)]">
                {/* Category label column */}
                <th className="text-left px-4 sm:px-6 py-4 text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)] w-[140px] sm:w-[160px]">
                  Category
                </th>
                {/* One column per player */}
                {columns.map((col) => (
                  <th key={col.name} className="px-3 sm:px-4 py-4 text-center">
                    <div className="flex flex-col items-center gap-1.5">
                      {/* Overall score badge */}
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold border-2"
                        style={{
                          color: overallScoreColor(col.score),
                          borderColor: overallScoreColor(col.score),
                          backgroundColor: col.isUser
                            ? `color-mix(in srgb, ${overallScoreColor(col.score)} 8%, transparent)`
                            : "var(--surface-dim)",
                        }}
                      >
                        {col.score}
                      </div>
                      {/* Name */}
                      <span
                        className={`text-xs truncate max-w-[80px] sm:max-w-[100px] ${
                          col.isUser
                            ? "font-bold text-[var(--brand)]"
                            : "font-medium text-[var(--text-secondary)]"
                        }`}
                      >
                        {col.name}
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>

            {/* ── Category rows ── */}
            <tbody>
              {CATEGORY_KEYS.map((key, rowIdx) => {
                /* Find best and worst score for this category */
                const scores = columns.map((c) => c.categories[key] ?? 0);
                const maxVal = Math.max(...scores);
                const minVal = Math.min(...scores);
                const allSame = maxVal === minVal;

                return (
                  <tr
                    key={key}
                    className={rowIdx < CATEGORY_KEYS.length - 1 ? "border-b border-[var(--track)]" : ""}
                    style={{ animation: `fade-in-up 300ms ease-out ${rowIdx * 50}ms both` }}
                  >
                    {/* Category label */}
                    <td className="px-4 sm:px-6 py-3.5 text-sm font-medium text-[var(--text-primary)]">
                      {CATEGORY_LABELS[key]}
                    </td>

                    {/* Score cells */}
                    {columns.map((col) => {
                      const val = col.categories[key] ?? 0;
                      const isBest = !allSame && val === maxVal;
                      const isWorst = !allSame && val === minVal;

                      return (
                        <td key={col.name} className="px-3 sm:px-4 py-3.5 text-center">
                          <span
                            className="inline-flex items-center justify-center w-10 h-7 rounded-lg text-sm font-bold font-[family-name:var(--font-mono)]"
                            style={{
                              fontVariantNumeric: "tabular-nums",
                              color: cellColor(val, isBest, isWorst),
                              backgroundColor: cellBg(isBest, isWorst),
                            }}
                          >
                            {val}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* ── Legend ── */}
        <div className="px-4 sm:px-6 py-3 border-t border-[var(--track)] bg-[var(--surface-dim)] flex items-center gap-4 text-[11px] text-[var(--text-tertiary)]">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: "var(--success-light)", border: "1px solid var(--success-border)" }}></span>
            Best in category
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: "var(--error-light)", border: "1px solid #fca5a5" }}></span>
            Weakest in category
          </span>
          <span className="ml-auto text-[var(--text-tertiary)]">Scores out of 10</span>
        </div>
      </div>

      {/* ── AI Summaries (collapsed under the table) ── */}
      {competitors.some((c) => c.summary && !/404|error|cannot be assessed|not found/i.test(c.summary)) && (
        <div className="mt-4 flex flex-col gap-3">
          {competitors.map((comp, i) => (
            comp.summary && !/404|error|cannot be assessed|not found/i.test(comp.summary) ? (
              <div
                key={comp.url}
                className="px-5 py-4 rounded-xl bg-[var(--surface-dim)] border border-[var(--border)]"
                style={{ animation: `fade-in-up 300ms ease-out ${200 + i * 100}ms both` }}
              >
                <p className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wider mb-1.5">
                  vs {comp.name}
                </p>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  {comp.summary}
                </p>
              </div>
            ) : null
          ))}
        </div>
      )}

      {/* ── Beat-competitor CTA ── */}
      {onBeatCompetitor && (
        <div className="mt-8 text-center" style={{ animation: "fade-in-up 400ms ease-out 400ms both" }}>
          <button
            type="button"
            onClick={() => onBeatCompetitor(topCompetitor.name)}
            className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl text-base font-semibold text-white polish-hover-lift polish-focus-ring bg-gradient-to-r from-[var(--brand)] to-blue-700"
            style={{
              boxShadow: "0 8px 32px color-mix(in srgb, var(--brand) 20%, transparent)",
            }}
          >
            Get a Plan to Beat {topCompetitor.name} →
          </button>
        </div>
      )}
    </section>
  );
}
