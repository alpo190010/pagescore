/**
 * Central API base URL derived from NEXT_PUBLIC_API_URL.
 *
 * In development this typically points to http://localhost:8000 (FastAPI).
 * In production it points to the deployed FastAPI origin.
 *
 * Falls back to "" (empty string) so relative fetches still work during
 * local-only development if the env var is unset — but that path is
 * intentionally unsupported in the repointed architecture.
 */
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ?? "";
