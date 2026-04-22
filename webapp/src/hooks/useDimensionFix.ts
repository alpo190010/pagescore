"use client";

import { useEffect, useRef, useState } from "react";
import { API_URL } from "@/lib/api";
import { authFetch } from "@/lib/auth-fetch";
import type { DimensionFix } from "@/lib/analysis";

/**
 * Fetches structured fix content for a single store-wide dimension.
 *
 * Shape mirrors the backend contract at `GET /fix/{dimension_key}`.
 * Free-tier callers receive `locked: true` with empty `steps` and null `code`.
 *
 * Requests for the same key share a module-level cache so re-opening a fix
 * is instant and doesn't re-hit the backend. Changing the key aborts any
 * in-flight request for the previous key.
 */

const fixCache = new Map<string, DimensionFix>();

interface UseDimensionFixResult {
  fix: DimensionFix | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
}

export function useDimensionFix(
  dimensionKey: string | null,
): UseDimensionFixResult {
  const [fix, setFix] = useState<DimensionFix | null>(() =>
    dimensionKey ? fixCache.get(dimensionKey) ?? null : null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!dimensionKey) {
      setFix(null);
      setLoading(false);
      setError(null);
      return;
    }

    const cached = fixCache.get(dimensionKey);
    if (cached) {
      setFix(cached);
      setLoading(false);
      setError(null);
      return;
    }

    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);

    (async () => {
      try {
        const res = await authFetch(
          `${API_URL}/fix/${encodeURIComponent(dimensionKey)}`,
          { signal: controller.signal },
        );
        if (!res.ok) {
          const body = (await res.json().catch(() => ({}))) as {
            detail?: string;
            error?: string;
          };
          throw new Error(
            body.detail || body.error || `Request failed (${res.status})`,
          );
        }
        const data = (await res.json()) as DimensionFix;
        fixCache.set(dimensionKey, data);
        if (!controller.signal.aborted) {
          setFix(data);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Unable to load fix");
        setLoading(false);
      }
    })();

    return () => controller.abort();
  }, [dimensionKey, attempt]);

  return {
    fix,
    loading,
    error,
    retry: () => setAttempt((n) => n + 1),
  };
}
