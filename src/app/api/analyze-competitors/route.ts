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
- "categories": object with scores 0-10 for each: { "title", "images", "pricing", "socialProof", "cta", "description", "trust" }

Score these e-commerce specific criteria:
- Title: Does it include product name, key benefit, and relevant keywords?
- Images: Are there multiple high-quality images? Lifestyle shots? Zoom capability?
- Pricing: Is there price anchoring? Original price shown? Savings highlighted?
- Social proof: Reviews count, star ratings, UGC, testimonials visible?
- CTA: Is "Add to Cart" prominent, above the fold, with urgency signals?
- Description: Does it lead with benefits over features? Scannable format?
- Trust: Are there badges, guarantees, secure checkout signals, return policy?

Be specific and reference actual content from the page. Be honest — don't inflate scores. If the page is a 404 or error page, score it 0 and say so.

HTML:
`;

async function fetchPageHtml(url: string): Promise<string> {
  const res = await fetch(url, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (compatible; PageLeaks/1.0; +https://pageleaks.com)",
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
      model: "openai/gpt-4o-mini",
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
  return {
    score: Math.min(100, Math.max(0, Number(result.score) || 50)),
    summary: result.summary || "Analysis complete.",
    tips: (result.tips || []).slice(0, 3),
    categories: result.categories || {},
  };
}

async function identifyCompetitors(
  html: string,
  apiKey: string
): Promise<Competitor[]> {
  const prompt = `You are an e-commerce expert. Based on this Shopify product page HTML, identify 2-3 real competitor product pages that sell similar items. Return a JSON array of { "name": "Brand - Product Name", "url": "https://..." } with direct product page URLs (not homepages). Only return real, likely-accessible URLs from well-known brands or stores in the same niche.

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
      model: "openai/gpt-4o-mini",
      messages: [{ role: "user", content: prompt }],
      temperature: 0.5,
      max_tokens: 300,
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
  return competitors.slice(0, 3);
}

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

    // Step 1: Fetch and analyze the user's page
    let userHtml: string;
    try {
      userHtml = await fetchPageHtml(url);
    } catch {
      return NextResponse.json(
        { error: "Could not fetch that URL. Make sure it's accessible." },
        { status: 400 }
      );
    }

    // Step 2: Score user's page + identify competitors in parallel
    const [userAnalysis, competitors] = await Promise.all([
      scorePage(userHtml, apiKey),
      identifyCompetitors(userHtml, apiKey),
    ]);

    // Step 3: Fetch and score each competitor page
    const competitorResults = await Promise.allSettled(
      competitors.map(async (comp) => {
        try {
          const html = await fetchPageHtml(comp.url);
          const analysis = await scorePage(html, apiKey);
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
      })
    );

    const scoredCompetitors = competitorResults
      .filter(
        (r): r is PromiseFulfilledResult<{
          name: string;
          url: string;
          score: number;
          summary: string;
          categories: CategoryScores;
        }> => r.status === "fulfilled" && r.value !== null
      )
      .map((r) => r.value);

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
