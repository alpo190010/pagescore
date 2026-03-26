import type { CategoryScores } from "@/lib/analysis/types";

/* ══════════════════════════════════════════════════════════════
   Types
   ══════════════════════════════════════════════════════════════ */

export interface PageAnalysis {
  score: number;
  summary: string;
  tips: string[];
  categories: CategoryScores;
}

export interface Competitor {
  name: string;
  url: string;
}

/* ══════════════════════════════════════════════════════════════
   Constants
   ══════════════════════════════════════════════════════════════ */

export const SCORING_PROMPT = `You are an e-commerce conversion expert specializing in Shopify product pages. Analyze this HTML and return a JSON object with:
- "score": number 0-100 (overall product page conversion effectiveness)
- "summary": one-sentence assessment (max 30 words)
- "tips": array of exactly 3 specific, actionable improvement tips (each max 25 words)
- "categories": object with scores 0-100 for each: { "title", "images", "pricing", "socialProof", "cta", "description", "trust" }

Score these e-commerce specific criteria:
- Title: Does it include product name, key benefit, and relevant keywords?
- Images: Are there multiple high-quality images? Lifestyle shots? Zoom capability?
- Pricing: Is there price anchoring? Original price shown? Savings highlighted?
- Social proof: Reviews count, star ratings, UGC, testimonials visible?
- CTA: Is "Add to Cart" prominent, above the fold, with urgency signals?
- Description: Does it lead with benefits over features? Scannable format?
- Trust: Are there badges, guarantees, secure checkout signals, return policy?

All scores must be 0-100. Be specific and reference actual content from the page. Be honest — don't inflate scores. If the page is a 404 or error page, score it 0 and say so.

HTML:
`;

export const TARGET_COMPETITORS = 3;
export const MAX_ROUNDS = 2; // Ask AI for more candidates at most once

/* ══════════════════════════════════════════════════════════════
   Helpers
   ══════════════════════════════════════════════════════════════ */

/** Clamp an unknown value to a 0-100 integer score. */
const c = (v: unknown) => Math.min(100, Math.max(0, Number(v) || 0));

/** Build a full 20-field CategoryScores from a partial AI response. */
export function buildCategoryScores(cats: Record<string, unknown>): CategoryScores {
  return {
    pageSpeed: c(cats.pageSpeed), images: c(cats.images), socialProof: c(cats.socialProof),
    checkout: c(cats.checkout), mobileCta: c(cats.mobileCta), title: c(cats.title),
    aiDiscoverability: c(cats.aiDiscoverability), structuredData: c(cats.structuredData),
    pricing: c(cats.pricing), description: c(cats.description), shipping: c(cats.shipping),
    crossSell: c(cats.crossSell), cartRecovery: c(cats.cartRecovery), trust: c(cats.trust),
    merchantFeed: c(cats.merchantFeed), socialCommerce: c(cats.socialCommerce),
    sizeGuide: c(cats.sizeGuide), variantUx: c(cats.variantUx),
    accessibility: c(cats.accessibility), contentFreshness: c(cats.contentFreshness),
  };
}

/* ══════════════════════════════════════════════════════════════
   Network / AI Functions
   ══════════════════════════════════════════════════════════════ */

export async function fetchPageHtml(url: string): Promise<string> {
  const res = await fetch(url, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9",
      "Accept-Encoding": "gzip, deflate, br",
      "Cache-Control": "no-cache",
      "Sec-Fetch-Dest": "document",
      "Sec-Fetch-Mode": "navigate",
      "Sec-Fetch-Site": "none",
      "Sec-Fetch-User": "?1",
      "Upgrade-Insecure-Requests": "1",
    },
    signal: AbortSignal.timeout(10000),
  });
  const html = await res.text();
  return html.slice(0, 15000);
}

export async function scorePage(
  html: string,
  apiKey: string
): Promise<PageAnalysis> {
  const prompt = SCORING_PROMPT + html + "\n\nReturn ONLY valid JSON, no markdown.";

  const aiRes = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "openai/gpt-5.4-nano",
      messages: [{ role: "user", content: prompt }],
      temperature: 0.3,
      max_tokens: 500,
    }),
  });

  if (!aiRes.ok) {
    throw new Error("AI analysis failed");
  }

  const aiData = await aiRes.json();
  const content = aiData.choices?.[0]?.message?.content || "";
  const jsonMatch = content.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error("Failed to parse analysis");
  }

  const result = JSON.parse(jsonMatch[0]);
  const cats = result.categories || {};
  const categories = buildCategoryScores(cats);
  return {
    score: Math.min(100, Math.max(0, Number(result.score) || 50)),
    summary: result.summary || "Analysis complete.",
    tips: (result.tips || []).slice(0, 3),
    categories,
  };
}

export async function identifyCompetitors(
  html: string,
  apiKey: string
): Promise<Competitor[]> {
  const prompt = `You are an e-commerce expert. Based on this Shopify product page HTML, identify 5-6 real competitor product pages that sell similar items. Return a JSON array of { "name": "Brand - Product Name", "url": "https://..." } with direct product page URLs (not homepages).

IMPORTANT RULES:
- Only return real, currently-accessible product page URLs from well-known brands or established online stores.
- Prefer large retailers whose pages are reliably up (e.g. Amazon, Sephora, Target, Ulta, Nordstrom, REI, etc.) over small DTC brands whose URLs change frequently.
- URLs must be real product pages, not search results, category pages, or homepages.
- Return 5-6 candidates so we have enough even if some are unavailable.

HTML:
${html}

Return ONLY a valid JSON array, no markdown.`;

  const aiRes = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "openai/gpt-5.4-nano",
      messages: [{ role: "user", content: prompt }],
      temperature: 0.5,
      max_tokens: 500,
    }),
  });

  if (!aiRes.ok) {
    throw new Error("Competitor identification failed");
  }

  const aiData = await aiRes.json();
  const content = aiData.choices?.[0]?.message?.content || "";
  const jsonMatch = content.match(/\[[\s\S]*\]/);
  if (!jsonMatch) {
    return [];
  }

  const competitors: Competitor[] = JSON.parse(jsonMatch[0]);
  return competitors.slice(0, 6);
}

/** Check if a URL returns a real product page (no AI cost, just a fetch) */
export async function validatePageHtml(url: string): Promise<string | null> {
  try {
    const html = await fetchPageHtml(url);
    const lower = html.toLowerCase();
    if (
      html.length < 500 ||
      lower.includes("<title>404") ||
      lower.includes("<title>page not found") ||
      lower.includes("page not found") ||
      lower.includes("access denied") ||
      lower.includes("403 forbidden") ||
      lower.includes("just a moment") // Cloudflare challenge
    ) {
      return null;
    }
    return html;
  } catch {
    return null;
  }
}

/** Score a pre-validated HTML page. Returns null if AI result is garbage. */
export async function scoreValidatedPage(
  comp: Competitor,
  html: string,
  apiKey: string
): Promise<{
  name: string;
  url: string;
  score: number;
  summary: string;
  categories: CategoryScores;
} | null> {
  try {
    const analysis = await scorePage(html, apiKey);
    const catSum = Object.values(analysis.categories).reduce((a, b) => a + b, 0);
    if (
      analysis.score === 0 ||
      catSum === 0 ||
      /404|error page|cannot be assessed|not found|unable to|access denied/i.test(analysis.summary)
    ) {
      return null;
    }
    return {
      name: comp.name,
      url: comp.url,
      score: analysis.score,
      summary: analysis.summary,
      categories: analysis.categories,
    };
  } catch {
    return null;
  }
}
