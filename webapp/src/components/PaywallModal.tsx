"use client";

import { useState } from "react";
import {
  XIcon,
  LockKeyIcon,
  CrownIcon,
  RocketLaunchIcon,
  BuildingsIcon,
  CheckCircleIcon,
} from "@phosphor-icons/react";
import { captureEvent } from "@/lib/analysis";
import type { PlanTier } from "@/lib/analysis/types";
import Button from "@/components/ui/Button";
import Modal, { ModalTitle, ModalClose } from "@/components/ui/Modal";

/* ══════════════════════════════════════════════════════════════
   PaywallModal — Subscription upgrade prompt (tier-aware)
   Shows Starter / Growth / Pro checkout links via LemonSqueezy.
   userPlan controls header copy and grays out current tier.
   ══════════════════════════════════════════════════════════════ */

const LS_STORE_URL = process.env.NEXT_PUBLIC_LS_STORE_URL ?? "";
const LS_VARIANT_STARTER = process.env.NEXT_PUBLIC_LS_VARIANT_STARTER ?? "";
const LS_VARIANT_GROWTH = process.env.NEXT_PUBLIC_LS_VARIANT_GROWTH ?? "";
const LS_VARIANT_PRO = process.env.NEXT_PUBLIC_LS_VARIANT_PRO ?? "";

interface SubscriptionTier {
  key: string;
  name: string;
  price: string;
  period: string;
  description: string;
  variant: string;
  icon: React.ReactNode;
}

const TIERS: SubscriptionTier[] = [
  {
    key: "starter",
    name: "Starter",
    price: "$29",
    period: "/mo",
    description: "10 scans per month with full reports",
    variant: LS_VARIANT_STARTER,
    icon: <RocketLaunchIcon size={20} weight="regular" />,
  },
  {
    key: "growth",
    name: "Growth",
    price: "$79",
    period: "/mo",
    description: "30 scans per month with full reports",
    variant: LS_VARIANT_GROWTH,
    icon: <CrownIcon size={20} weight="regular" />,
  },
  {
    key: "pro",
    name: "Pro",
    price: "$149",
    period: "/mo",
    description: "100 scans per month with full reports",
    variant: LS_VARIANT_PRO,
    icon: <BuildingsIcon size={20} weight="regular" />,
  },
];

function buildCheckoutUrl(
  variant: string,
  userId: string,
  analyzedUrl: string,
): string {
  if (!LS_STORE_URL || !variant) return "";
  return `${LS_STORE_URL}/checkout/buy/${variant}?checkout[custom][user_id]=${userId}&checkout[custom][url]=${encodeURIComponent(analyzedUrl)}`;
}

interface PaywallModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
  analyzedUrl: string;
  leakKey: string | null;
  userPlan?: PlanTier;
}

export default function PaywallModal({
  isOpen,
  onClose,
  userId,
  analyzedUrl,
  leakKey,
  userPlan = "free",
}: PaywallModalProps) {
  const [checkoutClicked, setCheckoutClicked] = useState(false);

  const isStarter = userPlan === "starter";

  return (
    <Modal
      open={isOpen}
      onOpenChange={(v) => !v && onClose()}
      ariaLabel="Upgrade to unlock full report"
      className="max-h-[90vh] overflow-y-auto"
    >
        <div
          className="h-1 w-full"
          style={{ background: "var(--gradient-primary)" }}
        />
        <ModalClose>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            shape="pill"
            className="absolute top-4 right-4 w-11 h-11 hover:bg-[var(--bg)] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] z-10"
            aria-label="Close"
          >
            <XIcon size={18} weight="bold" />
          </Button>
        </ModalClose>

        <div className="p-6 sm:p-8">
          {/* Header — tier-aware */}
          <div className="text-center mb-6">
            <div className="w-14 h-14 mx-auto mb-4 rounded-2xl flex items-center justify-center bg-[var(--brand-light)] border border-[var(--brand-border)]">
              <LockKeyIcon size={28} weight="regular" color="var(--brand)" />
            </div>
            <ModalTitle asChild>
              <h3 className="font-display text-xl font-bold mb-2 text-[var(--text-primary)]">
                {isStarter ? "Upgrade to unlock all dimensions" : "Subscribe to get fixes"}
              </h3>
            </ModalTitle>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
              {isStarter
                ? "You're on Starter with 7 dimensions. Upgrade to access all 18 conversion dimensions with detailed fixes."
                : "Get detailed fixes, actionable recommendations, and step-by-step guides to boost your conversion rate."
              }
            </p>
          </div>

          {/* ── Subscription Tiers ── */}
          <div className="space-y-3">
            {TIERS.map((tier) => {
              const isCurrent = isStarter && tier.key === "starter";
              const checkoutUrl = buildCheckoutUrl(
                tier.variant,
                userId,
                analyzedUrl,
              );
              const available = !!checkoutUrl && !isCurrent;

              return isCurrent ? (
                <div
                  key={tier.key}
                  className="flex items-center gap-4 p-4 rounded-2xl border border-[var(--border)] opacity-50"
                >
                  <div className="w-10 h-10 rounded-xl bg-[var(--surface-container-high)] flex items-center justify-center text-[var(--on-surface-variant)] shrink-0">
                    {tier.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-sm font-bold text-[var(--text-primary)]">
                        {tier.name}
                      </span>
                      <span className="text-lg font-extrabold text-[var(--text-tertiary)]">
                        {tier.price}
                      </span>
                      <span className="text-xs text-[var(--text-tertiary)]">
                        {tier.period}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-tertiary)] mt-0.5 flex items-center gap-1">
                      <CheckCircleIcon size={12} weight="fill" /> Current plan
                    </p>
                  </div>
                </div>
              ) : available ? (
                <Button
                  key={tier.key}
                  type="button"
                  variant="ghost"
                  size="md"
                  disabled={checkoutClicked}
                  onClick={() => {
                    captureEvent("paywall_subscription_clicked", {
                      tier: tier.key,
                      price: tier.price,
                      userId,
                      url: analyzedUrl,
                      leakKey,
                    });
                    setCheckoutClicked(true);
                    window.open(checkoutUrl, "_blank");
                    setTimeout(() => setCheckoutClicked(false), 2000);
                  }}
                  className="flex items-center gap-4 p-4 rounded-2xl border border-[var(--border)] hover:border-[var(--brand)] hover:bg-[var(--brand-light)] group text-left h-auto"
                >
                  <div className="w-10 h-10 rounded-xl bg-[var(--surface-container-high)] flex items-center justify-center text-[var(--on-surface-variant)] group-hover:text-[var(--brand)] transition-colors shrink-0">
                    {tier.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-sm font-bold text-[var(--text-primary)]">
                        {tier.name}
                      </span>
                      <span className="text-lg font-extrabold text-[var(--brand)]">
                        {tier.price}
                      </span>
                      <span className="text-xs text-[var(--text-tertiary)]">
                        {tier.period}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] mt-0.5 truncate">
                      {tier.description}
                    </p>
                  </div>
                </Button>
              ) : (
                <div
                  key={tier.key}
                  className="flex items-center gap-4 p-4 rounded-2xl border border-[var(--border)] opacity-50"
                >
                  <div className="w-10 h-10 rounded-xl bg-[var(--surface-container-high)] flex items-center justify-center text-[var(--on-surface-variant)] shrink-0">
                    {tier.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-sm font-bold text-[var(--text-primary)]">
                        {tier.name}
                      </span>
                      <span className="text-lg font-extrabold text-[var(--text-tertiary)]">
                        {tier.price}
                      </span>
                      <span className="text-xs text-[var(--text-tertiary)]">
                        {tier.period}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-tertiary)] mt-0.5">
                      Coming soon
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          <p className="text-xs text-center mt-5 text-[var(--text-tertiary)]">
            Secure checkout via LemonSqueezy. Cancel anytime.
          </p>
        </div>
    </Modal>
  );
}
