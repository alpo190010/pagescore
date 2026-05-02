"use client";

import { useState } from "react";
import {
  CaretDownIcon,
  CheckCircleIcon,
  XCircleIcon,
} from "@phosphor-icons/react";
import type { DimensionCheck } from "@/lib/analysis/types";
import PageSpeedScorecard from "@/components/analysis/PageSpeedScorecard";
import InlineCodeSnippet from "./InlineCodeSnippet";
import { RuleList } from "./RuleList";
import { SEVERITY_LABEL, severityColors, severityFor } from "./severity";

/* ══════════════════════════════════════════════════════════════
   CheckRow — one item inside a ChecksGroup list. Pass rows are
   simple labelled items. Fail rows carry a severity badge and
   become expandable disclosures when remediation, code, rules,
   or a Page Speed scorecard payload is attached.
   ══════════════════════════════════════════════════════════════ */

interface CheckRowProps {
  item: DimensionCheck;
  tone: "pass" | "fail";
  isLast: boolean;
}

export default function CheckRow({ item, tone, isLast }: CheckRowProps) {
  const iconColor =
    tone === "pass" ? "var(--success-text)" : "var(--error-text)";
  const labelColor = tone === "pass" ? "var(--ink-2)" : "var(--ink)";
  const labelWeight = tone === "pass" ? 500 : 600;
  const severity = severityFor(item.weight);
  const sevColors = severityColors(severity);

  // Failing rows with a remediation, code snippet, rule list, or
  // attached PageSpeed scorecard become expandable disclosures.
  const expandable =
    tone === "fail" &&
    Boolean(
      item.remediation ||
        item.code ||
        (item.rules && item.rules.length) ||
        item.pageSpeedSignals,
    );
  const [open, setOpen] = useState(false);

  const rowContent = (
    <>
      <span className="shrink-0 mt-0.5" aria-hidden>
        {tone === "pass" ? (
          <CheckCircleIcon size={18} weight="fill" color={iconColor} />
        ) : (
          <XCircleIcon size={18} weight="fill" color={iconColor} />
        )}
      </span>
      <div className="flex-1 min-w-0 text-left">
        <div
          className="text-[13.5px] leading-[1.4]"
          style={{ color: labelColor, fontWeight: labelWeight }}
        >
          {item.label}
        </div>
        {item.detail && (
          <p
            className="text-[12px] leading-[1.45] mt-0.5"
            style={{ color: "var(--ink-3)" }}
          >
            {item.detail}
          </p>
        )}
      </div>
      {tone === "fail" && (
        <span
          className="shrink-0 font-mono font-bold text-[10px] px-2 py-0.5 rounded-md"
          style={{
            background: sevColors.bg,
            color: sevColors.fg,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
          aria-label={`${SEVERITY_LABEL[severity]} severity`}
        >
          {SEVERITY_LABEL[severity]}
        </span>
      )}
      {expandable && (
        <span
          className="shrink-0 mt-1"
          style={{
            color: "var(--ink-3)",
            transition: "transform 180ms var(--ease-out-quart)",
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
          }}
          aria-hidden
        >
          <CaretDownIcon size={14} weight="bold" />
        </span>
      )}
    </>
  );

  return (
    <li
      style={{
        borderBottom: isLast ? "none" : "1px solid var(--rule-2)",
      }}
    >
      {expandable ? (
        <button
          type="button"
          className="w-full flex items-start gap-3 px-4 py-3 cursor-pointer"
          style={{
            background: "transparent",
            border: "none",
          }}
          aria-expanded={open}
          aria-controls={`check-${item.id}-remediation`}
          onClick={() => setOpen((v) => !v)}
        >
          {rowContent}
        </button>
      ) : (
        <div className="flex items-start gap-3 px-4 py-3">{rowContent}</div>
      )}
      {expandable && open && (
        <div
          id={`check-${item.id}-remediation`}
          className="pl-[41px] pr-4 py-3 text-[13px] leading-[1.55] flex flex-col gap-3"
          style={{
            background: "var(--bg-elev)",
            color: "var(--ink-2)",
            borderTop: "1px solid var(--rule-2)",
            animation: "fade-in-up 200ms var(--ease-out-quart) both",
          }}
        >
          {item.pageSpeedSignals && (
            <PageSpeedScorecard signals={item.pageSpeedSignals} />
          )}
          {item.remediation && <div>{item.remediation}</div>}
          {item.rules && item.rules.length > 0 && (
            <RuleList rules={item.rules} />
          )}
          {item.code && <InlineCodeSnippet code={item.code} />}
        </div>
      )}
    </li>
  );
}
