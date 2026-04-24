"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useSyncExternalStore,
} from "react";
import {
  ArrowClockwiseIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  WarningCircleIcon,
} from "@phosphor-icons/react";
import type { StoreAnalysisData } from "@/lib/analysis";
import {
  getRefreshState,
  startRefresh,
  subscribeRefresh,
} from "@/lib/storeHealthRefresh";

/* ══════════════════════════════════════════════════════════════
   StoreHealthRefreshButton — Re-analyzes the current store so the
   user can verify whether a fix worked without leaving the detail
   page. Calls POST /store/{domain}/refresh-analysis (runs all 7
   detectors, ~45–60s; free users rate-limited to 1/min per user,
   paid users unlimited).

   Refresh state is shared across every mount of this component for
   the same domain via the module store in lib/storeHealthRefresh.ts.
   That means navigating between dimensions mid-flight keeps the
   "Re-analyzing…" state alive instead of resetting to idle.

   States: idle → loading → success → idle (auto after 2.5s).
   On 429 or network error: loading → error → idle (auto after 6s).
   On success: the module holds the result briefly; the mounted
   parent's onRefreshed is invoked once to update storeAnalysis.
   ══════════════════════════════════════════════════════════════ */

interface StoreHealthRefreshButtonProps {
  domain: string;
  /** Dimension key (e.g. "checkout", "pageSpeed"). Scopes refresh state + backend call. */
  dimensionKey: string;
  dimensionLabel: string;
  onRefreshed: (updated: StoreAnalysisData) => void;
  /**
   * "card" (default) — standalone card with a heading.
   * "inline" — just the button + status text, for embedding.
   * "step-item" — a full <li><button> styled to match a FixSteps step card,
   *               where the whole row is the click target.
   */
  variant?: "card" | "inline" | "step-item";
  /** Required when variant="step-item". Two-digit step number like "05". */
  stepNumber?: string;
}

export default function StoreHealthRefreshButton({
  domain,
  dimensionKey,
  dimensionLabel,
  onRefreshed,
  variant = "card",
  stepNumber,
}: StoreHealthRefreshButtonProps) {
  // Subscribe to the shared refresh state for this (domain, dimensionKey).
  // Each dimension has an independent refresh lifecycle — clicking
  // "Re-analyze Shipping" doesn't affect the Checkout button state.
  const getSnapshot = useCallback(
    () => getRefreshState(domain, dimensionKey),
    [domain, dimensionKey],
  );
  const subscribe = useCallback(
    (cb: () => void) => subscribeRefresh(domain, dimensionKey, cb),
    [domain, dimensionKey],
  );
  const state = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const status = state.status;

  // Always invoke the latest onRefreshed without re-triggering the
  // success effect — keeps dependency array clean.
  const onRefreshedRef = useRef(onRefreshed);
  useEffect(() => {
    onRefreshedRef.current = onRefreshed;
  }, [onRefreshed]);

  // When the module transitions to success with a payload, propagate
  // it to the parent. Idempotent: two mounts firing this for the same
  // data produce the same storeAnalysis state.
  useEffect(() => {
    if (state.status.kind === "success" && state.data) {
      onRefreshedRef.current(state.data);
    }
  }, [state.status.kind, state.data]);

  const handleClick = useCallback(() => {
    if (status.kind === "loading") return;
    startRefresh(domain, dimensionKey);
  }, [domain, dimensionKey, status.kind]);

  const controls = (
    <div className="flex items-center gap-3 flex-wrap">
      <button
        type="button"
        onClick={handleClick}
        disabled={status.kind === "loading"}
        aria-busy={status.kind === "loading"}
        className="inline-flex items-center gap-2 font-display font-bold text-[13px] px-4 py-2.5 rounded-[10px] transition-opacity"
        style={{
          background: "var(--ink)",
          color: "var(--paper)",
          opacity: status.kind === "loading" ? 0.7 : 1,
          cursor: status.kind === "loading" ? "progress" : "pointer",
        }}
      >
        <ArrowClockwiseIcon
          size={14}
          weight="bold"
          className={status.kind === "loading" ? "animate-spin" : ""}
        />
        {status.kind === "loading"
          ? "Re-analyzing…"
          : `Re-analyze ${dimensionLabel}`}
      </button>
      {status.kind === "loading" && (
        <span className="text-[12px]" style={{ color: "var(--ink-3)" }}>
          This takes about a minute.
        </span>
      )}
      {status.kind === "success" && (
        <span
          className="inline-flex items-center gap-1.5 text-[12px] font-semibold"
          style={{ color: "var(--success-text)" }}
        >
          <CheckCircleIcon size={14} weight="fill" />
          Updated just now
        </span>
      )}
      {status.kind === "error" && (
        <span
          className="inline-flex items-center gap-1.5 text-[12px]"
          style={{ color: "var(--error-text)" }}
        >
          <WarningCircleIcon size={14} weight="fill" />
          {status.message}
        </span>
      )}
    </div>
  );

  if (variant === "inline") return controls;

  if (variant === "step-item") {
    const isLoading = status.kind === "loading";
    return (
      <li className="list-none">
        <button
          type="button"
          onClick={handleClick}
          disabled={isLoading}
          aria-busy={isLoading}
          className="group flex items-center gap-3 rounded-[12px] px-3.5 py-3 w-full text-left transition-all"
          style={{
            background: "var(--ink)",
            color: "var(--paper)",
            border: "1px solid var(--ink)",
            cursor: isLoading ? "progress" : "pointer",
            boxShadow: "0 2px 10px color-mix(in srgb, var(--ink) 18%, transparent)",
          }}
          onMouseEnter={(e) => {
            if (!isLoading) e.currentTarget.style.transform = "translateY(-1px)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "translateY(0)";
          }}
        >
          <span
            className="shrink-0 inline-flex items-center justify-center w-[22px] h-[22px] rounded-md font-mono text-[11px] font-bold"
            style={{
              background: "var(--paper)",
              color: "var(--ink)",
              lineHeight: 1,
            }}
          >
            {stepNumber ?? ""}
          </span>
          <ArrowClockwiseIcon
            size={16}
            weight="bold"
            color="var(--paper)"
            className={isLoading ? "animate-spin" : ""}
          />
          <span
            className="font-display text-[14px] leading-[1.4] font-bold flex-1 min-w-0 truncate"
            style={{ color: "var(--paper)", letterSpacing: "-0.01em" }}
          >
            {isLoading ? "Re-analyzing…" : `Re-analyze ${dimensionLabel}`}
          </span>
          {status.kind === "idle" && (
            <ArrowRightIcon
              size={14}
              weight="bold"
              color="var(--paper)"
              className="shrink-0 transition-transform group-hover:translate-x-0.5"
              style={{ opacity: 0.7 }}
            />
          )}
          {status.kind === "loading" && (
            <span
              className="shrink-0 text-[11px] hidden sm:inline"
              style={{ color: "var(--paper)", opacity: 0.7 }}
            >
              ~1 min
            </span>
          )}
          {status.kind === "success" && (
            <span
              className="shrink-0 inline-flex items-center gap-1 text-[12px] font-semibold font-mono uppercase px-2 py-0.5 rounded-md"
              style={{
                background: "var(--paper)",
                color: "var(--success-text)",
                letterSpacing: "0.05em",
              }}
            >
              <CheckCircleIcon size={12} weight="fill" />
              Updated
            </span>
          )}
          {status.kind === "error" && (
            <span
              className="shrink-0 inline-flex items-center gap-1 text-[11px] font-semibold font-mono uppercase px-2 py-0.5 rounded-md"
              style={{
                background: "var(--paper)",
                color: "var(--error-text)",
                letterSpacing: "0.05em",
              }}
            >
              <WarningCircleIcon size={12} weight="fill" />
              Retry
            </span>
          )}
        </button>
      </li>
    );
  }

  return (
    <section
      className="rounded-[14px] border px-5 py-4 flex flex-col gap-2.5"
      style={{
        background: "var(--paper)",
        borderColor: "var(--rule-2)",
      }}
    >
      <div
        className="font-mono text-[10px] font-bold uppercase"
        style={{ color: "var(--ink-3)", letterSpacing: "0.14em" }}
      >
        Finished applying the fix?
      </div>
      {controls}
    </section>
  );
}
