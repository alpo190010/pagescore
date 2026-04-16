import { Suspense } from "react";
import Link from "next/link";
import {
  CheckCircle,
  Sparkle,
  RocketLaunch,
  Lightning,
} from "@phosphor-icons/react/dist/ssr";
import Footer from "@/components/Footer";
import Button from "@/components/ui/Button";
import PricingActions from "./_components/PricingActions";

/* ══════════════════════════════════════════════════════════════
   Tier definitions — 2-tier model (Free active + Pro teaser)
   ══════════════════════════════════════════════════════════════ */
interface PricingTier {
  key: string;
  name: string;
  description: string;
  scanPill: string;
  features: { text: string; included: boolean }[];
  icon: React.ReactNode;
  ctaLabel: string;
}

const PRICING_TIERS: PricingTier[] = [
  {
    key: "free",
    name: "Free",
    description: "Everything you need to start fixing your product pages",
    scanPill: "3 scans per month",
    features: [
      { text: "3 scans per month", included: true },
      { text: "Full 18-dimension scoring", included: true },
      { text: "Actionable recommendations", included: true },
      { text: "Revenue leak estimates", included: true },
    ],
    icon: <Sparkle size={24} weight="regular" />,
    ctaLabel: "Get Started",
  },
  {
    key: "pro-waitlist",
    name: "Pro",
    description: "For merchants who want more \u2014 coming soon",
    scanPill: "Unlimited scans",
    features: [
      { text: "AI-powered fixes", included: true },
      { text: "Store monitoring", included: true },
      { text: "Competitor insights", included: true },
      { text: "Unlimited scans", included: true },
    ],
    icon: <RocketLaunch size={24} weight="regular" />,
    ctaLabel: "Join Waitlist",
  },
];

/* ══════════════════════════════════════════════════════════════
   /pricing page — Server Component
   ══════════════════════════════════════════════════════════════ */
export default function PricingPage() {
  return (
    <>
      <main id="main-content" className="min-h-screen bg-[var(--bg)]">
        {/* ── Hero ── */}
        <section className="pt-16 sm:pt-24 pb-12 sm:pb-16 text-center">
          <div className="max-w-7xl mx-auto px-4 sm:px-8">
            <h1 className="font-display text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-[var(--on-surface)] mb-4 leading-[1.1]">
              Simple, transparent pricing
            </h1>
            <p className="text-lg sm:text-xl text-[var(--on-surface-variant)] max-w-2xl mx-auto">
              Find your conversion leaks. Fix what matters. Start free.
            </p>
          </div>
        </section>

        {/* ── Tier Grid ── */}
        <section className="pb-16 sm:pb-24">
          <div className="max-w-3xl mx-auto px-4 sm:px-8">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-5 lg:gap-6 max-w-3xl mx-auto">
              {PRICING_TIERS.map((tier) => {
                const isActive = tier.key === "free";
                return (
                  <div
                    key={tier.key}
                    className={`relative flex flex-col rounded-2xl border bg-[var(--surface-container-lowest)] p-6 sm:p-8 transition-all ${
                      isActive
                        ? "border-[var(--brand)] shadow-[var(--shadow-brand-md)] ring-2 ring-[var(--brand)]/20"
                        : "border-[var(--outline-variant)] opacity-70"
                    }`}
                  >
                    {/* Coming Soon badge — Pro card only */}
                    {!isActive && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-bold bg-[var(--surface-container-high)] text-[var(--on-surface-variant)]">
                        Coming Soon
                      </div>
                    )}

                    {/* Icon + Name */}
                    <div className="flex items-center gap-3 mb-4">
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                        style={{
                          background: isActive
                            ? "var(--brand-light)"
                            : "var(--surface-container-high)",
                          color: isActive
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

                    {/* Description */}
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

                    {/* Features — all checkmarks per D-01 */}
                    <ul className="space-y-3 mb-8 flex-1">
                      {tier.features.map((feature) => (
                        <li key={feature.text} className="flex items-start gap-2">
                          <CheckCircle
                            size={18}
                            weight="fill"
                            color="var(--success)"
                            className="shrink-0 mt-0.5"
                          />
                          <span className="text-sm text-[var(--on-surface)]">
                            {feature.text}
                          </span>
                        </li>
                      ))}
                    </ul>

                    {/* CTA -- client island */}
                    <Suspense fallback={null}>
                      <PricingActions tier={{ key: tier.key, ctaLabel: tier.ctaLabel }} />
                    </Suspense>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── FAQ / Trust ── */}
        <section className="py-16 sm:py-20 bg-[var(--surface-container-low)]">
          <div className="max-w-3xl mx-auto px-4 sm:px-8 text-center">
            <h2 className="font-display text-2xl sm:text-3xl font-extrabold text-[var(--on-surface)] mb-4">
              Free, with more on the way.
            </h2>
            <p className="text-[var(--on-surface-variant)] mb-8 text-lg">
              Start analyzing your product pages today at no cost. Pro features
              are in development — join the waitlist to get early access.
            </p>
            <Button asChild variant="primary" size="lg" shape="pill">
              <Link href="/">Try Free — No Signup Required</Link>
            </Button>
          </div>
        </section>

        {/* ── Footer ── */}
        <Footer />
      </main>
    </>
  );
}
