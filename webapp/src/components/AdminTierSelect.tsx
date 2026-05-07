"use client";

import { useState } from "react";
import { authFetch } from "@/lib/auth-fetch";
import { API_URL } from "@/lib/api";

type AdminTier = "free" | "insights" | "fixes";

interface AdminTierSelectProps {
  userId: string;
  storeDomain: string;
  currentTier: string;
  /** Called after the backend confirms the new tier so the parent can refetch. */
  onSuccess: () => void | Promise<void>;
}

/**
 * Inline admin-only tier selector. Posts directly to the admin store-subscription
 * endpoint, bypassing Paddle. Reverts to the previous value and surfaces an
 * inline error when the request fails.
 */
export default function AdminTierSelect({
  userId,
  storeDomain,
  currentTier,
  onSuccess,
}: AdminTierSelectProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isPaid = currentTier === "insights" || currentTier === "fixes";

  async function handleChange(nextTier: AdminTier) {
    if (nextTier === currentTier) return;
    setError(null);
    setBusy(true);
    try {
      const res = await authFetch(
        `${API_URL}/admin/users/${userId}/store-subscriptions`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            store_domain: storeDomain,
            plan_tier: nextTier,
          }),
        },
      );
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setError(
          (data && (data.detail || data.error)) || "Failed to update plan.",
        );
        return;
      }
      await onSuccess();
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="inline-flex flex-col items-start gap-1">
      <select
        aria-label={`Change plan for ${storeDomain}`}
        value={currentTier}
        onChange={(e) => handleChange(e.target.value as AdminTier)}
        disabled={busy}
        className="text-xs font-bold uppercase tracking-wide px-2 py-0.5 rounded-full polish-focus-ring outline-none cursor-pointer disabled:cursor-wait disabled:opacity-60"
        style={{
          background: isPaid
            ? "var(--brand-light)"
            : "var(--surface-container-high)",
          color: isPaid ? "var(--brand)" : "var(--on-surface-variant)",
          border: "1px solid var(--border)",
        }}
      >
        <option value="free">Free</option>
        <option value="insights">Insights</option>
        <option value="fixes">Fixes</option>
      </select>
      {busy && (
        <span className="text-[10px] text-[var(--text-tertiary)]">
          Saving…
        </span>
      )}
      {error && (
        <span
          role="alert"
          className="text-[10px] text-[var(--error)] max-w-[200px] break-words"
        >
          {error}
        </span>
      )}
    </span>
  );
}
