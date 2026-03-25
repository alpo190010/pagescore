"use client";

import { useState, useEffect, useRef } from "react";

/* ── Lazy PostHog — don't block initial paint with 176KB bundle ── */
export function captureEvent(event: string, properties?: Record<string, unknown>) {
  import("posthog-js").then(({ default: posthog }) => {
    try { posthog.capture(event, properties); } catch { /* not initialized */ }
  });
}

/* ══════════════════════════════════════════════════════════════
   Types — 20 Dimensions
   ══════════════════════════════════════════════════════════════ */

export interface CategoryScores {
  pageSpeed: number;
  images: number;
  socialProof: number;
  checkout: number;
  mobileCta: number;
  title: number;
  aiDiscoverability: number;
  structuredData: number;
  pricing: number;
  description: number;
  shipping: number;
  crossSell: number;
  cartRecovery: number;
  trust: number;
  merchantFeed: number;
  socialCommerce: number;
  sizeGuide: number;
  variantUx: number;
  accessibility: number;
  contentFreshness: number;
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

/** Shape of each entry returned by `buildLeaks` */
export interface LeakCard {
  key: string;
  catScore: number;
  impact: string;
  revenue: string;
  tip: string;
  problem: string;
  category: string;
  revenueImpact: string;
}

/* ══════════════════════════════════════════════════════════════
   Constants — 20 Dimensions
   ══════════════════════════════════════════════════════════════ */

export const CATEGORY_BENCHMARKS: Record<string, { avg: number; achievable: number }> = {
  fashion:      { avg: 1.90, achievable: 2.80 },
  beauty:       { avg: 2.50, achievable: 3.70 },
  food:         { avg: 1.50, achievable: 3.00 },
  home:         { avg: 1.20, achievable: 2.00 },
  electronics:  { avg: 1.20, achievable: 2.00 },
  fitness:      { avg: 1.60, achievable: 2.40 },
  jewelry:      { avg: 0.80, achievable: 1.40 },
  other:        { avg: 1.40, achievable: 2.20 },
};

export const CATEGORY_LABELS: Record<string, string> = {
  pageSpeed: "Page Speed",
  images: "Product Images",
  socialProof: "Reviews & Social Proof",
  checkout: "Checkout & Payments",
  mobileCta: "Mobile CTA & UX",
  title: "Title & SEO",
  aiDiscoverability: "AI Discoverability",
  structuredData: "Schema Markup",
  pricing: "Pricing Psychology",
  description: "Description Quality",
  shipping: "Shipping Transparency",
  crossSell: "Cross-Sell & Upsell",
  cartRecovery: "Cart Recovery Flows",
  trust: "Trust & Guarantees",
  merchantFeed: "Merchant Feed Quality",
  socialCommerce: "Social Commerce",
  sizeGuide: "Size & Fit Info",
  variantUx: "Variant UX & Stock",
  accessibility: "Accessibility",
  contentFreshness: "Content Freshness",
};

export const CATEGORY_REVENUE_IMPACT: Record<string, string> = {
  pageSpeed: "Very High",
  images: "Very High",
  socialProof: "Very High",
  checkout: "Very High",
  mobileCta: "High",
  title: "High",
  aiDiscoverability: "High",
  structuredData: "High",
  pricing: "High",
  description: "Medium-High",
  shipping: "Medium-High",
  crossSell: "Medium-High",
  cartRecovery: "Medium-High",
  trust: "Medium",
  merchantFeed: "Medium",
  socialCommerce: "Medium",
  sizeGuide: "Medium",
  variantUx: "Medium",
  accessibility: "Low-Medium",
  contentFreshness: "Low-Medium",
};

export const CATEGORY_PROBLEMS: Record<string, { low: string; mid: string }> = {
  pageSpeed: { low: "Page loads too slowly. A 1-second delay cuts conversions ~7%", mid: "Page speed could be faster. Only 48% of Shopify stores pass Core Web Vitals on mobile" },
  images: { low: "Product imagery is insufficient. 56% of users explore images before reading anything", mid: "Image gallery lacks variety. Missing lifestyle, scale, or texture shots" },
  socialProof: { low: "No visible reviews. Going from 0 to 5 reviews delivers a 270% conversion lift", mid: "Social proof present but poorly positioned. UGC photo reviews drive 144-161% higher conversion" },
  checkout: { low: "Checkout options are limited. Shop Pay alone lifts conversion up to 50%", mid: "Payment options could be expanded. BNPL increases conversion 35% on higher-ticket items" },
  mobileCta: { low: "CTA is hidden or broken on mobile. 77% of traffic is mobile but converts at half the desktop rate", mid: "Mobile CTA could be more prominent. Sticky add-to-cart buttons are non-negotiable" },
  title: { low: "Product title fails to communicate value or include key search terms", mid: "Title misses SEO opportunities. Primary keyword should be in the first 3-5 words" },
  aiDiscoverability: { low: "Page is invisible to AI shopping. AI-referred traffic converts at 14.2% vs 2.8% from Google", mid: "AI discoverability could be improved. AI traffic to retail grew 4,700% YoY" },
  structuredData: { low: "Missing or broken schema markup. 65% of pages cited by Google AI Mode include structured data", mid: "Schema markup is incomplete. Rich snippets boost CTR up to 25%" },
  pricing: { low: "Price presentation creates friction. No anchoring, no compare-at price, no installment framing", mid: "Pricing psychology underutilized. Charm pricing and anchoring shift conversion measurably" },
  description: { low: "Description fails to sell. 78% of sites don't structure by highlights", mid: "Description needs better structure and benefit focus" },
  shipping: { low: "Hidden shipping costs cause 48% of all cart abandonment", mid: "Shipping info is vague. Concrete delivery dates outperform estimates. 41% of sites fail here" },
  crossSell: { low: "No cross-sell or upsell strategy. AI recommendations can increase AOV by 18.65%", mid: "Cross-sell present but not optimized. Show 4-6 recommendations near the buy section" },
  cartRecovery: { low: "No abandoned cart recovery flows. Automated flows drive 30% of email revenue", mid: "Cart recovery could be stronger. Three emails recover 37% more carts than one" },
  trust: { low: "No trust signals visible. Visible phone numbers are the #1 global trust symbol", mid: "Trust elements present but not prominently displayed" },
  merchantFeed: { low: "No Google Merchant feed detected. 75% of retail ad clicks come from Shopping Ads", mid: "Feed quality could be improved. GTIN accuracy alone increases conversion up to 20%" },
  socialCommerce: { low: "No social commerce integration. TikTok Shop drives 3-5x higher conversion than static listings", mid: "Social commerce is underutilized. Pinterest Rich Pins increase CTR 39%" },
  sizeGuide: { low: "No size guide. 30-40% of clothing returns are size-related", mid: "Size info could be more interactive. Fit finders dramatically outperform static charts" },
  variantUx: { low: "Variant selection is confusing. Color swatches outperform dropdowns for visual products", mid: "Variant UX could improve. Low-stock warnings reduce abandonment by 8%" },
  accessibility: { low: "Accessibility issues detected. 4,500+ lawsuits filed in 2024, up 37% in 2025", mid: "Some accessibility gaps. 54% of Shopify stores fail color contrast" },
  contentFreshness: { low: "Content appears stale. Outdated badges and certifications erode trust", mid: "Content could be fresher. Regular updates signal relevance to search engines and AI" },
};

/** Category SVG icons — solid, monochrome */
export const CATEGORY_SVG: Record<string, React.ReactNode> = {
  pageSpeed: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M11 21h-1l1-7H7.5c-.88 0-.33-.75-.31-.78C8.48 10.94 10.42 7.54 13.01 3h1l-1 7h3.51c.4 0 .62.19.4.66C12.97 17.55 11 21 11 21z"/>
    </svg>
  ),
  images: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
    </svg>
  ),
  socialProof: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
    </svg>
  ),
  checkout: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49A1.003 1.003 0 0020 4H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/>
    </svg>
  ),
  mobileCta: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z"/>
    </svg>
  ),
  title: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M5 4v3h5.5v12h3V7H19V4H5z"/>
    </svg>
  ),
  aiDiscoverability: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/>
    </svg>
  ),
  structuredData: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/>
    </svg>
  ),
  pricing: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
    </svg>
  ),
  description: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11zM8 15h8v2H8v-2zm0-4h8v2H8v-2z"/>
    </svg>
  ),
  shipping: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M20 8h-3V4H3c-1.1 0-2 .9-2 2v11h2c0 1.66 1.34 3 3 3s3-1.34 3-3h6c0 1.66 1.34 3 3 3s3-1.34 3-3h2v-5l-3-4zM6 18.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm13.5-9l1.96 2.5H17V9.5h2.5zm-1.5 9c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/>
    </svg>
  ),
  crossSell: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
    </svg>
  ),
  cartRecovery: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
    </svg>
  ),
  trust: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/>
    </svg>
  ),
  merchantFeed: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
    </svg>
  ),
  socialCommerce: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/>
    </svg>
  ),
  sizeGuide: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M21 6H3c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 10H3V8h2v4h2V8h2v4h2V8h2v4h2V8h2v4h2V8h2v8z"/>
    </svg>
  ),
  variantUx: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2C6.49 2 2 6.49 2 12s4.49 10 10 10 10-4.49 10-10S17.51 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm3-8c0 1.66-1.34 3-3 3s-3-1.34-3-3 1.34-3 3-3 3 1.34 3 3z"/>
    </svg>
  ),
  accessibility: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M20.5 6c-2.61.7-5.67 1-8.5 1s-5.89-.3-8.5-1L3 8c1.86.5 4 .83 6 1v13h2v-6h2v6h2V9c2-.17 4.14-.5 6-1l-.5-2zM12 6c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2z"/>
    </svg>
  ),
  contentFreshness: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
    </svg>
  ),
  cta: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6h2c0-1.66 1.34-3 3-3s3 1.34 3 3v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm0 12H6V10h12v10zm-6-3c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2z"/>
    </svg>
  ),
};

/** Leak categories for "What We Check" section on landing page */
export const LEAK_CATEGORIES = [
  { iconKey: "pageSpeed", label: "Page Speed", leak: "Slow loading kills 7% conversion per second", cost: "Every visitor affected on every page" },
  { iconKey: "images", label: "Images", leak: "Low-quality or too few photos", cost: "56% of users explore images first" },
  { iconKey: "socialProof", label: "Social Proof", leak: "Reviews missing or buried below fold", cost: "0→5 reviews = 270% conversion lift" },
  { iconKey: "checkout", label: "Checkout", leak: "Limited payment options", cost: "Shop Pay lifts conversion up to 50%" },
  { iconKey: "mobileCta", label: "Mobile CTA", leak: "CTA hidden or broken on mobile", cost: "77% of traffic, half the conversion" },
  { iconKey: "title", label: "Title & SEO", leak: "Generic title misses search traffic", cost: "No discovery = no sales" },
  { iconKey: "aiDiscoverability", label: "AI Discovery", leak: "Invisible to ChatGPT and AI shopping", cost: "AI traffic converts at 14.2% vs 2.8%" },
  { iconKey: "structuredData", label: "Schema", leak: "Missing structured data", cost: "65% of AI-cited pages have schema" },
  { iconKey: "pricing", label: "Pricing", leak: "No anchoring or installment framing", cost: "Price feels high with no context" },
  { iconKey: "description", label: "Description", leak: "Wall of text, no benefits", cost: "78% of sites fail description structure" },
  { iconKey: "shipping", label: "Shipping", leak: "Hidden costs at checkout", cost: "#1 cart abandonment reason (48%)" },
  { iconKey: "crossSell", label: "Cross-Sell", leak: "No recommendations near buy button", cost: "Missing 18% AOV increase" },
  { iconKey: "cartRecovery", label: "Cart Recovery", leak: "No abandoned cart emails", cost: "2% of sends = 30% of email revenue" },
  { iconKey: "trust", label: "Trust", leak: "No guarantees or contact info visible", cost: "Doubt kills the sale at checkout" },
  { iconKey: "merchantFeed", label: "Merchant Feed", leak: "Missing or broken Google Shopping feed", cost: "75% of ad clicks come from Shopping" },
  { iconKey: "socialCommerce", label: "Social Commerce", leak: "No TikTok Shop or Pinterest integration", cost: "3-5x higher conversion on social" },
  { iconKey: "sizeGuide", label: "Size Guide", leak: "No interactive size finder", cost: "30-40% of returns are size-related" },
  { iconKey: "variantUx", label: "Variants", leak: "Dropdowns instead of visual swatches", cost: "69% abandon when out of stock" },
  { iconKey: "accessibility", label: "Accessibility", leak: "Color contrast and screen reader issues", cost: "4,500+ lawsuits in 2024 alone" },
  { iconKey: "contentFreshness", label: "Freshness", leak: "Stale content and expired badges", cost: "Erodes trust with search engines & AI" },
];

/* ══════════════════════════════════════════════════════════════
   Helpers
   ══════════════════════════════════════════════════════════════ */

export function roundNicely(n: number): number {
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

/** Score → CSS color variable */
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

/** Build leak cards from categories + tips, sorted worst-first */
export function buildLeaks(categories: CategoryScores, tips: string[]): LeakCard[] {
  const entries = Object.entries(categories) as [keyof CategoryScores, number][];
  entries.sort((a, b) => a[1] - b[1]);

  return entries.map((entry, i) => {
    const [key, catScore] = entry;
    const impact = i < 3 ? "HIGH" : i < 8 ? "MED" : "LOW";
    let revenue: string;
    if (i < 3) {
      revenue = `+$${150 + (catScore * 7) % 50}/mo`;
    } else if (i < 8) {
      revenue = `+$${80 + (catScore * 11) % 40}/mo`;
    } else {
      revenue = `+$${30 + (catScore * 13) % 30}/mo`;
    }
    const problems = CATEGORY_PROBLEMS[key] || { low: `Improve your ${key} to increase conversions.`, mid: `Your ${key} needs optimization.` };
    const problem = catScore <= 40 ? problems.low : problems.mid;
    const tip = tips[i] || `Improve your ${key} to increase conversions.`;
    const revenueImpact = CATEGORY_REVENUE_IMPACT[key] || "Medium";
    return { key, catScore, impact, revenue, tip, problem, category: CATEGORY_LABELS[key] || key, revenueImpact };
  });
}

/** URL validation — returns normalized URL or null */
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

/* ══════════════════════════════════════════════════════════════
   Hooks
   ══════════════════════════════════════════════════════════════ */

export function useCountUp(target: number, duration = 1200) {
  const [value, setValue] = useState(0);
  const started = useRef(false);
  const rafId = useRef<number>(0);

  useEffect(() => {
    if (target <= 0) {
      started.current = false;
      setValue(0);
      return;
    }
    if (started.current) return;
    started.current = true;
    const start = performance.now();
    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) rafId.current = requestAnimationFrame(tick);
    }
    rafId.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId.current);
  }, [target, duration]);

  return value;
}

export function isProductPageUrl(url: string): boolean {
  try {
    const path = new URL(url).pathname;
    return /\/products\/[^/]+/.test(path) || /\/p\/[^/]+/.test(path);
  } catch { return false; }
}

export function extractDomain(url: string): string {
  try { return new URL(url).hostname; } catch { return ""; }
}

export function parseAnalysisResponse(data: Record<string, unknown>): FreeResult {
  const cats = data.categories as Record<string, unknown> | undefined;
  const safeCategories: CategoryScores = {
    pageSpeed: Number(cats?.pageSpeed) || 0,
    images: Number(cats?.images) || 0,
    socialProof: Number(cats?.socialProof) || 0,
    checkout: Number(cats?.checkout) || 0,
    mobileCta: Number(cats?.mobileCta) || 0,
    title: Number(cats?.title) || 0,
    aiDiscoverability: Number(cats?.aiDiscoverability) || 0,
    structuredData: Number(cats?.structuredData) || 0,
    pricing: Number(cats?.pricing) || 0,
    description: Number(cats?.description) || 0,
    shipping: Number(cats?.shipping) || 0,
    crossSell: Number(cats?.crossSell) || 0,
    cartRecovery: Number(cats?.cartRecovery) || 0,
    trust: Number(cats?.trust) || 0,
    merchantFeed: Number(cats?.merchantFeed) || 0,
    socialCommerce: Number(cats?.socialCommerce) || 0,
    sizeGuide: Number(cats?.sizeGuide) || 0,
    variantUx: Number(cats?.variantUx) || 0,
    accessibility: Number(cats?.accessibility) || 0,
    contentFreshness: Number(cats?.contentFreshness) || 0,
  };

  return {
    score: Math.min(100, Math.max(0, Number(data.score) || 0)),
    summary: String(data.summary || "Analysis complete."),
    tips: Array.isArray(data.tips) ? data.tips.map(String).slice(0, 20) : [],
    categories: safeCategories,
    productPrice: Number(data.productPrice) || 0,
    productCategory: String(data.productCategory || "other"),
    estimatedMonthlyVisitors: Number(data.estimatedMonthlyVisitors) || 1000,
  };
}
