/* ══════════════════════════════════════════════════════════════
   Severity ladder shared by storewide and per-product check rows.
   Critical / Major / Minor classification + token-aware colours.
   Pure module — no React, no JSX.
   ══════════════════════════════════════════════════════════════ */

export type Severity = "critical" | "major" | "minor";

export function severityFor(weight: number): Severity {
  if (weight >= 15) return "critical";
  if (weight >= 7) return "major";
  return "minor";
}

export const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  major: "Major",
  minor: "Minor",
};

export function severityColors(severity: Severity): { bg: string; fg: string } {
  switch (severity) {
    case "critical":
      return { bg: "var(--error-light)", fg: "var(--error-text)" };
    case "major":
      return { bg: "var(--warning-light)", fg: "var(--warning-text)" };
    case "minor":
      return { bg: "var(--bg-elev)", fg: "var(--ink-3)" };
  }
}
