/**
 * Auth-aware fetch helpers.
 *
 * `authFetch` — drop-in fetch replacement that adds `Authorization: Bearer <jwt>`
 * when the user has an active session. Falls through to plain fetch otherwise.
 *
 * `getAuthToken` — resolves to the raw JWT string or null.
 */

export async function getAuthToken(): Promise<string | null> {
  // Impersonation token takes priority (client-side only)
  if (typeof window !== "undefined") {
    const impersonationToken = localStorage.getItem("impersonation_token");
    if (impersonationToken) return impersonationToken;
  }

  // Fall back to Auth.js session cookie
  try {
    const res = await fetch("/api/auth/token");
    if (!res.ok) return null;
    const data = await res.json();
    return data.token ?? null;
  } catch {
    return null;
  }
}

export async function authFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const token = await getAuthToken();

  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(input, { ...init, headers });
}
