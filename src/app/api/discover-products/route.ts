import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const { url } = await req.json();

    if (!url || typeof url !== "string") {
      return NextResponse.json({ error: "URL is required" }, { status: 400 });
    }

    const res = await fetch(url, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        Accept:
          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
      },
      signal: AbortSignal.timeout(10000),
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: `Could not fetch that URL (${res.status})` },
        { status: 400 }
      );
    }

    const html = await res.text();

    // Extract product links — Shopify uses /products/ or /collections/.../products/
    const productLinkRegex = /href=["']((?:https?:\/\/[^"']*)?\/products\/[^"'#?]+)/gi;
    const titleRegex = /<title[^>]*>([^<]+)<\/title>/i;

    const seen = new Set<string>();
    const products: Array<{ url: string; slug: string }> = [];
    let match;

    const baseUrl = new URL(url);

    while ((match = productLinkRegex.exec(html)) !== null) {
      let href = match[1];
      // Resolve relative URLs
      if (href.startsWith("/")) {
        href = `${baseUrl.protocol}//${baseUrl.host}${href}`;
      }
      // Normalize: remove trailing slashes, query params
      try {
        const parsed = new URL(href);
        const clean = `${parsed.protocol}//${parsed.host}${parsed.pathname.replace(/\/$/, "")}`;
        if (seen.has(clean)) continue;
        seen.add(clean);

        // Extract slug for display
        const slug = parsed.pathname
          .split("/products/")[1]
          ?.replace(/-/g, " ")
          .replace(/\//g, "")
          .trim();
        if (slug) {
          products.push({ url: clean, slug });
        }
      } catch {
        continue;
      }

      if (products.length >= 20) break;
    }

    // Extract page title for store name
    const titleMatch = html.match(titleRegex);
    const storeName = titleMatch?.[1]?.trim().split(/[–—|]/)[0]?.trim() || "";

    return NextResponse.json({
      products,
      storeName,
      isProductPage: html.includes("/products/") && products.length <= 2 && /add.to.cart|AddToCart|product-form/i.test(html),
    });
  } catch (err) {
    console.error("Discover products error:", err);
    return NextResponse.json(
      { error: "Could not fetch that URL. Make sure it's accessible." },
      { status: 400 }
    );
  }
}
