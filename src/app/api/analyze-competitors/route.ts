import { NextRequest, NextResponse } from "next/server";
import type { CategoryScores } from "@/lib/analysis/types";
import {
  type Competitor,
  TARGET_COMPETITORS,
  MAX_ROUNDS,
  fetchPageHtml,
  scorePage,
  identifyCompetitors,
  validatePageHtml,
  scoreValidatedPage,
  buildCategoryScores,
} from "@/lib/competitor-analysis";

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
            model: "openai/gpt-5.4-nano",
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
              const cats = buildCategoryScores(fb.categories || {});
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
