import { auth } from "@/auth";

export const proxy = auth((req) => {
  if (!req.auth && req.nextUrl.pathname.startsWith("/dashboard")) {
    return Response.redirect(new URL("/", req.nextUrl.origin));
  }
});
