"use client";

import { ArrowSquareOutIcon } from "@phosphor-icons/react";
import type { AccessibilityRule } from "@/lib/analysis/types";
import { SEVERITY_LABEL, severityColors, severityFor } from "./severity";

/* ══════════════════════════════════════════════════════════════
   RuleList / RuleRow — long-tail axe-core violations rendered
   inside the accessibility check disclosure drawer. Each rule
   row is clickable (when a safe deque-university URL is present)
   and shows severity + occurrence count.
   ══════════════════════════════════════════════════════════════ */

export function impactToWeight(impact: string): number {
  switch (impact) {
    case "critical":
      return 15;
    case "serious":
      return 8;
    case "moderate":
      return 4;
    case "minor":
      return 2;
    default:
      return 4;
  }
}

/** Allow only the canonical axe-core docs host (defends against any
 * upstream payload mutation that could inject a phishing URL). */
export function isSafeAxeUrl(url: string): boolean {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    return (
      parsed.protocol === "https:" &&
      parsed.hostname === "dequeuniversity.com"
    );
  } catch {
    return false;
  }
}

export function RuleList({ rules }: { rules: AccessibilityRule[] }) {
  return (
    <ul className="flex flex-col gap-2 list-none p-0">
      {rules.map((rule) => (
        <RuleRow key={rule.id} rule={rule} />
      ))}
    </ul>
  );
}

function RuleRow({ rule }: { rule: AccessibilityRule }) {
  const severity = severityFor(impactToWeight(rule.impact));
  const sev = severityColors(severity);
  const safeUrl = isSafeAxeUrl(rule.helpUrl) ? rule.helpUrl : null;
  const summary = rule.help || "Accessibility issue detected";
  const places = rule.nodeCount === 1 ? "place" : "places";

  const inner = (
    <>
      <div className="flex-1 min-w-0">
        <p
          className="text-[13px] leading-[1.45] font-medium"
          style={{ color: "var(--ink)" }}
        >
          {summary}
        </p>
        <div
          className="flex items-center gap-2 mt-1.5 flex-wrap text-[11px]"
          style={{ color: "var(--ink-3)" }}
        >
          <span
            className="font-display font-bold text-[10px] px-1.5 py-0.5 rounded"
            style={{
              background: sev.bg,
              color: sev.fg,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
            aria-label={`${SEVERITY_LABEL[severity]} severity`}
          >
            {SEVERITY_LABEL[severity]}
          </span>
          <span className="tabular-nums">
            Found in {rule.nodeCount} {places}
          </span>
          {safeUrl && (
            <span className="font-medium" style={{ color: "var(--ink-2)" }}>
              See how to fix this →
            </span>
          )}
        </div>
      </div>
      {safeUrl && (
        <ArrowSquareOutIcon
          size={14}
          weight="bold"
          color="var(--ink-3)"
          className="shrink-0 mt-1"
          aria-hidden
        />
      )}
    </>
  );

  // Rule ID stays available as a tooltip/aria for power users (axe-core
  // contributors, devs reviewing) without leaking jargon into the
  // primary display for non-technical store owners.
  const accessibleHint = `${summary}. Affects ${rule.nodeCount} ${places}. (Reference: ${rule.id})`;

  return (
    <li
      className="rounded-[10px] border"
      style={{
        background: "var(--paper)",
        borderColor: "var(--rule-2)",
      }}
    >
      {safeUrl ? (
        <a
          href={safeUrl}
          target="_blank"
          rel="noopener noreferrer"
          title={accessibleHint}
          aria-label={accessibleHint}
          className="flex items-start gap-3 px-3 py-2.5 transition-colors hover:bg-[var(--bg-elev)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ink)]/30 rounded-[10px]"
        >
          {inner}
        </a>
      ) : (
        <div
          className="flex items-start gap-3 px-3 py-2.5"
          title={accessibleHint}
        >
          {inner}
        </div>
      )}
    </li>
  );
}
