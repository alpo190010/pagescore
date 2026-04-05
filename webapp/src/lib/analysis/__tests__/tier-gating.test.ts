import { describe, it, expect } from "vitest";
import { STARTER_DIMENSIONS, getDimensionAccess } from "../conversion-model";
import { ACTIVE_DIMENSIONS } from "../constants";
import type { PlanTier } from "../types";
import type { DimensionAccess } from "../conversion-model";

/* ══════════════════════════════════════════════════════════════
   Tier-Gating Tests (D076)
   ══════════════════════════════════════════════════════════════ */

const EXPECTED_STARTER_KEYS = [
  "socialProof", "images", "checkout", "title", "pricing", "shipping", "trust",
] as const;

const ALL_DIMENSION_KEYS = [...ACTIVE_DIMENSIONS];

describe("STARTER_DIMENSIONS", () => {
  it("contains exactly 7 members", () => {
    expect(STARTER_DIMENSIONS.size).toBe(7);
  });

  it("contains exactly the D076 keys", () => {
    for (const key of EXPECTED_STARTER_KEYS) {
      expect(STARTER_DIMENSIONS.has(key)).toBe(true);
    }
    // No extra keys
    for (const key of STARTER_DIMENSIONS) {
      expect(EXPECTED_STARTER_KEYS).toContain(key);
    }
  });
});

describe("getDimensionAccess", () => {
  describe("free plan", () => {
    it("returns locked for all 18 active dimensions", () => {
      for (const key of ALL_DIMENSION_KEYS) {
        expect(getDimensionAccess("free", key)).toBe("locked" satisfies DimensionAccess);
      }
    });
  });

  describe("starter plan", () => {
    it("returns unlocked for the 7 starter dimensions", () => {
      for (const key of EXPECTED_STARTER_KEYS) {
        expect(getDimensionAccess("starter", key)).toBe("unlocked" satisfies DimensionAccess);
      }
    });

    it("returns locked for the other 11 dimensions", () => {
      const nonStarter = ALL_DIMENSION_KEYS.filter((k) => !STARTER_DIMENSIONS.has(k));
      expect(nonStarter.length).toBe(11);
      for (const key of nonStarter) {
        expect(getDimensionAccess("starter", key)).toBe("locked" satisfies DimensionAccess);
      }
    });
  });

  describe("growth plan", () => {
    it("returns unlocked for all 18 active dimensions", () => {
      for (const key of ALL_DIMENSION_KEYS) {
        expect(getDimensionAccess("growth", key)).toBe("unlocked" satisfies DimensionAccess);
      }
    });
  });

  describe("pro plan", () => {
    it("returns unlocked for all 18 active dimensions", () => {
      for (const key of ALL_DIMENSION_KEYS) {
        expect(getDimensionAccess("pro", key)).toBe("unlocked" satisfies DimensionAccess);
      }
    });
  });

  describe("unknown dimension key", () => {
    it("returns locked for free plan", () => {
      expect(getDimensionAccess("free", "nonexistent")).toBe("locked");
    });

    it("returns locked for starter plan", () => {
      expect(getDimensionAccess("starter", "nonexistent")).toBe("locked");
    });

    it("returns unlocked for growth plan (all dims unlocked)", () => {
      expect(getDimensionAccess("growth", "nonexistent")).toBe("unlocked");
    });

    it("returns unlocked for pro plan (all dims unlocked)", () => {
      expect(getDimensionAccess("pro", "nonexistent")).toBe("unlocked");
    });
  });
});
