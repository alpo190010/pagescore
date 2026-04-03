"use client";

import { useState, useEffect, useCallback } from "react";
import { authFetch } from "@/lib/auth-fetch";
import { API_URL } from "@/lib/api";

/* ══════════════════════════════════════════════════════════════
   /admin — Platform analytics dashboard
   Stat cards, CSS bar charts, plan distribution.
   Protected by proxy.ts admin route guard (S01).
   ══════════════════════════════════════════════════════════════ */

interface AnalyticsData {
  total_users: number;
  signups_over_time: { date: string; count: number }[];
  total_scans: number;
  scans_over_time: { date: string; count: number }[];
  plan_distribution: { plan_tier: string; count: number }[];
  total_credits_used: number;
}

/** Format a large number with locale grouping (e.g. 1,234) */
function fmtNum(n: number): string {
  return n.toLocaleString("en-US");
}

/** Abbreviate an ISO date to "Apr 1" style */
function fmtDate(iso: string): string {
  try {
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

/** Color token for plan tier badges — matches users/page.tsx */
function planBadgeStyle(tier: string): React.CSSProperties {
  switch (tier) {
    case "pro":
      return { background: "var(--brand)", color: "var(--brand-light)" };
    case "growth":
      return { background: "var(--success)", color: "#fff" };
    case "starter":
      return {
        background: "var(--surface-container-high)",
        color: "var(--text-primary)",
      };
    default:
      return {
        background: "var(--surface-container)",
        color: "var(--text-secondary)",
      };
  }
}

export default function AdminDashboardPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch(`${API_URL}/admin/analytics`);
      if (!res.ok) throw new Error(`Failed to load analytics (${res.status})`);
      const json: AnalyticsData = await res.json();
      setData(json);
    } catch {
      setError("Failed to load analytics. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  return (
    <div>
      <h1
        className="text-2xl font-extrabold text-[var(--on-surface)] tracking-tight mb-6"
        style={{ fontFamily: "var(--font-manrope), Manrope, sans-serif" }}
      >
        Dashboard
      </h1>

      {/* Error state */}
      {error && (
        <div
          className="text-center py-12 rounded-2xl border border-[var(--outline-variant)]"
          style={{ background: "var(--surface-container-lowest)" }}
        >
          <p
            className="text-sm text-[var(--error)] font-medium mb-4"
            role="alert"
          >
            {error}
          </p>
          <button
            type="button"
            onClick={fetchAnalytics}
            className="px-6 py-2 rounded-xl text-sm font-semibold text-white cursor-pointer"
            style={{ background: "var(--brand)" }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !error && (
        <div className="space-y-6">
          {/* Skeleton stat cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-28 rounded-xl animate-pulse"
                style={{ background: "var(--surface-container-low)" }}
              />
            ))}
          </div>
          {/* Skeleton chart areas */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="h-56 rounded-xl animate-pulse"
                style={{ background: "var(--surface-container-low)" }}
              />
            ))}
          </div>
          {/* Skeleton plan distribution */}
          <div
            className="h-32 rounded-xl animate-pulse"
            style={{ background: "var(--surface-container-low)" }}
          />
        </div>
      )}

      {/* Dashboard content */}
      {!loading && !error && data && (
        <div className="space-y-6">
          {/* ── Stat cards ── */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard label="Total Users" value={fmtNum(data.total_users)} />
            <StatCard label="Total Scans" value={fmtNum(data.total_scans)} />
            <StatCard
              label="Credits Used"
              value={fmtNum(data.total_credits_used)}
            />
          </div>

          {/* ── Bar charts ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <BarChart
              title="Signups (Last 30 Days)"
              data={data.signups_over_time}
              barColor="var(--brand)"
            />
            <BarChart
              title="Scans (Last 30 Days)"
              data={data.scans_over_time}
              barColor="var(--success)"
            />
          </div>

          {/* ── Plan distribution ── */}
          <div
            className="rounded-xl border border-[var(--border)] p-5"
            style={{ background: "var(--surface-container-lowest)" }}
          >
            <h2 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">
              Plan Distribution
            </h2>

            {data.plan_distribution.length === 0 ? (
              <p className="text-sm text-[var(--text-secondary)]">
                No plan data yet.
              </p>
            ) : (
              <div className="space-y-3">
                {data.plan_distribution.map((p) => {
                  const maxCount = Math.max(
                    ...data.plan_distribution.map((d) => d.count),
                  );
                  const pct = maxCount > 0 ? (p.count / maxCount) * 100 : 0;
                  return (
                    <div key={p.plan_tier} className="flex items-center gap-3">
                      <span
                        className="inline-block px-2.5 py-0.5 rounded-full text-xs font-bold min-w-[64px] text-center"
                        style={planBadgeStyle(p.plan_tier)}
                      >
                        {p.plan_tier}
                      </span>
                      <div className="flex-1 h-6 rounded-md overflow-hidden bg-[var(--surface-container-low)]">
                        <div
                          className="h-full rounded-md transition-all"
                          style={{
                            width: `${pct}%`,
                            background: planBarColor(p.plan_tier),
                            minWidth: pct > 0 ? "4px" : undefined,
                          }}
                        />
                      </div>
                      <span className="text-sm font-semibold text-[var(--text-primary)] min-w-[32px] text-right tabular-nums">
                        {fmtNum(p.count)}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────── Sub-components ─────────────────────── */

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="rounded-xl border border-[var(--border)] p-5"
      style={{ background: "var(--surface-container-lowest)" }}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)] mb-1">
        {label}
      </p>
      <p className="text-3xl font-extrabold text-[var(--text-primary)] tabular-nums">
        {value}
      </p>
    </div>
  );
}

function BarChart({
  title,
  data,
  barColor,
}: {
  title: string;
  data: { date: string; count: number }[];
  barColor: string;
}) {
  const maxVal = Math.max(...data.map((d) => d.count), 1);

  return (
    <div
      className="rounded-xl border border-[var(--border)] p-5"
      style={{ background: "var(--surface-container-lowest)" }}
    >
      <h2 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">
        {title}
      </h2>

      {data.length === 0 ? (
        <p className="text-sm text-[var(--text-secondary)] py-8 text-center">
          No data yet.
        </p>
      ) : (
        <div className="flex items-end gap-[3px] h-36">
          {data.map((d) => {
            const heightPct = (d.count / maxVal) * 100;
            return (
              <div
                key={d.date}
                className="flex-1 flex flex-col items-center justify-end h-full group"
              >
                {/* Count label — visible on hover */}
                <span className="text-[10px] font-semibold text-[var(--text-secondary)] mb-1 opacity-0 group-hover:opacity-100 transition-opacity tabular-nums">
                  {d.count}
                </span>
                {/* Bar */}
                <div
                  className="w-full rounded-t-sm transition-all"
                  style={{
                    height: `${heightPct}%`,
                    minHeight: d.count > 0 ? "3px" : "1px",
                    background:
                      d.count > 0
                        ? barColor
                        : "var(--surface-container-high)",
                  }}
                />
              </div>
            );
          })}
        </div>
      )}

      {/* X-axis date labels — show first, middle, last to avoid crowding */}
      {data.length > 0 && (
        <div className="flex justify-between mt-2">
          <span className="text-[10px] text-[var(--text-secondary)]">
            {fmtDate(data[0].date)}
          </span>
          {data.length > 2 && (
            <span className="text-[10px] text-[var(--text-secondary)]">
              {fmtDate(data[Math.floor(data.length / 2)].date)}
            </span>
          )}
          {data.length > 1 && (
            <span className="text-[10px] text-[var(--text-secondary)]">
              {fmtDate(data[data.length - 1].date)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/** Map plan tier to a bar fill color */
function planBarColor(tier: string): string {
  switch (tier) {
    case "pro":
      return "var(--brand)";
    case "growth":
      return "var(--success)";
    case "starter":
      return "var(--surface-container-high)";
    default:
      return "var(--surface-container)";
  }
}
