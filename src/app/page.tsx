"use client";

import { useState } from "react";

interface FreeResult {
  score: number;
  summary: string;
  tips: string[];
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FreeResult | null>(null);
  const [error, setError] = useState("");

  async function analyze(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Analysis failed");
      }
      const data = await res.json();
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center px-4">
      {/* Hero */}
      <section className="max-w-2xl w-full text-center pt-24 pb-16">
        <div className="inline-block px-3 py-1 mb-6 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          AI-Powered Analysis
        </div>
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
          Is your landing page{" "}
          <span className="text-indigo-400">losing you money?</span>
        </h1>
        <p className="text-lg text-[var(--muted)] mb-10 max-w-lg mx-auto">
          Paste your URL. Get an AI-powered score with actionable fixes in 30
          seconds. Free quick scan — or unlock the full deep-dive report.
        </p>

        <form onSubmit={analyze} className="flex gap-3 max-w-lg mx-auto">
          <input
            type="url"
            required
            placeholder="https://your-landing-page.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="flex-1 px-4 py-3 rounded-lg bg-[var(--card)] border border-[var(--border)] text-white placeholder:text-[var(--muted)] focus:outline-none focus:border-indigo-500 transition"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-3 rounded-lg bg-indigo-500 hover:bg-indigo-400 text-white font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {loading ? "Analyzing…" : "Scan Free"}
          </button>
        </form>
      </section>

      {/* Error */}
      {error && (
        <div className="max-w-2xl w-full p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm mb-8">
          {error}
        </div>
      )}

      {/* Free Result */}
      {result && (
        <section className="max-w-2xl w-full mb-16">
          <div className="p-6 rounded-xl bg-[var(--card)] border border-[var(--border)]">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Quick Score</h2>
              <div
                className={`text-3xl font-bold ${
                  result.score >= 70
                    ? "text-green-400"
                    : result.score >= 40
                    ? "text-yellow-400"
                    : "text-red-400"
                }`}
              >
                {result.score}/100
              </div>
            </div>
            <p className="text-[var(--muted)] mb-4">{result.summary}</p>
            <h3 className="font-semibold mb-2">Top 3 Quick Fixes:</h3>
            <ul className="space-y-2">
              {result.tips.map((tip, i) => (
                <li key={i} className="flex gap-2 text-sm">
                  <span className="text-indigo-400 mt-0.5">→</span>
                  <span>{tip}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Upsell */}
          <div className="mt-6 p-6 rounded-xl bg-gradient-to-r from-indigo-500/10 to-purple-500/10 border border-indigo-500/20">
            <h3 className="text-lg font-bold mb-2">
              Want the full deep-dive report?
            </h3>
            <p className="text-[var(--muted)] text-sm mb-4">
              Get a comprehensive 10-section analysis: copy teardown, SEO audit,
              CRO opportunities, design review, accessibility check, performance
              tips, mobile UX, trust signals, competitor positioning, and a
              prioritized action plan.
            </p>
            <a
              href={`/report?url=${encodeURIComponent(url)}`}
              className="inline-block px-6 py-3 rounded-lg bg-indigo-500 hover:bg-indigo-400 text-white font-semibold transition"
            >
              Get Full Report — $7
            </a>
          </div>
        </section>
      )}

      {/* Social Proof / Features */}
      {!result && (
        <section className="max-w-3xl w-full grid md:grid-cols-3 gap-6 pb-24">
          {[
            {
              icon: "⚡",
              title: "30-Second Scan",
              desc: "AI analyzes your page instantly. No signup required for the free scan.",
            },
            {
              icon: "🎯",
              title: "Actionable Fixes",
              desc: "Not vague advice. Specific changes you can make today to improve conversions.",
            },
            {
              icon: "📊",
              title: "10-Section Report",
              desc: "Copy, SEO, CRO, design, accessibility, performance, mobile UX, and more.",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="p-5 rounded-xl bg-[var(--card)] border border-[var(--border)]"
            >
              <div className="text-2xl mb-3">{f.icon}</div>
              <h3 className="font-semibold mb-1">{f.title}</h3>
              <p className="text-sm text-[var(--muted)]">{f.desc}</p>
            </div>
          ))}
        </section>
      )}

      {/* Footer */}
      <footer className="pb-8 text-xs text-[var(--muted)]">
        © {new Date().getFullYear()} PageScore. Built with AI.
      </footer>
    </main>
  );
}
