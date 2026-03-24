"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface ViralityData {
  lastUpdated: string;
  status: string;
  platforms: Record<string, { status: string; findings: string[] }>;
  titleFormulas: string[];
  postingTimes: string[];
  keyInsights: string[];
  doNot: string[];
}

export default function ViralityPage() {
  const [data, setData] = useState<ViralityData | null>(null);

  useEffect(() => {
    const load = () =>
      fetch("/virality.json?" + Date.now())
        .then((r) => r.json())
        .then(setData)
        .catch(() => {});
    load();
    const i = setInterval(load, 15000);
    return () => clearInterval(i);
  }, []);

  if (!data) return (
    <div className="min-h-screen flex items-center justify-center text-[var(--muted)]">
      Loading virality research...
    </div>
  );

  const statusColor = data.status === "complete" ? "text-green-400" : "text-orange-400 animate-pulse";

  return (
    <main className="min-h-screen px-4 py-12 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold">🔥 Virality Research</h1>
        <Link href="/dashboard" className="text-xs text-indigo-400 hover:underline">← Dashboard</Link>
      </div>
      <p className={`text-sm mb-8 ${statusColor}`}>
        {data.status === "complete" ? "✅ Research complete" : "⏳ Agent researching..."} · Updated: {data.lastUpdated} · Auto-refreshes every 15s
      </p>

      {/* Platform Research */}
      <section className="mb-10">
        <h2 className="text-lg font-bold mb-3">Platform Findings</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(data.platforms).map(([platform, info]) => (
            <div key={platform} className="rounded-lg bg-[var(--card)] border border-[var(--border)] p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold capitalize text-indigo-400">{platform}</h3>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  info.status === "complete" ? "bg-green-500/20 text-green-400" :
                  info.status === "researching" ? "bg-orange-500/20 text-orange-400" :
                  "bg-gray-500/20 text-gray-400"
                }`}>{info.status}</span>
              </div>
              {info.findings.length > 0 ? (
                <ul className="space-y-2">
                  {info.findings.map((f, i) => (
                    <li key={i} className="text-sm text-[var(--muted)] flex gap-2">
                      <span className="text-indigo-400 shrink-0">→</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-[var(--muted)] italic">Researching...</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Title Formulas */}
      {data.titleFormulas.length > 0 && (
        <section className="mb-10">
          <h2 className="text-lg font-bold mb-3">🎯 Title Formulas That Work</h2>
          <div className="rounded-lg bg-[var(--card)] border border-[var(--border)] overflow-hidden">
            {data.titleFormulas.map((f, i) => (
              <div key={i} className="px-4 py-3 border-b border-[var(--border)] last:border-0 text-sm">
                <span className="text-yellow-400 mr-2">{i + 1}.</span>{f}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Posting Times */}
      {data.postingTimes.length > 0 && (
        <section className="mb-10">
          <h2 className="text-lg font-bold mb-3">⏰ Best Posting Times</h2>
          <div className="rounded-lg bg-[var(--card)] border border-[var(--border)] overflow-hidden">
            {data.postingTimes.map((t, i) => (
              <div key={i} className="px-4 py-2 border-b border-[var(--border)] last:border-0 text-sm text-[var(--muted)]">
                <span className="text-green-400 mr-2">✓</span>{t}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Key Insights */}
      {data.keyInsights.length > 0 && (
        <section className="mb-10">
          <h2 className="text-lg font-bold mb-3">💡 Key Insights</h2>
          <div className="rounded-lg bg-[var(--card)] border border-[var(--border)] overflow-hidden">
            {data.keyInsights.map((insight, i) => (
              <div key={i} className="px-4 py-3 border-b border-[var(--border)] last:border-0 text-sm">
                <span className="text-indigo-400 mr-2">→</span>{insight}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Do NOT do */}
      {data.doNot.length > 0 && (
        <section className="mb-10">
          <h2 className="text-lg font-bold mb-3">❌ Never Do This</h2>
          <div className="rounded-lg bg-[var(--card)] border border-red-500/20 overflow-hidden">
            {data.doNot.map((d, i) => (
              <div key={i} className="px-4 py-2 border-b border-[var(--border)] last:border-0 text-sm text-red-400">
                <span className="mr-2">✗</span>{d}
              </div>
            ))}
          </div>
        </section>
      )}

      {data.status !== "complete" && (
        <div className="text-center py-12 text-[var(--muted)]">
          <div className="text-4xl mb-4">🔍</div>
          <p className="text-sm">Virality research agent is working...</p>
          <p className="text-xs mt-2">This page auto-updates every 15 seconds</p>
        </div>
      )}

      <footer className="text-center text-xs text-[var(--muted)] pt-8">
        PageLeaks Virality Research · Private · Auto-refreshes every 15s
      </footer>
    </main>
  );
}
