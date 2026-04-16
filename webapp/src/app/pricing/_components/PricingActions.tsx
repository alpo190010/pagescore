"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import dynamic from "next/dynamic";
import Link from "next/link";
import Button from "@/components/ui/Button";
import { authFetch } from "@/lib/auth-fetch";
import { API_URL } from "@/lib/api";

const AuthModal = dynamic(() => import("@/components/AuthModal"), {
  ssr: false,
});

/* -- Props -- */
interface PricingActionsProps {
  tier: {
    key: string;
    ctaLabel: string;
  };
}

/**
 * Client island for a single pricing tier CTA.
 * Free tier: static link to homepage.
 * Pro waitlist: auth-gated confirmation wired to backend POST /user/waitlist.
 */
export default function PricingActions({ tier }: PricingActionsProps) {
  const { data: session } = useSession();
  const isSignedIn = !!session?.user;

  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [waitlistConfirmed, setWaitlistConfirmed] = useState(false);
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState(false);
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // On mount: check /user/plan for existing waitlist status (D-06)
  useEffect(() => {
    if (tier.key !== "pro-waitlist" || !isSignedIn) return;
    authFetch(`${API_URL}/user/plan`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d?.proWaitlist) setWaitlistConfirmed(true);
      })
      .catch(() => {});
  }, [tier.key, isSignedIn]);

  // On mount: auto-enroll when redirected back with ?waitlist=1 after signup (D-09)
  useEffect(() => {
    if (tier.key !== "pro-waitlist" || !isSignedIn) return;
    if (searchParams.get("waitlist") !== "1") return;
    authFetch(`${API_URL}/user/waitlist`, { method: "POST" })
      .then((r) => {
        if (r.ok) {
          setWaitlistConfirmed(true);
          router.replace(pathname, { scroll: false });
        }
      })
      .catch(() => {});
  }, [isSignedIn, searchParams, pathname, router, tier.key]);

  return (
    <>
      {tier.key === "free" ? (
        /* Free tier -- link to homepage (per D-03) */
        <Button
          asChild
          variant="secondary"
          size="md"
          shape="pill"
          className="w-full text-center"
        >
          <Link href="/">{tier.ctaLabel}</Link>
        </Button>
      ) : waitlistConfirmed ? (
        /* Authenticated user confirmed waitlist -- show inline message */
        <p
          role="status"
          className="text-sm text-center font-semibold py-3 text-[var(--success)] animate-[fade-in_300ms_ease-out]"
        >
          You&apos;re on the list! We&apos;ll let you know when Pro launches.
        </p>
      ) : (
        /* Pro waitlist -- auth gate (per D-07) */
        <>
          <Button
            type="button"
            variant="secondary"
            size="md"
            shape="pill"
            disabled={joining}
            aria-busy={joining}
            onClick={() => {
              if (!isSignedIn) {
                setAuthModalOpen(true);
                return;
              }
              setJoining(true);
              setJoinError(false);
              authFetch(`${API_URL}/user/waitlist`, { method: "POST" })
                .then((r) => {
                  if (r.ok) setWaitlistConfirmed(true);
                  else setJoinError(true);
                })
                .catch(() => setJoinError(true))
                .finally(() => setJoining(false));
            }}
            className={`w-full px-8 border border-[var(--outline-variant)] text-[var(--on-surface-variant)] ${joining ? "opacity-50" : ""}`}
          >
            {tier.ctaLabel}
          </Button>
          {joinError && (
            <p className="text-xs text-center mt-2 text-[var(--error-base)]">
              Something went wrong. Please try again.
            </p>
          )}
        </>
      )}

      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        callbackUrl="/pricing?waitlist=1"
      />
    </>
  );
}
