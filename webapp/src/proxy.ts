import { auth } from "@/auth";

export const proxy = auth((req) => {
  if (
    !req.auth &&
    (req.nextUrl.pathname.startsWith("/dashboard") ||
      req.nextUrl.pathname.startsWith("/settings"))
  ) {
    return Response.redirect(new URL("/", req.nextUrl.origin));
  }
});
