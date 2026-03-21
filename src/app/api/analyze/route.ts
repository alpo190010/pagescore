import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const { url } = await req.json();

    if (!url || typeof url !== "string") {
      return NextResponse.json({ error: "URL is required" }, { status: 400 });
    }

    // Fetch the page HTML
    let html: string;
    try {
      const res = await fetch(url, {
        headers: {
          "User-Agent":
            "Mozilla/5.0 (compatible; PageScore/1.0; +https://pagescore.app)",
        },
        signal: AbortSignal.timeout(10000),
      });
      html = await res.text();
    } catch {
      return NextResponse.json(
        { error: "Could not fetch that URL. Make sure it's accessible." },
        { status: 400 }
      );
    }

    // Truncate HTML to keep tokens reasonable
    const truncated = html.slice(0, 15000);

    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: "Server configuration error" },
        { status: 500 }
      );
    }

    const prompt = `You are a landing page conversion expert. Analyze this HTML and return a JSON object with:
- "score": number 0-100 (overall landing page effectiveness)
- "summary": one-sentence assessment (max 30 words)
- "tips": array of exactly 3 specific, actionable improvement tips (each max 25 words)

Be specific and reference actual content from the page. Be honest — don't inflate scores.

HTML:
${truncated}

Return ONLY valid JSON, no markdown.`;

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
      console.error("OpenAI error:", await aiRes.text());
      return NextResponse.json(
        { error: "AI analysis failed" },
        { status: 500 }
      );
    }

    const aiData = await aiRes.json();
    const content = aiData.choices?.[0]?.message?.content || "";

    // Parse JSON from response
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return NextResponse.json(
        { error: "Failed to parse analysis" },
        { status: 500 }
      );
    }

    const result = JSON.parse(jsonMatch[0]);

    return NextResponse.json({
      score: Math.min(100, Math.max(0, Number(result.score) || 50)),
      summary: result.summary || "Analysis complete.",
      tips: (result.tips || []).slice(0, 3),
    });
  } catch (err) {
    console.error("Analyze error:", err);
    return NextResponse.json(
      { error: "Something went wrong" },
      { status: 500 }
    );
  }
}
