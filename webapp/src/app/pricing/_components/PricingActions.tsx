"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import dynamic from "next/dynamic";
import Link from "next/link";
import Button from "@/components/ui/Button";
import { isPaddleConfigured, openMembershipCheckout } from "@/lib/paddle";

const AuthModal = dynamic(() => import("@/components/AuthModal"), {
  ssr: false,
});

/* -- Props -- */
interface PricingActionsProps {
  tier: {
    key: "free" | "membership";
    ctaLabel: string;
    /** True when this card matches the authenticated user's current plan. */
    isCurrent: boolean;
  };
}

function CurrentPlanLabel() {
  return (
    <div
      className="w-full text-center py-3 text-sm font-semibold rounded-full border"
      style={{
        background: "var(--surface-container-low)",
        color: "var(--on-surface-variant)",
        borderColor: "var(--outline-variant)",
      }}
      role="status"
    >
      Current plan
    </div>
  );
}

export default function PricingActions({ tier }: PricingActionsProps) {
  const { data: session } = useSession();
  const isSignedIn = !!session?.user;

  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [checkoutBusy, setCheckoutBusy] = useState(false);

  // ── Free tier: link to scan ──
  if (tier.key === "free") {
    if (tier.isCurrent) return <CurrentPlanLabel />;
    return (
      <Button
        asChild
        variant="secondary"
        size="md"
        shape="pill"
        className="w-full text-center"
      >
        <Link href="/">{tier.ctaLabel}</Link>
      </Button>
    );
  }

  // ── Membership: Paddle inline checkout ($79 / year) ──
  if (tier.isCurrent) return <CurrentPlanLabel />;

  const configured = isPaddleConfigured();

  const onClick = async () => {
    if (!isSignedIn) {
      setAuthModalOpen(true);
      return;
    }
    const userId = session?.user?.id;
    if (!userId) return;
    setCheckoutBusy(true);
    try {
      const opened = await openMembershipCheckout({
        userId,
        email: session?.user?.email ?? undefined,
      });
      if (!opened) {
        console.error(
          "Paddle checkout failed to open — env vars missing or SDK failed to load",
        );
      }
    } finally {
      setCheckoutBusy(false);
    }
  };

  return (
    <>
      <Button
        type="button"
        variant="primary"
        size="md"
        shape="pill"
        className="w-full"
        onClick={onClick}
        disabled={!configured || checkoutBusy}
        aria-busy={checkoutBusy}
        aria-disabled={!configured}
      >
        {checkoutBusy ? "Opening…" : tier.ctaLabel}
      </Button>
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode="signup"
        heading="Create your account to join"
        subheading="You'll land on the checkout right after signup."
        callbackUrl="/pricing"
      />
    </>
  );
}
