import { describe, it, expect } from "vitest";
import { calculateConversionLoss, buildLeaks, groupLeaks } from "@/lib/analysis/helpers";
import {
  DIMENSION_IMPACT_WEIGHTS,
  ACTIVE_DIMENSIONS,
} from "@/lib/analysis/constants";
import type { CategoryScores } from "@/lib/analysis/types";

/* ── calculateConversionLoss formula tests ─────────────────── */

describe("calculateConversionLoss", () => {
  it("max loss for Very High tier (checkout score 0) → 25%", () => {
    expect(calculateConversionLoss(0, "checkout")).toBe(25);
  });

  it("perfect score → 0% loss", () => {
    expect(calculateConversionLoss(100, "checkout")).toBe(0);
  });

  it("mid score, High tier (pricing score 50) → 10%", () => {
    expect(calculateConversionLoss(50, "pricing")).toBe(10);
  });

  it("mid score, Low-Medium tier (contentFreshness score 50) → 2.5%", () => {
    expect(calculateConversionLoss(50, "contentFreshness")).toBe(2.5);
  });

  it("all 18 dimensions produce values >= 0 and <= 30", () => {
    for (const key of ACTIVE_DIMENSIONS) {
      for (const score of [0, 25, 50, 75, 100]) {
        const loss = calculateConversionLoss(score, key);
        expect(loss).toBeGreaterThanOrEqual(0);
        expect(loss).toBeLessThanOrEqual(30);
      }
    }
  });

  // Negative / boundary tests
  it("score < 0 is clamped to 0 (same as score 0)", () => {
    expect(calculateConversionLoss(-50, "checkout")).toBe(
      calculateConversionLoss(0, "checkout"),
    );
  });

  it("score > 100 is clamped to 100 (returns 0)", () => {
    expect(calculateConversionLoss(150, "checkout")).toBe(0);
  });

  it("unknown dimension key returns 0", () => {
    expect(calculateConversionLoss(50, "nonExistentKey")).toBe(0);
  });
});

/* ── DIMENSION_IMPACT_WEIGHTS constant tests ───────────────── */

describe("DIMENSION_IMPACT_WEIGHTS", () => {
  it("has exactly the 18 ACTIVE_DIMENSIONS keys", () => {
    const weightKeys = new Set(Object.keys(DIMENSION_IMPACT_WEIGHTS));
    expect(weightKeys.size).toBe(ACTIVE_DIMENSIONS.size);
    for (const key of ACTIVE_DIMENSIONS) {
      expect(weightKeys.has(key)).toBe(true);
    }
  });

  it("all weights are between 0.01 and 0.50", () => {
    for (const [, weight] of Object.entries(DIMENSION_IMPACT_WEIGHTS)) {
      expect(weight).toBeGreaterThanOrEqual(0.01);
      expect(weight).toBeLessThanOrEqual(0.50);
    }
  });

  it("Very High > High > Medium-High > Medium > Low-Medium", () => {
    const veryHigh = DIMENSION_IMPACT_WEIGHTS["checkout"];
    const high = DIMENSION_IMPACT_WEIGHTS["pricing"];
    const mediumHigh = DIMENSION_IMPACT_WEIGHTS["description"];
    const medium = DIMENSION_IMPACT_WEIGHTS["trust"];
    const lowMedium = DIMENSION_IMPACT_WEIGHTS["accessibility"];

    expect(veryHigh).toBeGreaterThan(high);
    expect(high).toBeGreaterThan(mediumHigh);
    expect(mediumHigh).toBeGreaterThan(medium);
    expect(medium).toBeGreaterThan(lowMedium);
  });
});

/* ── Helper: full CategoryScores fixtures ──────────────────── */

function makeCategoryScores(defaultScore: number): CategoryScores {
  return {
    pageSpeed: defaultScore, images: defaultScore, socialProof: defaultScore,
    checkout: defaultScore, mobileCta: defaultScore, title: defaultScore,
    aiDiscoverability: defaultScore, structuredData: defaultScore, pricing: defaultScore,
    description: defaultScore, shipping: defaultScore, crossSell: defaultScore,
    trust: defaultScore, socialCommerce: defaultScore, sizeGuide: defaultScore,
    variantUx: defaultScore, accessibility: defaultScore, contentFreshness: defaultScore,
  };
}

/* ── buildLeaks tests ──────────────────────────────────────── */

describe("buildLeaks", () => {
  it("returns 18 cards when given full CategoryScores", () => {
    const categories = makeCategoryScores(50);
    const tips = Array.from({ length: 18 }, (_, i) => `Tip ${i + 1}`);
    const cards = buildLeaks(categories, tips);
    expect(cards).toHaveLength(18);
  });

  it("each card has conversionLoss > 0 when score < 100", () => {
    const categories = makeCategoryScores(50);
    const tips = Array.from({ length: 18 }, (_, i) => `Tip ${i + 1}`);
    const cards = buildLeaks(categories, tips);
    for (const card of cards) {
      expect(card.conversionLoss).toBeGreaterThan(0);
    }
  });

  it("each card's revenue string contains '%' and not '$'", () => {
    const categories = makeCategoryScores(30);
    const tips = Array.from({ length: 18 }, (_, i) => `Tip ${i + 1}`);
    const cards = buildLeaks(categories, tips);
    for (const card of cards) {
      expect(card.revenue).toContain("%");
      expect(card.revenue).not.toContain("$");
    }
  });

  it("cards are sorted worst-first (lowest catScore first)", () => {
    const categories = makeCategoryScores(50);
    categories.checkout = 10; // worst
    categories.contentFreshness = 90; // best
    const tips = Array.from({ length: 18 }, (_, i) => `Tip ${i + 1}`);
    const cards = buildLeaks(categories, tips);
    expect(cards[0].key).toBe("checkout");
    expect(cards[cards.length - 1].key).toBe("contentFreshness");
    // Verify overall sort
    for (let i = 1; i < cards.length; i++) {
      expect(cards[i].catScore).toBeGreaterThanOrEqual(cards[i - 1].catScore);
    }
  });

  it("uses dimensionTips when provided", () => {
    const categories = makeCategoryScores(50);
    const tips = ["fallback tip"];
    const dimTips = { checkout: ["Use Shop Pay for faster checkout"] };
    const cards = buildLeaks(categories, tips, dimTips);
    const checkoutCard = cards.find((c) => c.key === "checkout")!;
    expect(checkoutCard.tip).toBe("Use Shop Pay for faster checkout");
  });

  it("perfect scores (100) produce conversionLoss = 0 on every card", () => {
    const categories = makeCategoryScores(100);
    const tips: string[] = [];
    const cards = buildLeaks(categories, tips);
    for (const card of cards) {
      expect(card.conversionLoss).toBe(0);
      expect(card.revenue).toBe("~0% conversion loss");
    }
  });
});

/* ── groupLeaks tests ──────────────────────────────────────── */

describe("groupLeaks", () => {
  it("returns groups with conversionLoss aggregated correctly", () => {
    const categories = makeCategoryScores(50);
    const tips = Array.from({ length: 18 }, (_, i) => `Tip ${i + 1}`);
    const cards = buildLeaks(categories, tips);
    const groups = groupLeaks(cards);

    expect(groups.length).toBeGreaterThan(0);
    for (const group of groups) {
      const expectedLoss = group.leaks.reduce((sum, l) => sum + l.conversionLoss, 0);
      expect(group.conversionLoss).toBe(Math.round(expectedLoss * 10) / 10);
    }
  });

  it("a group's conversionLoss equals the sum of its cards' conversionLoss", () => {
    const categories = makeCategoryScores(30);
    categories.checkout = 10; // Very High weight, low score → high loss
    categories.images = 90;   // Very High weight, high score → low loss
    const tips = Array.from({ length: 18 }, (_, i) => `Tip ${i + 1}`);
    const cards = buildLeaks(categories, tips);
    const groups = groupLeaks(cards);

    for (const group of groups) {
      const cardSum = group.leaks.reduce((sum, l) => sum + l.conversionLoss, 0);
      expect(group.conversionLoss).toBe(Math.round(cardSum * 10) / 10);
    }
  });

  it("groups are sorted worst-first (lowest avgScore first)", () => {
    const categories = makeCategoryScores(50);
    categories.checkout = 10; // conversion group → low avg
    categories.mobileCta = 15;
    categories.crossSell = 20;
    const tips = Array.from({ length: 18 }, (_, i) => `Tip ${i + 1}`);
    const cards = buildLeaks(categories, tips);
    const groups = groupLeaks(cards);

    for (let i = 1; i < groups.length; i++) {
      expect(groups[i].avgScore).toBeGreaterThanOrEqual(groups[i - 1].avgScore);
    }
  });

});
