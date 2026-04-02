import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";

/**
 * GET /api/auth/token
 *
 * Returns the raw JWT session cookie so client-side code can forward it
 * as a Bearer token to the FastAPI backend.
 *
 * - If no session exists → { token: null }
 * - If session exists → { token: "<jwt>" }
 */
export async function GET(request: NextRequest) {
  const session = await auth();

  if (!session) {
    return NextResponse.json({ token: null });
  }

  // Auth.js stores the JWT in a cookie. Try the plain name first,
  // then the __Secure- prefixed variant used in production (HTTPS).
  const cookieName =
    request.cookies.get("authjs.session-token")?.value
      ? "authjs.session-token"
      : "__Secure-authjs.session-token";

  const token = request.cookies.get(cookieName)?.value ?? null;

  return NextResponse.json({ token });
}
