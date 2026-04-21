import { describe, it, expect } from "vitest";
import { getDimensionAccess } from "../conversion-model";
import { ACTIVE_DIMENSIONS } from "../constants";
import type { DimensionAccess } from "../conversion-model";

/* ══════════════════════════════════════════════════════════════
   Tier-Gating Tests — 3-tier model (free / starter / pro)
   Free tier: scoring only — recommendations locked
   Starter / Pro: full access
   ══════════════════════════════════════════════════════════════ */

const ALL_DIMENSION_KEYS = [...ACTIVE_DIMENSIONS];

describe("getDimensionAccess", () => {
  describe("free plan", () => {
    it("returns locked for all active dimensions", () => {
      for (const key of ALL_DIMENSION_KEYS) {
        expect(getDimensionAccess("free", key)).toBe("locked" satisfies DimensionAccess);
      }
    });

    it("returns locked for unknown dimension keys", () => {
      expect(getDimensionAccess("free", "nonexistent")).toBe("locked");
    });
  });

  describe("starter plan", () => {
    it("returns unlocked for all active dimensions", () => {
      for (const key of ALL_DIMENSION_KEYS) {
        expect(getDimensionAccess("starter", key)).toBe("unlocked" satisfies DimensionAccess);
      }
    });
  });

  describe("pro plan", () => {
    it("returns unlocked for all active dimensions", () => {
      for (const key of ALL_DIMENSION_KEYS) {
        expect(getDimensionAccess("pro", key)).toBe("unlocked" satisfies DimensionAccess);
      }
    });

    it("returns unlocked for unknown dimension keys", () => {
      expect(getDimensionAccess("pro", "nonexistent")).toBe("unlocked");
    });
  });
});
