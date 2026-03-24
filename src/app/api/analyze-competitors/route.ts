import { NextRequest, NextResponse } from "next/server";

interface CategoryScores {
  title: number;
  images: number;
  pricing: number;
  socialProof: number;
  cta: number;
  description: number;
  trust: number;
}

interface PageAnalysis {
  score: number;
  summary: string;
  tips: string[];
  categories: CategoryScores;
}

interface Competitor {
  name: string;
  url: string;
}

const SCORING_PROMPT = `You are an e-commerce conversion expert specializing in Shopify product pages. Analyze this HTML and return a JSON object with:
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

async function fetchPageHtml(url: string): Promise<string> {
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

async function scorePage(
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
      model: "deepseek/deepseek-v3.2",
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
  // Ensure all 7 category keys exist with numeric values 0-100
  const categories: CategoryScores = {
    title: Math.min(100, Math.max(0, Number(cats.title) || 0)),
    images: Math.min(100, Math.max(0, Number(cats.images) || 0)),
    pricing: Math.min(100, Math.max(0, Number(cats.pricing) || 0)),
    socialProof: Math.min(100, Math.max(0, Number(cats.socialProof) || 0)),
    cta: Math.min(100, Math.max(0, Number(cats.cta) || 0)),
    description: Math.min(100, Math.max(0, Number(cats.description) || 0)),
    trust: Math.min(100, Math.max(0, Number(cats.trust) || 0)),
  };
  return {
    score: Math.min(100, Math.max(0, Number(result.score) || 50)),
    summary: result.summary || "Analysis complete.",
    tips: (result.tips || []).slice(0, 3),
    categories,
  };
}

async function identifyCompetitors(
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
      model: "deepseek/deepseek-v3.2",
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
async function validatePageHtml(url: string): Promise<string | null> {
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
async function scoreValidatedPage(
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

const TARGET_COMPETITORS = 3;
const MAX_ROUNDS = 2; // Ask AI for more candidates at most once

export async function POST(req: NextRequest) {
  try {
    const { url } = await req.json();

    if (!url || typeof url !== "string") {
      return NextResponse.json({ error: "URL is required" }, { status: 400 });
    }

    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: "Server configuration error" },
        { status: 500 }
      );
    }

    // Step 1: Fetch the user's page
    let userHtml: string;
    try {
      userHtml = await fetchPageHtml(url);
    } catch {
      return NextResponse.json(
        { error: "Could not fetch that URL. Make sure it's accessible." },
        { status: 400 }
      );
    }

    // Step 2: Score user's page + get first batch of competitors in parallel
    const [userAnalysis, initialCandidates] = await Promise.all([
      scorePage(userHtml, apiKey),
      identifyCompetitors(userHtml, apiKey),
    ]);

    // Step 3: Validate → Score loop until we have 3 or run out of rounds
    const scoredCompetitors: Array<{
      name: string;
      url: string;
      score: number;
      summary: string;
      categories: CategoryScores;
    }> = [];
    const triedUrls = new Set<string>();

    let candidates = initialCandidates;

    for (let round = 0; round < MAX_ROUNDS && scoredCompetitors.length < TARGET_COMPETITORS; round++) {
      // Filter out already-tried URLs
      const untried = candidates.filter((c) => !triedUrls.has(c.url));
      if (untried.length === 0) break;

      // Phase A: Validate all untried URLs in parallel (cheap, no AI cost)
      const validationResults = await Promise.all(
        untried.map(async (comp) => {
          triedUrls.add(comp.url);
          const html = await validatePageHtml(comp.url);
          return html ? { comp, html } : null;
        })
      );
      const reachable = validationResults.filter(
        (r): r is { comp: Competitor; html: string } => r !== null
      );

      // Phase B: Score only reachable pages in parallel
      const needed = TARGET_COMPETITORS - scoredCompetitors.length;
      const toScore = reachable.slice(0, needed + 2); // score a couple extra in case AI returns garbage
      const scoreResults = await Promise.all(
        toScore.map(({ comp, html }) => scoreValidatedPage(comp, html, apiKey))
      );

      for (const result of scoreResults) {
        if (result && scoredCompetitors.length < TARGET_COMPETITORS) {
          scoredCompetitors.push(result);
        }
      }

      // If still short, ask AI for more candidates (round 2)
      if (scoredCompetitors.length < TARGET_COMPETITORS && round < MAX_ROUNDS - 1) {
        const alreadyNames = [
          ...scoredCompetitors.map((c) => c.name),
          ...Array.from(triedUrls),
        ].join(", ");
        candidates = await identifyCompetitors(
          userHtml + `\n\n<!-- EXCLUDE THESE (already tried): ${alreadyNames} -->`,
          apiKey
        );
      }
    }

    // Step 4: Fallback — if we still don't have enough, ask AI to score
    // competitors from its knowledge (no URL fetch needed)
    if (scoredCompetitors.length < TARGET_COMPETITORS) {
      const existingNames = scoredCompetitors.map((c) => c.name).join(", ");
      const shortfall = TARGET_COMPETITORS - scoredCompetitors.length;

      const fallbackPrompt = `You are an e-commerce conversion expert with deep knowledge of major retail product pages.

Based on this product page HTML, identify ${shortfall} real competitor products and score their product pages from your knowledge.

${existingNames ? `ALREADY INCLUDED (do NOT repeat): ${existingNames}` : ""}

For each competitor, return your best assessment of their typical product page quality. Use well-known brands whose product pages you know well.

Return a JSON array of objects:
[{
  "name": "Brand - Product Name",
  "score": number 0-100,
  "summary": "one-sentence assessment of their product page (max 30 words)",
  "categories": { "title": 0-100, "images": 0-100, "pricing": 0-100, "socialProof": 0-100, "cta": 0-100, "description": 0-100, "trust": 0-100 }
}]

Be realistic — score based on what these brands' product pages actually look like. Big brands often score high on images and trust but can score lower on CTA urgency or pricing anchoring.

HTML of the user's product:
${userHtml.slice(0, 5000)}

Return ONLY a valid JSON array, no markdown.`;

      try {
        const aiRes = await fetch("https://openrouter.ai/api/v1/chat/completions", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${apiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: "deepseek/deepseek-v3.2",
            messages: [{ role: "user", content: fallbackPrompt }],
            temperature: 0.4,
            max_tokens: 800,
          }),
        });

        if (aiRes.ok) {
          const aiData = await aiRes.json();
          const content = aiData.choices?.[0]?.message?.content || "";
          const jsonMatch = content.match(/\[[\s\S]*\]/);
          if (jsonMatch) {
            const fallbacks = JSON.parse(jsonMatch[0]) as Array<{
              name: string;
              score: number;
              summary: string;
              categories: Record<string, number>;
            }>;
            for (const fb of fallbacks) {
              if (scoredCompetitors.length >= TARGET_COMPETITORS) break;
              if (scoredCompetitors.some((c) => c.name === fb.name)) continue;
              const cats: CategoryScores = {
                title: Math.min(100, Math.max(0, Number(fb.categories?.title) || 0)),
                images: Math.min(100, Math.max(0, Number(fb.categories?.images) || 0)),
                pricing: Math.min(100, Math.max(0, Number(fb.categories?.pricing) || 0)),
                socialProof: Math.min(100, Math.max(0, Number(fb.categories?.socialProof) || 0)),
                cta: Math.min(100, Math.max(0, Number(fb.categories?.cta) || 0)),
                description: Math.min(100, Math.max(0, Number(fb.categories?.description) || 0)),
                trust: Math.min(100, Math.max(0, Number(fb.categories?.trust) || 0)),
              };
              const catSum = Object.values(cats).reduce((a, b) => a + b, 0);
              if (fb.score > 0 && catSum > 0) {
                scoredCompetitors.push({
                  name: fb.name,
                  url: "",
                  score: Math.min(100, Math.max(0, Number(fb.score) || 50)),
                  summary: fb.summary || "Scored from known brand data.",
                  categories: cats,
                });
              }
            }
          }
        }
      } catch (fallbackErr) {
        console.error("Fallback competitor scoring failed:", fallbackErr);
      }
    }

    return NextResponse.json({
      yourPage: {
        score: userAnalysis.score,
        summary: userAnalysis.summary,
        tips: userAnalysis.tips,
        categories: userAnalysis.categories,
        url,
      },
      competitors: scoredCompetitors,
    });
  } catch (err) {
    console.error("Competitor analysis error:", err);
    return NextResponse.json(
      { error: "Something went wrong" },
      { status: 500 }
    );
  }
}
