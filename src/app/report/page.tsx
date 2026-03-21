"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function ReportContent() {
  const params = useSearchParams();
  const url = params.get("url") || "";

  // Lemon Squeezy checkout URL - replace with actual product link
  const checkoutUrl = process.env.NEXT_PUBLIC_LEMONSQUEEZY_CHECKOUT_URL || "#";
  const fullCheckoutUrl = `${checkoutUrl}?checkout[custom][url]=${encodeURIComponent(url)}`;

  return (
    <main className="min-h-screen flex flex-col items-center px-4 pt-24">
      <div className="max-w-xl w-full text-center">
        <h1 className="text-3xl font-bold mb-4">Full Page Analysis</h1>
        <p className="text-[var(--muted)] mb-2">
          Deep-dive report for:
        </p>
        <p className="text-indigo-400 font-mono text-sm mb-8 break-all">
          {url || "No URL provided"}
        </p>

        <div className="p-6 rounded-xl bg-[var(--card)] border border-[var(--border)] text-left mb-8">
          <h2 className="font-bold mb-4">Your report includes:</h2>
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
        </div>

        <a
          href={fullCheckoutUrl}
          className="inline-block px-8 py-4 rounded-lg bg-indigo-500 hover:bg-indigo-400 text-white font-bold text-lg transition"
        >
          Get Full Report — $7
        </a>
        <p className="text-xs text-[var(--muted)] mt-4">
          Delivered to your email within 5 minutes. One-time payment.
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
