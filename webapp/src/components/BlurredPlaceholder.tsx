"use client";

import Link from "next/link";
import {
  ArrowRightIcon,
  CheckCircleIcon,
  LockKeyIcon,
  XCircleIcon,
} from "@phosphor-icons/react";
import { meetsRequirement, type PlanTier } from "@/lib/tier";

/**
 * Reusable paywall wrapper for tier-gated content.
 *
 * DOM-safe gating: locked viewers NEVER see the real ``children`` in the
 * DOM. Instead, a synthetic ``placeholder`` (or a generic skeleton) is
 * rendered blurred with the upgrade CTA on top. The strict gate is
 * server-side stripping; this component just makes sure no smuggled
 * children leak past it.
 *
 *   - When the current tier meets the requirement, renders ``children``
 *     unchanged. Zero visual cost.
 *   - When the current tier does NOT meet the requirement, renders the
 *     ``placeholder`` (or default skeleton) blurred with a centered
 *     upgrade CTA layered on top. ``children`` are not rendered.
 */
interface BlurredPlaceholderProps {
  /** Tier required to unlock the children — "insights" or "fixes". */
  requiredTier: PlanTier;
  /** Caller's current tier ("free" | "insights" | "fixes" | null). */
  currentTier?: string | null;
  /** Heading on the upgrade overlay (defaults to a tier-specific string). */
  title?: string;
  /** Subhead on the upgrade overlay. */
  subtitle?: string;
  /** CTA button label. */
  cta?: string;
  /**
   * Synthetic content rendered blurred under the overlay when locked.
   * Should NEVER include real premium data — this is a visual hint of
   * the locked content's shape. Defaults to a generic skeleton.
   */
  placeholder?: React.ReactNode;
  /** Real content rendered when unlocked. NOT rendered when locked. */
  children: React.ReactNode;
}

export default function BlurredPlaceholder({
  requiredTier,
  currentTier,
  title,
  subtitle,
  cta,
  placeholder,
  children,
}: BlurredPlaceholderProps) {
  if (meetsRequirement(currentTier, requiredTier)) {
    return <>{children}</>;
  }

  const heading =
    title ??
    (requiredTier === "insights"
      ? "Unlock detailed analysis"
      : "Unlock the full fix");
  const sub =
    subtitle ??
    (requiredTier === "insights"
      ? "See exactly what's working and what's missing on every product page."
      : "Step-by-step instructions and copy-paste code to repair each issue.");
  const ctaLabel =
    cta ?? (requiredTier === "insights" ? "Get Insights" : "Get Fixes");

  return (
    <div className="relative">
      <div
        aria-hidden
        className="select-none pointer-events-none"
        style={{ filter: "blur(8px)", opacity: 0.55 }}
      >
        {placeholder ?? <DefaultSkeleton />}
      </div>
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <Link
          href="/pricing"
          aria-label={ctaLabel}
          className="group rounded-[14px] border px-5 py-5 flex items-center gap-4 transition-[background,border-color,box-shadow,transform] duration-150 ease-[var(--ease-out-quart)] hover:-translate-y-px focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ink)]/30"
          style={{
            background: "var(--paper)",
            borderColor: "var(--rule-2)",
            boxShadow: "var(--shadow-subtle)",
          }}
        >
          <span
            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
            style={{
              background: "var(--bg-elev)",
              color: "var(--ink-2)",
            }}
          >
            <LockKeyIcon size={18} weight="bold" />
          </span>
          <div className="flex-1 min-w-0">
            <div
              className="font-display font-bold text-[15px] leading-tight"
              style={{ color: "var(--ink)" }}
            >
              {heading}
            </div>
            <p
              className="text-[12.5px] leading-[1.5] mt-1"
              style={{ color: "var(--ink-3)" }}
            >
              {sub}
            </p>
          </div>
          <span
            className="shrink-0 inline-flex items-center gap-1.5 text-[12.5px] font-semibold px-3 py-1.5 rounded-full transition-transform duration-150 group-hover:translate-x-0.5"
            style={{
              background: "var(--ink)",
              color: "var(--paper)",
            }}
            aria-hidden="true"
          >
            {ctaLabel}
            <ArrowRightIcon size={14} weight="bold" />
          </span>
        </Link>
      </div>
    </div>
  );
}

/* ── DefaultSkeleton ──────────────────────────────────────────
   Imitation of the locked diagnostic surface. Renders mock rows
   in their natural red (failing) / green (passing) colors so the
   blurred-behind preview makes the value of the unlock visible.
   No real labels, details, or remediation prose are placed in
   this DOM — only generic gray text bars.
   ─────────────────────────────────────────────────────────── */
function DefaultSkeleton() {
  // Mix of severities and pass/fail states, tuned to look like a
  // typical dimension's "what's missing / what's working" pair.
  const rows: { tone: "fail" | "pass"; severity?: "Critical" | "Major" | "Minor"; widthPct: number }[] = [
    { tone: "fail", severity: "Critical", widthPct: 78 },
    { tone: "fail", severity: "Major", widthPct: 64 },
    { tone: "fail", severity: "Major", widthPct: 71 },
    { tone: "fail", severity: "Minor", widthPct: 58 },
    { tone: "pass", widthPct: 66 },
    { tone: "pass", widthPct: 52 },
  ];

  return (
    <div className="flex flex-col gap-3.5" aria-hidden>
      {/* Severity-chips imitation */}
      <div className="flex items-center gap-2 flex-wrap">
        {[
          { label: "All", n: 8 },
          { label: "Critical", n: 1 },
          { label: "Major", n: 4 },
          { label: "Minor", n: 3 },
        ].map((chip, i) => (
          <span
            key={chip.label}
            className="rounded-full px-3.5 py-1.5 text-[13px] font-semibold"
            style={{
              background: i === 0 ? "var(--ink)" : "transparent",
              color: i === 0 ? "var(--paper)" : "var(--ink-2)",
              border: `1px solid ${i === 0 ? "var(--ink)" : "var(--rule-2)"}`,
            }}
          >
            {chip.label} <span className="tabular-nums opacity-80">{chip.n}</span>
          </span>
        ))}
      </div>

      {/* Check-row imitations */}
      <ul
        className="rounded-[14px] border list-none m-0 p-0 overflow-hidden"
        style={{
          background: "var(--paper)",
          borderColor: "var(--rule-2)",
        }}
      >
        {rows.map((row, i) => (
          <li
            key={i}
            className="flex items-start gap-3 px-4 py-3"
            style={{
              borderBottom:
                i < rows.length - 1 ? "1px solid var(--rule-2)" : "none",
            }}
          >
            <span className="shrink-0 mt-0.5">
              {row.tone === "pass" ? (
                <CheckCircleIcon
                  size={18}
                  weight="fill"
                  color="var(--success-text)"
                />
              ) : (
                <XCircleIcon
                  size={18}
                  weight="fill"
                  color="var(--error-text)"
                />
              )}
            </span>
            <div className="flex-1 min-w-0 flex flex-col gap-1.5">
              <div
                className="rounded h-3.5"
                style={{
                  background: "var(--bg-elev)",
                  width: `${row.widthPct}%`,
                }}
              />
              <div
                className="rounded h-3"
                style={{
                  background: "var(--bg-elev)",
                  width: `${Math.max(40, row.widthPct - 14)}%`,
                }}
              />
            </div>
            {row.severity && (
              <span
                className="shrink-0 font-mono font-bold text-[10px] px-2 py-0.5 rounded-md"
                style={{
                  background:
                    row.severity === "Critical"
                      ? "var(--error-text)"
                      : row.severity === "Major"
                      ? "var(--warning-text)"
                      : "var(--ink-3)",
                  color: "var(--paper)",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                {row.severity}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
