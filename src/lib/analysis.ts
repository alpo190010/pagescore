/* ═══════════════════════════════════════════════════════════════
   Shared types, utilities, and constants for PageLeaks
   ═══════════════════════════════════════════════════════════════ */

/* ── Types ── */
export interface CategoryScores {
  title: number;
  images: number;
  pricing: number;
  socialProof: number;
  cta: number;
  description: number;
  trust: number;
}

export interface CompetitorResult {
  competitors: Array<{
    name: string;
    url: string;
    score: number;
    summary: string;
    categories: CategoryScores;
  }>;
}

export interface FreeResult {
  score: number;
  summary: string;
  tips: string[];
  categories: CategoryScores;
  productPrice: number;
  productCategory: string;
  estimatedMonthlyVisitors: number;
}

export interface LeakCard {
  key: string;
  catScore: number;
  impact: "HIGH" | "MED" | "LOW";
  revenue: string;
  tip: string;
  problem: string;
  category: string;
}

/* ── Lazy PostHog — don't block initial paint ── */
export function captureEvent(event: string, properties?: Record<string, unknown>) {
  import("posthog-js").then(({ default: posthog }) => {
    try { posthog.capture(event, properties); } catch { /* not initialized */ }
  });
}

/* ── Revenue loss estimation (research-backed) ── */
const CATEGORY_BENCHMARKS: Record<string, { avg: number; achievable: number }> = {
  fashion:      { avg: 1.90, achievable: 2.80 },
  beauty:       { avg: 2.50, achievable: 3.70 },
  food:         { avg: 1.50, achievable: 3.00 },
  home:         { avg: 1.20, achievable: 2.00 },
  electronics:  { avg: 1.20, achievable: 2.00 },
  fitness:      { avg: 1.60, achievable: 2.40 },
  jewelry:      { avg: 0.80, achievable: 1.40 },
  other:        { avg: 1.40, achievable: 2.20 },
};

function roundNicely(n: number): number {
  if (n < 100) return Math.round(n / 5) * 5;
  if (n < 1000) return Math.round(n / 25) * 25;
  if (n < 10000) return Math.round(n / 100) * 100;
  return Math.round(n / 500) * 500;
}

export function calculateRevenueLoss(
  score: number,
  productPrice: number,
  estimatedVisitors: number,
  productCategory: string
) {
  const benchmarks = CATEGORY_BENCHMARKS[productCategory] || CATEGORY_BENCHMARKS["other"];
  const { avg, achievable } = benchmarks;
  const price = productPrice || 35;
  const visitors = estimatedVisitors || 500;

  const bottomCR = avg * 0.4;
  const scoreNorm = score / 100;
  const estimatedCR = bottomCR + scoreNorm * (achievable - bottomCR);
  const gapVsAchievable = Math.max(0, achievable - estimatedCR) / 100;
  const pageAttributable = gapVsAchievable * 0.40;
  const additionalOrders = visitors * pageAttributable;
  const maxOrders = Math.max(0.3, 15 / Math.pow(1 + price / 50, 0.6));
  const cappedOrders = Math.min(additionalOrders, maxOrders);
  const monthlyLoss = cappedOrders * price;

  return {
    lossLow: Math.max(roundNicely(monthlyLoss * 0.7), 20),
    lossHigh: Math.max(roundNicely(monthlyLoss * 1.3), 50),
  };
}

/* ── Score color helpers ── */
export function scoreColor(score: number): string {
  if (score >= 70) return "var(--success)";
  if (score >= 40) return "var(--warning)";
  return "var(--error)";
}

export function scoreColorText(score: number): string {
  if (score >= 70) return "var(--success-text)";
  if (score >= 40) return "var(--warning-text)";
  return "var(--error-text)";
}

export function scoreColorTintBg(score: number): string {
  if (score >= 70) return "var(--success-light)";
  if (score >= 40) return "var(--warning-light)";
  return "var(--error-light)";
}

/* ── Build leak cards from categories + tips ── */
export const CATEGORY_LABELS: Record<string, string> = {
  title: "Title",
  images: "Images",
  pricing: "Pricing",
  socialProof: "Social Proof",
  cta: "CTA",
  description: "Description",
  trust: "Trust",
};

const CATEGORY_PROBLEMS: Record<string, { low: string; mid: string }> = {
  title: { low: "Product title fails to communicate value or key benefits", mid: "Title misses opportunities to highlight differentiators" },
  images: { low: "Product imagery is insufficient for purchase confidence", mid: "Image gallery lacks variety and lifestyle context" },
  pricing: { low: "Price presentation creates friction and lacks anchoring", mid: "Pricing strategy misses conversion optimization basics" },
  socialProof: { low: "No visible social proof to build buyer confidence", mid: "Social proof elements are present but poorly positioned" },
  cta: { low: "Call-to-action is weak, hidden, or lacks urgency", mid: "CTA could be more prominent and compelling" },
  description: { low: "Product description fails to sell — wall of text or missing", mid: "Description needs better structure and benefit focus" },
  trust: { low: "No trust signals visible — guarantees, returns, or badges missing", mid: "Trust elements present but not prominently displayed" },
};

export function buildLeaks(categories: CategoryScores, tips: string[]): LeakCard[] {
  const entries = Object.entries(categories) as [keyof CategoryScores, number][];
  entries.sort((a, b) => a[1] - b[1]);

  return entries.slice(0, 7).map((entry, i) => {
    const [key, catScore] = entry;
    let impact: "HIGH" | "MED" | "LOW";
    let revenue: string;
    if (i === 0) {
      impact = "HIGH";
      revenue = `+$${150 + (catScore * 7) % 50}/mo`;
    } else if (i === 1) {
      impact = "MED";
      revenue = `+$${80 + (catScore * 11) % 40}/mo`;
    } else {
      impact = "LOW";
      revenue = `+$${30 + (catScore * 13) % 30}/mo`;
    }
    const problems = CATEGORY_PROBLEMS[key] || { low: `Improve your ${key} to increase conversions.`, mid: `Your ${key} needs optimization.` };
    const problem = catScore <= 40 ? problems.low : problems.mid;
    const tip = tips[i] || `Improve your ${key} to increase conversions.`;
    return { key, catScore, impact, revenue, tip, problem, category: CATEGORY_LABELS[key] || key };
  });
}

/* ── URL validation ── */
export function isValidUrl(input: string): string | null {
  const trimmed = input.trim();
  const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  try {
    const parsed = new URL(withProtocol);
    if (!["http:", "https:"].includes(parsed.protocol)) return null;
    if (!parsed.hostname.includes(".")) return null;
    return parsed.href;
  } catch {
    return null;
  }
}

/** Check if a URL looks like a product page (vs homepage/collection) */
export function isProductPageUrl(url: string): boolean {
  try {
    const urlPath = new URL(url).pathname;
    return /\/products\/[^/]+/.test(urlPath);
  } catch {
    return false;
  }
}

/** Extract hostname from URL, returns empty string on failure */
export function extractDomain(url: string): string {
  try { return new URL(url).hostname; } catch { return ""; }
}

/** Parse API response into a safe FreeResult */
export function parseAnalysisResponse(data: Record<string, unknown>): FreeResult {
  const cats = data.categories as Record<string, unknown> | undefined;
  const safeCategories: CategoryScores = {
    title: Number(cats?.title) || 0,
    images: Number(cats?.images) || 0,
    pricing: Number(cats?.pricing) || 0,
    socialProof: Number(cats?.socialProof) || 0,
    cta: Number(cats?.cta) || 0,
    description: Number(cats?.description) || 0,
    trust: Number(cats?.trust) || 0,
  };

  return {
    score: Math.min(100, Math.max(0, Number(data.score) || 0)),
    summary: String(data.summary || "Analysis complete."),
    tips: Array.isArray(data.tips) ? data.tips.map(String).slice(0, 7) : [],
    categories: safeCategories,
    productPrice: Number(data.productPrice) || 0,
    productCategory: String(data.productCategory || "other"),
    estimatedMonthlyVisitors: Number(data.estimatedMonthlyVisitors) || 1000,
  };
}
