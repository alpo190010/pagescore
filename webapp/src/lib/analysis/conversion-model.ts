/* ══════════════════════════════════════════════════════════════
   Conversion Model — pure TS, no React imports.
   Safe for Server Component / SSR import.
   ══════════════════════════════════════════════════════════════ */

/**
 * Numeric conversion-impact weights per dimension, used by calculateConversionLoss().
 * Tiers: Very High 0.25, High 0.20, Medium-High 0.13, Medium 0.08, Low-Medium 0.05.
 * Must stay in sync with ACTIVE_DIMENSIONS keys in constants.tsx.
 */
export const DIMENSION_IMPACT_WEIGHTS: Record<string, number> = {
  // Very High (0.25)
  pageSpeed: 0.25,
  images: 0.25,
  socialProof: 0.25,
  checkout: 0.25,
  // High (0.20)
  mobileCta: 0.20,
  title: 0.20,
  aiDiscoverability: 0.20,
  structuredData: 0.20,
  pricing: 0.20,
  // Medium-High (0.13)
  description: 0.13,
  shipping: 0.13,
  crossSell: 0.13,
  // Medium (0.08)
  trust: 0.08,
  socialCommerce: 0.08,
  sizeGuide: 0.08,
  variantUx: 0.08,
  // Low-Medium (0.05)
  accessibility: 0.05,
  contentFreshness: 0.05,
};

/**
 * Per-dimension conversion loss as a percentage (0–25).
 * Formula: ((100 - clamp(score, 0, 100)) / 100) × weight × 100
 * Returns 0 for unknown dimension keys. Rounded to 1 decimal place.
 */
export function calculateConversionLoss(score: number, dimensionKey: string): number {
  const weight = DIMENSION_IMPACT_WEIGHTS[dimensionKey] ?? 0;
  if (weight === 0) return 0;
  const clamped = Math.min(100, Math.max(0, score));
  const loss = ((100 - clamped) / 100) * weight * 100;
  return Math.round(loss * 10) / 10;
}
