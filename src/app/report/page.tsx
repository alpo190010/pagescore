"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

const PLANS = [
  {
    name: "Starter",
    price: "$29/mo",
    features: [
      "Full 10-section reports with AI fix suggestions",
      "AI-generated title & description rewrites",
      "Up to 10 products",
      "Competitor comparison unlocked",
    ],
    cta: "Start Free Trial — Starter",
    highlight: true,
  },
  {
    name: "Growth",
    price: "$79/mo",
    features: [
      "Everything in Starter, plus:",
      "Weekly monitoring & email alerts",
      "AI rewrites for all product copy",
      "Up to 100 products",
      "Competitive benchmarking & trends",
    ],
    cta: "Start Free Trial — Growth",
    highlight: false,
  },
];

function ReportContent() {
  const params = useSearchParams();
  const url = params.get("url") || "";
  const feature = params.get("feature") || "";

  return (
    <main className="min-h-screen flex flex-col items-center px-4 pt-24">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-4">
            {feature === "rewrites" ? "Unlock AI Rewrites" : "Unlock Your Full Report"}
          </h1>
          <p className="text-[var(--muted)] mb-2">
            {feature === "rewrites"
              ? "Get AI-optimized product copy for:"
              : "Deep-dive analysis for:"}
          </p>
          <p className="text-indigo-400 font-mono text-sm break-all">
            {url || "No URL provided"}
          </p>
        </div>

        {/* What's included */}
        <div className="p-6 rounded-xl bg-[var(--card)] border border-[var(--border)] text-left mb-8">
          <h2 className="font-bold mb-4">Your full report includes:</h2>
          <ul className="space-y-3">
            {[
              "📝 Copy Teardown — headline, subhead, CTA analysis",
              "🔍 SEO Audit — meta tags, structure, keywords",
              "🎯 CRO Opportunities — conversion blockers & fixes",
              "🎨 Design Review — visual hierarchy, whitespace, contrast",
              "♿ Accessibility — WCAG compliance issues",
              "⚡ Performance — load time, asset optimization",
              "📱 Mobile UX — responsive design issues",
              "🤝 Trust Signals — social proof, credibility gaps",
              "🏆 Competitor Positioning — differentiation analysis",
              "📋 Prioritized Action Plan — what to fix first",
            ].map((item) => (
              <li key={item} className="text-sm flex gap-2">
                <span>{item}</span>
              </li>
            ))}
          </ul>
          {feature === "rewrites" && (
            <div className="mt-4 pt-4 border-t border-[var(--border)]">
              <h3 className="font-bold mb-2">Plus AI Rewrites:</h3>
              <ul className="space-y-2">
                <li className="text-sm flex gap-2">✨ Optimized product title for SEO + conversions</li>
                <li className="text-sm flex gap-2">✨ Rewritten product description with benefit-first copy</li>
                <li className="text-sm flex gap-2">✨ Meta description optimized for click-through</li>
              </ul>
            </div>
          )}
        </div>

        {/* Plan selection */}
        <div className="grid md:grid-cols-2 gap-4 mb-8">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`p-6 rounded-xl border flex flex-col ${
                plan.highlight
                  ? "bg-indigo-500/5 border-indigo-500/30 relative"
                  : "bg-[var(--card)] border-[var(--border)]"
              }`}
            >
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-xs font-bold bg-indigo-500 text-white">
                  Recommended
                </div>
              )}
              <h3 className="font-bold text-lg mb-1">{plan.name}</h3>
              <div className="text-2xl font-bold mb-3">{plan.price}</div>
              <ul className="space-y-2 mb-6 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="text-sm flex gap-2">
                    <span className="text-indigo-400 shrink-0">✓</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              {/* TODO: Replace href with actual Lemon Squeezy subscription checkout URL for each plan */}
              <a
                href="#"
                className={`block text-center px-6 py-3 rounded-lg font-bold transition ${
                  plan.highlight
                    ? "bg-indigo-500 hover:bg-indigo-400 text-white"
                    : "border border-[var(--border)] hover:border-indigo-500/50 text-white"
                }`}
              >
                {plan.cta}
              </a>
            </div>
          ))}
        </div>

        <p className="text-center text-xs text-[var(--muted)] mb-4">
          Cancel anytime. Reports delivered to your email within 5 minutes.
        </p>
        <p className="text-center text-xs text-[var(--muted)]">
          Need unlimited products or white-label reports?{" "}
          <a href="mailto:hello@pagescore.app" className="text-indigo-400 hover:underline">
            Contact us about the Agency plan ($199/mo)
          </a>
        </p>
      </div>
    </main>
  );
}

export default function ReportPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-[var(--muted)]">Loading...</div>}>
      <ReportContent />
    </Suspense>
  );
}
