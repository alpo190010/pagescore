"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

const PLANS = [
  {
    name: "Pro",
    price: "$49/mo",
    features: [
      "Full 10-section reports with AI fix suggestions",
      "AI-generated title & description rewrites",
      "Up to 10 products",
      "Competitor comparison unlocked",
    ],
    cta: "Start Free Trial — Pro",
    highlight: true,
  },
  {
    name: "Agency",
    price: "$149/mo",
    features: [
      "Everything in Pro, plus:",
      "Weekly monitoring & email alerts",
      "Unlimited products & multiple stores",
      "White-label PDF reports",
      "Team seats & priority support",
    ],
    cta: "Start Free Trial — Agency",
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
                    <span className="text-indigo-400 shrink-0">&#10003;</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
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
