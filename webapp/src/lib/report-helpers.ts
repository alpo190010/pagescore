/* ══════════════════════════════════════════════════════════════
   Report Helpers — pure functions for the public report page
   ══════════════════════════════════════════════════════════════ */

/**
 * Display labels for all 20 CategoryScores keys.
 * Duplicated from constants.tsx because that file imports React icons,
 * which triggers createContext and breaks Server Component evaluation.
 */
export const REPORT_CATEGORY_LABELS: Record<string, string> = {
  pageSpeed: "Page Speed", images: "Product Images", socialProof: "Reviews & Social Proof",
  checkout: "Checkout & Payments", mobileCta: "Mobile CTA & UX", title: "Title & SEO",
  aiDiscoverability: "AI Discoverability", structuredData: "Schema Markup", pricing: "Pricing Psychology",
  description: "Description Quality", shipping: "Shipping Transparency", crossSell: "Cross-Sell & Upsell",
  cartRecovery: "Cart Recovery Flows", trust: "Trust & Guarantees", merchantFeed: "Merchant Feed Quality",
  socialCommerce: "Social Commerce", sizeGuide: "Size & Fit Info", variantUx: "Variant UX & Stock",
  accessibility: "Accessibility", contentFreshness: "Content Freshness",
};

/**
 * Dimensions with real scoring. Must match ACTIVE_DIMENSIONS in analysis/constants.tsx.
 * Can't import from there because it pulls in React icons → breaks Server Components.
 */
export const ACTIVE_REPORT_DIMENSIONS: ReadonlySet<string> = new Set(["socialProof"]);
export function getStatusLabel(score: number): string {
  if (score >= 70) return "Strong";
  if (score >= 40) return "Room to improve";
  return "Critical issue";
}

/** Score → CSS color variable (border/primary) */
export function scoreColor(score: number): string {
  if (score >= 70) return "var(--success)";
  if (score >= 40) return "var(--warning)";
  return "var(--error)";
}
/** High-contrast text variant */
export function scoreColorText(score: number): string {
  if (score >= 70) return "var(--success-text)";
  if (score >= 40) return "var(--warning-text)";
  return "var(--error-text)";
}
/** Tinted background variant */
export function scoreColorTintBg(score: number): string {
  if (score >= 70) return "var(--success-light)";
  if (score >= 40) return "var(--warning-light)";
  return "var(--error-light)";
}

/** Contextual assessment prose for each category × 3 levels */
export function getExplanation(key: string, score: number): string {
  const explanations: Record<string, Record<string, string>> = {
    title: {
      high: "Your product title is well-optimized with clear keywords and benefit-driven language that helps both SEO and conversions.",
      mid: "Your title could use stronger keyword targeting and benefit-driven language. Consider including the primary use case or key differentiator.",
      low: "Your product title needs urgent attention. It likely lacks keywords, is too generic, or doesn't communicate value. Rewrite with your top keyword + key benefit.",
    },
    images: {
      high: "Strong image presentation with multiple angles, lifestyle shots, and good quality. This builds buyer confidence effectively.",
      mid: "Your images are functional but could be stronger. Add lifestyle shots, zoom-capable high-res images, and show the product in use.",
      low: "Critical image issues detected. Missing multiple angles, poor quality, or no lifestyle context. Product images are the #1 conversion driver — fix this first.",
    },
    pricing: {
      high: "Good pricing presentation with effective anchoring, clear value proposition, and strategic use of compare-at prices or bundles.",
      mid: "Your pricing display could better communicate value. Consider adding compare-at prices, bundle savings, or per-unit cost breakdowns.",
      low: "Pricing presentation is hurting conversions. No anchoring, no perceived value, or confusing price structure. Add compare-at prices and emphasize savings.",
    },
    socialProof: {
      high: "Strong social proof with reviews, ratings, and trust indicators that help overcome purchase hesitation.",
      mid: "Some social proof present but underutilized. Feature review count more prominently, add photo reviews, or highlight specific testimonials.",
      low: "Critically low social proof. Missing or hidden reviews severely impact trust. Prioritize collecting and displaying customer reviews immediately.",
    },
    description: {
      high: "Well-written description with clear benefits, scannable formatting, and persuasive copy that addresses buyer concerns.",
      mid: "Description is adequate but could convert better. Break into scannable sections, lead with benefits over features, and address common objections.",
      low: "Product description needs a complete rewrite. It's either too thin, feature-only, wall-of-text, or missing entirely. Lead with benefits and use bullet points.",
    },
    trust: {
      high: "Good trust signals including shipping info, return policy, secure payment badges, and brand credibility indicators.",
      mid: "Some trust signals present but gaps remain. Add visible return policy, shipping timeline, payment security badges, and guarantee info near the buy button.",
      low: "Missing critical trust signals. Buyers don't feel safe purchasing. Add return policy, shipping info, security badges, and guarantees immediately.",
    },
    pageSpeed: {
      high: "Page loads quickly with good Core Web Vitals. Fast pages keep users engaged and improve search ranking.",
      mid: "Page speed is adequate but has room for improvement. Optimize images, reduce JavaScript, and consider lazy loading for below-fold content.",
      low: "Page loads too slowly. Every second of delay cuts conversions by approximately 7%. Prioritize image compression, code splitting, and server response time.",
    },
    checkout: {
      high: "Checkout experience is smooth with multiple payment options including express checkout and buy-now-pay-later.",
      mid: "Checkout could be streamlined. Consider adding express payment options like Shop Pay or Apple Pay to reduce friction.",
      low: "Checkout is a major conversion barrier. Limited payment options and a complex flow are costing you sales. Add express checkout and simplify the process.",
    },
    mobileCta: {
      high: "Mobile experience is strong with touch-friendly CTAs, readable text, and a smooth purchase flow on small screens.",
      mid: "Mobile CTA could be more prominent. Consider a sticky add-to-cart button and ensure all interactive elements are easily tappable.",
      low: "Mobile CTA is hidden or broken. With most traffic on mobile, this is critically hurting conversions. Add a sticky buy button and fix touch targets.",
    },
    aiDiscoverability: {
      high: "Good AI discoverability with structured content that AI shopping assistants can parse and recommend effectively.",
      mid: "AI discoverability could be improved. Add clear product attributes, FAQ content, and structured data to help AI assistants surface your products.",
      low: "Your page is invisible to AI shopping assistants. AI-referred traffic converts at much higher rates — add structured content and clear product metadata.",
    },
    structuredData: {
      high: "Schema markup is well-implemented with product, review, and pricing structured data helping search and AI visibility.",
      mid: "Schema markup is present but incomplete. Add review, pricing, and availability structured data for richer search results.",
      low: "Missing or broken schema markup. Structured data is essential for rich snippets and AI citations — implement Product schema immediately.",
    },
    shipping: {
      high: "Shipping info is clear and transparent with delivery estimates, free shipping thresholds, and return policy visible.",
      mid: "Shipping info is present but vague. Add concrete delivery dates and make free shipping thresholds more prominent.",
      low: "Hidden shipping costs are the #1 cause of cart abandonment. Display shipping info clearly near the buy button with delivery timelines.",
    },
    crossSell: {
      high: "Effective cross-sell and upsell strategy with relevant recommendations near the buy section increasing average order value.",
      mid: "Cross-sell is present but could be optimized. Show 4-6 relevant recommendations and consider bundle discounts.",
      low: "No cross-sell or upsell strategy. You're missing significant revenue — add AI-powered product recommendations near the buy button.",
    },
    cartRecovery: {
      high: "Cart recovery flows are in place with automated email sequences and exit-intent strategies to recapture abandoned carts.",
      mid: "Cart recovery could be stronger. Add a multi-email sequence and consider SMS or push notifications for abandoned carts.",
      low: "No cart recovery flows detected. Automated abandoned cart emails alone can drive 30% of email revenue — implement immediately.",
    },
    merchantFeed: {
      high: "Merchant feed is well-optimized for Google Shopping with accurate product data, GTINs, and competitive pricing.",
      mid: "Merchant feed quality could be improved. Ensure GTINs are accurate and product titles match search intent.",
      low: "No Google Merchant feed detected. Most retail ad clicks come from Shopping Ads — set up a properly optimized product feed.",
    },
    socialCommerce: {
      high: "Social commerce integration is strong with active presence on shoppable platforms driving additional sales channels.",
      mid: "Social commerce is underutilized. Consider Pinterest Rich Pins, Instagram Shopping, or TikTok Shop for higher-converting social traffic.",
      low: "No social commerce integration. Social shopping platforms drive significantly higher conversion rates — connect your catalog to at least one platform.",
    },
    sizeGuide: {
      high: "Size and fit information is comprehensive with interactive guides that help reduce size-related returns.",
      mid: "Size info could be more interactive. Consider a fit finder tool rather than a static size chart to reduce return rates.",
      low: "No size guide found. Size-related returns account for 30-40% of clothing returns — add an interactive size finder immediately.",
    },
    variantUx: {
      high: "Variant selection is intuitive with visual swatches, clear stock indicators, and smooth option changes.",
      mid: "Variant UX could improve. Replace dropdowns with visual swatches and add low-stock warnings to create urgency.",
      low: "Variant selection is confusing. Dropdowns instead of visual swatches and no stock info are hurting conversions — redesign the selection flow.",
    },
    accessibility: {
      high: "Good accessibility with proper contrast, keyboard navigation, and screen reader support meeting WCAG guidelines.",
      mid: "Some accessibility gaps detected. Check color contrast ratios, add missing alt text, and ensure keyboard navigation works throughout.",
      low: "Significant accessibility issues detected. Poor contrast, missing alt text, or broken keyboard navigation expose you to legal risk and exclude customers.",
    },
    contentFreshness: {
      high: "Content is fresh and up-to-date with current information, recent reviews, and active product updates.",
      mid: "Content could be fresher. Update product descriptions, add recent customer reviews, and ensure certifications are current.",
      low: "Content appears stale. Outdated badges, old reviews, and unchanged descriptions erode trust with both customers and search engines.",
    },
  };

  const level = score >= 70 ? "high" : score >= 40 ? "mid" : "low";
  return (
    explanations[key]?.[level] ??
    (score >= 70
      ? "This section is performing well."
      : score >= 40
        ? "There's room for improvement in this area."
        : "This needs urgent attention.")
  );
}
