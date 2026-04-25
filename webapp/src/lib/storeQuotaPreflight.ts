/**
 * Shared pre-flight store-quota check.
 *
 * The HeroForm submit path catches a quota violation BEFORE navigation by
 * calling GET /user/stores and comparing against the target domain. The
 * /analyze and /scan/[domain] pages need the same behaviour for users who
 * arrive via bookmark, history, or shared link — otherwise they hit a
 * 403 error state instead of the polished "Store limit reached" modal.
 *
 * On network or auth errors this returns ``null`` and callers fall
 * through to the server-side gate (which still 403s with the canonical
 * error envelope).
 */

import { authFetch } from "@/lib/auth-fetch";
import { API_URL } from "@/lib/api";

export interface QuotaPreflightExhausted {
  exhausted: true;
  used: number;
  quota: number;
}

export interface QuotaPreflightOk {
  exhausted: false;
  used: number;
  quota: number;
  /** True when the caller already owns the target domain — re-scan is free. */
  alreadyTracked: boolean;
}

export type QuotaPreflightResult = QuotaPreflightExhausted | QuotaPreflightOk;

interface UserStoresResponse {
  stores: Array<{ domain: string }>;
  quota: number;
  used: number;
}

/**
 * Hit GET /user/stores and decide whether *targetDomain* can be scanned.
 *
 * Returns ``null`` on any error so callers can silently fall through to
 * the destination page (which gates server-side as a backup). Anonymous
 * callers also resolve to ``null`` since /user/stores requires auth.
 */
export async function preflightStoreQuota(
  targetDomain: string,
): Promise<QuotaPreflightResult | null> {
  const normalized = targetDomain.toLowerCase();
  try {
    const res = await authFetch(`${API_URL}/user/stores`);
    if (!res.ok) return null;
    const payload = (await res.json()) as UserStoresResponse;
    const alreadyTracked = payload.stores.some(
      (s) => s.domain.toLowerCase() === normalized,
    );
    if (alreadyTracked || payload.used < payload.quota) {
      return {
        exhausted: false,
        used: payload.used,
        quota: payload.quota,
        alreadyTracked,
      };
    }
    return {
      exhausted: true,
      used: payload.used,
      quota: payload.quota,
    };
  } catch {
    return null;
  }
}
