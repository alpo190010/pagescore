import { describe, it, expect } from 'vitest';
import {
  calculateDollarLossPerThousand,
  CATEGORY_BENCHMARKS,
} from '@/lib/analysis/conversion-model';
import type { CategoryScores } from '@/lib/analysis/types';

/* ── Helper: uniform CategoryScores fixture ──────────────── */

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

/* ══════════════════════════════════════════════════════════════
   CATEGORY_BENCHMARKS structure tests
   ══════════════════════════════════════════════════════════════ */

describe('CATEGORY_BENCHMARKS', () => {
  const expectedCategories = [
    'fashion', 'beauty', 'food', 'home',
    'electronics', 'fitness', 'jewelry', 'other',
  ];

  it('has exactly 8 categories', () => {
    expect(Object.keys(CATEGORY_BENCHMARKS)).toHaveLength(8);
  });

  it('contains all expected category keys', () => {
    for (const cat of expectedCategories) {
      expect(CATEGORY_BENCHMARKS).toHaveProperty(cat);
    }
  });

  it('every category has floor, avg, achievable — all positive numbers', () => {
    for (const [name, bench] of Object.entries(CATEGORY_BENCHMARKS)) {
      expect(bench.floor, `${name}.floor`).toBeGreaterThan(0);
      expect(bench.avg, `${name}.avg`).toBeGreaterThan(0);
      expect(bench.achievable, `${name}.achievable`).toBeGreaterThan(0);
    }
  });

  it('floor < avg < achievable for every category (R032)', () => {
    for (const [name, bench] of Object.entries(CATEGORY_BENCHMARKS)) {
      expect(bench.floor, `${name}: floor < avg`).toBeLessThan(bench.avg);
      expect(bench.avg, `${name}: avg < achievable`).toBeLessThan(bench.achievable);
    }
  });

  it('floor values are non-zero for every category', () => {
    for (const [name, bench] of Object.entries(CATEGORY_BENCHMARKS)) {
      expect(bench.floor, `${name}.floor`).not.toBe(0);
    }
  });
});

/* ══════════════════════════════════════════════════════════════
   Piecewise-linear interpolation (tested indirectly via dollar loss)

   With uniform CategoryScores the weighted average equals the input
   score, so we can predict the CR and compute expected dollar loss.
   ══════════════════════════════════════════════════════════════ */

describe('scoreToConversionRate (indirect via calculateDollarLossPerThousand)', () => {
  it('score 0 → CR = floor (fashion)', () => {
    // CR = floor = 0.50%, achievable = 2.80%
    // loss = (0.028 - 0.005) × 1000 × 50 = 1150.00
    const result = calculateDollarLossPerThousand(makeCategoryScores(0), 50, 'fashion');
    expect(result).toBe(1150);
  });

  it('score 65 → CR = avg (fashion)', () => {
    // CR = avg = 1.90%, achievable = 2.80%
    // loss = (0.028 - 0.019) × 1000 × 100 = 900.00
    const result = calculateDollarLossPerThousand(makeCategoryScores(65), 100, 'fashion');
    expect(result).toBe(900);
  });

  it('score 100 → CR = achievable (fashion), $0 loss', () => {
    const result = calculateDollarLossPerThousand(makeCategoryScores(100), 50, 'fashion');
    expect(result).toBe(0);
  });

  it('score 32.5 (lower-segment midpoint) → midpoint between floor and avg', () => {
    // CR = (0.50 + 1.90) / 2 = 1.20%
    // loss = (0.028 - 0.012) × 1000 × 100 = 1600.00
    const result = calculateDollarLossPerThousand(makeCategoryScores(32.5), 100, 'fashion');
    expect(result).toBe(1600);
  });

  it('score 82.5 (upper-segment midpoint) → midpoint between avg and achievable', () => {
    // CR = (1.90 + 2.80) / 2 = 2.35%
    // loss = (0.028 - 0.0235) × 1000 × 100 = 450.00
    const result = calculateDollarLossPerThousand(makeCategoryScores(82.5), 100, 'fashion');
    expect(result).toBe(450);
  });
});

/* ══════════════════════════════════════════════════════════════
   calculateDollarLossPerThousand — dollar computation
   ══════════════════════════════════════════════════════════════ */

describe('calculateDollarLossPerThousand', () => {
  it('all scores 100 (perfect), price $50, "fashion" → $0', () => {
    expect(calculateDollarLossPerThousand(makeCategoryScores(100), 50, 'fashion')).toBe(0);
  });

  it('all scores 0, price $50, "fashion" → $1150.00', () => {
    // achievableCR = 0.028, estimatedCR = 0.005 (floor)
    // loss = (0.028 - 0.005) × 1000 × 50 = 1150.00
    expect(calculateDollarLossPerThousand(makeCategoryScores(0), 50, 'fashion')).toBe(1150);
  });

  it('all scores 65, price $100, "electronics" → $800.00', () => {
    // achievableCR = 0.020, estimatedCR = 0.012 (avg)
    // loss = (0.020 - 0.012) × 1000 × 100 = 800.00
    expect(calculateDollarLossPerThousand(makeCategoryScores(65), 100, 'electronics')).toBe(800);
  });

  it('result is always >= 0 across score range', () => {
    for (const score of [0, 25, 50, 75, 100]) {
      const result = calculateDollarLossPerThousand(makeCategoryScores(score), 100, 'fashion');
      expect(result, `score=${score}`).toBeGreaterThanOrEqual(0);
    }
  });

  it('result is rounded to at most 2 decimal places', () => {
    // Use an input that's likely to produce fractional cents
    const result = calculateDollarLossPerThousand(makeCategoryScores(33), 77, 'food');
    const decimalPart = result.toString().split('.')[1] ?? '';
    expect(decimalPart.length).toBeLessThanOrEqual(2);
  });
});

/* ══════════════════════════════════════════════════════════════
   Edge cases
   ══════════════════════════════════════════════════════════════ */

describe('calculateDollarLossPerThousand edge cases', () => {
  it('productPrice = 0 → returns 0 (R031)', () => {
    expect(calculateDollarLossPerThousand(makeCategoryScores(50), 0, 'fashion')).toBe(0);
  });

  it('productPrice = -10 → returns 0 (R031)', () => {
    expect(calculateDollarLossPerThousand(makeCategoryScores(50), -10, 'fashion')).toBe(0);
  });

  it('unknown category "nonexistent" falls back to "other" benchmarks', () => {
    const withUnknown = calculateDollarLossPerThousand(makeCategoryScores(50), 100, 'nonexistent');
    const withOther = calculateDollarLossPerThousand(makeCategoryScores(50), 100, 'other');
    expect(withUnknown).toBe(withOther);
    expect(withUnknown).toBeGreaterThan(0);
    expect(Number.isFinite(withUnknown)).toBe(true);
  });

  it('all scores < 0 → clamps to 0, same result as score 0', () => {
    const negative = calculateDollarLossPerThousand(makeCategoryScores(-50), 100, 'fashion');
    const zero = calculateDollarLossPerThousand(makeCategoryScores(0), 100, 'fashion');
    expect(negative).toBe(zero);
    expect(negative).toBeGreaterThan(0);
  });

  it('all scores > 100 → clamps to 100, returns $0 (perfect = no loss)', () => {
    const result = calculateDollarLossPerThousand(makeCategoryScores(150), 100, 'fashion');
    expect(result).toBe(0);
  });
});

/* ══════════════════════════════════════════════════════════════
   All categories produce sensible results
   ══════════════════════════════════════════════════════════════ */

describe('all categories produce sensible results', () => {
  const allCategories = Object.keys(CATEGORY_BENCHMARKS);

  it('all 8 categories with scores 50, price $100 → positive loss', () => {
    for (const cat of allCategories) {
      const result = calculateDollarLossPerThousand(makeCategoryScores(50), 100, cat);
      expect(result, `${cat} should be positive`).toBeGreaterThan(0);
    }
  });

  it('no category produces NaN or Infinity at any score', () => {
    for (const cat of allCategories) {
      for (const score of [0, 25, 50, 75, 100]) {
        const result = calculateDollarLossPerThousand(makeCategoryScores(score), 100, cat);
        expect(Number.isNaN(result), `${cat} score=${score} NaN`).toBe(false);
        expect(Number.isFinite(result), `${cat} score=${score} Infinite`).toBe(true);
      }
    }
  });
});
