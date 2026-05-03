"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import {
  CheckCircle,
  Sparkle,
  Lightning,
  Star,
  CheckCircle as CheckCircleIcon,
} from "@phosphor-icons/react";
import { authFetch } from "@/lib/auth-fetch";
import { API_URL } from "@/lib/api";
import PricingActions from "./PricingActions";

/** Map the user's persisted plan_tier to the card key used in TIERS.
 *
 * Both legacy Starter subscribers (if any remain) and new Membership buyers
 * persist as ``plan_tier === "starter"``, so they share the same card.
 */
function cardKeyForPlanTier(
  planTier: string | undefined,
): "free" | "membership" | null {
  if (planTier === "free") return "free";
  if (planTier === "starter") return "membership";
  return null;
}

interface PricingTier {
  key: "free" | "membership";
  name: string;
  description: string;
  scanPill: string;
  /** USD; rendered with the appropriate suffix per tier. */
  price: number;
  /** Optional strikethrough anchor — must be a real previous price, not a
   * fabricated MSRP. */
  originalPrice?: number;
  /** Optional small line under the price explaining the strikethrough. */
  priceNote?: string;
  features: string[];
  icon: React.ReactNode;
  ctaLabel: string;
  highlighted?: boolean;
}

const TIERS: PricingTier[] = [
  {
    key: "free",
    name: "Free",
    description: "See exactly where you're losing revenue.",
    scanPill: "3 scans per month",
    price: 0,
    features: [
      "3 scans per calendar month",
      "Full 18-dimension scoring",
      "Revenue leak estimates",
      "Score breakdown per dimension",
    ],
    icon: <Sparkle size={24} weight="regular" />,
    ctaLabel: "Start Free",
  },
  {
    key: "membership",
    name: "Membership",
    description:
      "A year of unlimited fix recommendations across every product in your store.",
    scanPill: "Unlimited scans, one store",
    price: 79,
    // The annual Starter plan was previously listed at $139/year (60% off
    // monthly $29 × 12). Verifiable in git history. Membership replaces it
    // at a lower price.
    originalPrice: 139,
    priceNote: "Down from our previous annual rate.",
    features: [
      "Full fix recommendations",
      "All 18 dimensions",
      "Revenue leak estimates",
      "Email support",
      "1-year access — no auto-renewal",
    ],
    icon: <Lightning size={24} weight="fill" />,
    ctaLabel: "Become a member",
    highlighted: true,
  },
];

export default function PricingPlans() {
  const { data: session, status } = useSession();

  // The session JWT bakes `plan_tier` in at sign-in, so admin changes to a
  // user's plan don't appear until they sign out and back in. Fetch the
  // live value from the backend and prefer it over the session copy.
  const [livePlanTier, setLivePlanTier] = useState<string | null>(null);
  useEffect(() => {
    if (status !== "authenticated") return;
    const controller = new AbortController();
    authFetch(`${API_URL}/user/plan`, { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.plan) setLivePlanTier(data.plan);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        // Silent fallback: session copy remains in effect.
      });
    return () => controller.abort();
  }, [status]);

  const effectivePlanTier =
    livePlanTier ?? (session?.user?.plan_tier as string | undefined);
  const currentCardKey =
    status === "authenticated"
      ? cardKeyForPlanTier(effectivePlanTier)
      : null;

  return (
    <section className="pb-16 sm:pb-24">
      <div className="max-w-3xl mx-auto px-4 sm:px-8">
        {/* Tier grid — 2 cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-5 lg:gap-6">
          {TIERS.map((tier) => {
            const isFree = tier.price === 0;
            const isCurrent = tier.key === currentCardKey;

            return (
              <div
                key={tier.key}
                aria-current={isCurrent ? "true" : undefined}
                className={`relative flex flex-col rounded-2xl border bg-[var(--surface-container-lowest)] p-6 sm:p-8 transition-all ${
                  isCurrent
                    ? "border-[var(--ok)] shadow-[var(--shadow-brand-md)] ring-2 ring-[var(--ok)]/30"
                    : tier.highlighted
                      ? "border-[var(--brand)] shadow-[var(--shadow-brand-md)] ring-2 ring-[var(--brand)]/20"
                      : "border-[var(--outline-variant)]"
                }`}
              >
                {/* Badge: Current plan takes priority over Most popular */}
                {isCurrent ? (
                  <div
                    className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-bold inline-flex items-center gap-1"
                    style={{ background: "var(--ok)", color: "var(--paper)" }}
                  >
                    <CheckCircleIcon size={12} weight="fill" />
                    Your plan
                  </div>
                ) : tier.highlighted ? (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-bold bg-[var(--brand)] text-[var(--paper)] inline-flex items-center gap-1">
                    <Star size={12} weight="fill" />
                    Most popular
                  </div>
                ) : null}

                {/* Icon + Name */}
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                    style={{
                      background: tier.highlighted
                        ? "var(--brand-light)"
                        : "var(--surface-container-high)",
                      color: tier.highlighted
                        ? "var(--brand)"
                        : "var(--on-surface-variant)",
                    }}
                  >
                    {tier.icon}
                  </div>
                  <h3 className="font-display text-lg font-extrabold text-[var(--on-surface)]">
                    {tier.name}
                  </h3>
                </div>

                {/* Price */}
                <div className="mb-4">
                  {isFree ? (
                    <div className="font-display text-4xl font-extrabold text-[var(--on-surface)]">
                      $0
                      <span className="text-base font-semibold text-[var(--on-surface-variant)]">
                        {" "}
                        / forever
                      </span>
                    </div>
                  ) : (
                    <>
                      {tier.originalPrice && (
                        <div
                          className="text-sm font-semibold text-[var(--on-surface-variant)] line-through mb-1"
                          aria-label={`Previously $${tier.originalPrice} per year`}
                        >
                          ${tier.originalPrice} / year
                        </div>
                      )}
                      <div className="font-display text-4xl font-extrabold text-[var(--on-surface)]">
                        ${tier.price}
                        <span className="text-base font-semibold text-[var(--on-surface-variant)]">
                          {" "}
                          / year
                        </span>
                      </div>
                      {tier.priceNote && (
                        <p className="text-xs text-[var(--on-surface-variant)] mt-2">
                          {tier.priceNote}
                        </p>
                      )}
                    </>
                  )}
                </div>

                <p className="text-sm text-[var(--on-surface-variant)] mb-6">
                  {tier.description}
                </p>

                {/* Scan count highlight */}
                <div className="flex items-center gap-2 mb-6 px-3 py-2 rounded-xl bg-[var(--surface-container-low)]">
                  <Lightning size={16} weight="fill" color="var(--brand)" />
                  <span className="text-sm font-semibold text-[var(--on-surface)]">
                    {tier.scanPill}
                  </span>
                </div>

                {/* Features */}
                <ul className="space-y-3 mb-8 flex-1">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <CheckCircle
                        size={18}
                        weight="fill"
                        color="var(--success)"
                        className="shrink-0 mt-0.5"
                      />
                      <span className="text-sm text-[var(--on-surface)]">
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <PricingActions
                  tier={{
                    key: tier.key,
                    ctaLabel: tier.ctaLabel,
                    isCurrent,
                  }}
                />
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
