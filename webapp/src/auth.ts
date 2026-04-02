import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import * as jwt from "jsonwebtoken";
import type { JWT } from "@auth/core/jwt";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [Google],
  session: { strategy: "jwt" },
  jwt: {
    async encode({ token, secret }) {
      const signingSecret = Array.isArray(secret) ? secret[0] : secret;
      return jwt.sign(token as object, signingSecret, { algorithm: "HS256" });
    },
    async decode({ token, secret }) {
      if (!token) return null;
      try {
        const signingSecret = Array.isArray(secret) ? secret[0] : secret;
        return jwt.verify(token, signingSecret, {
          algorithms: ["HS256"],
        }) as JWT;
      } catch {
        return null;
      }
    },
  },
  callbacks: {
    jwt({ token, account, profile }) {
      // On initial sign-in, populate token with Google profile fields
      if (account && profile) {
        token.sub = profile.sub ?? undefined;
        token.email = profile.email ?? undefined;
        token.name = profile.name ?? undefined;
        token.picture = profile.picture ?? undefined;
      }
      return token;
    },
    session({ session, token }) {
      // Expose token fields on the session object for client access
      if (session.user) {
        session.user.id = token.sub ?? "";
        session.user.email = token.email ?? "";
        session.user.name = token.name ?? "";
        session.user.image = token.picture as string | undefined;
      }
      return session;
    },
  },
});
