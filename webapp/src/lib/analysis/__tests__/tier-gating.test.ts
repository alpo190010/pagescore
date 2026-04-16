import { describe, it, expect } from "vitest";
import { getDimensionAccess } from "../conversion-model";
import { ACTIVE_DIMENSIONS } from "../constants";
import type { PlanTier } from "../types";
import type { DimensionAccess } from "../conversion-model";

/* ══════════════════════════════════════════════════════════════
   Tier-Gating Tests — 2-tier model (free / pro)
   ══════════════════════════════════════════════════════════════ */

const ALL_DIMENSION_KEYS = [...ACTIVE_DIMENSIONS];

describe("getDimensionAccess", () => {
  describe("free plan", () => {
    it("returns unlocked for all 18 active dimensions", () => {
      for (const key of ALL_DIMENSION_KEYS) {
        expect(getDimensionAccess("free", key)).toBe("unlocked" satisfies DimensionAccess);
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
    it("returns unlocked for free plan", () => {
      expect(getDimensionAccess("free", "nonexistent")).toBe("unlocked");
    });

    it("returns unlocked for pro plan (all dims unlocked)", () => {
      expect(getDimensionAccess("pro", "nonexistent")).toBe("unlocked");
    });
  });
});
