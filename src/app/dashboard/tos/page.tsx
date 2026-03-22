"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface PlatformRule {
  action: string;
  status: "green" | "yellow" | "red";
  note: string;
}

interface Platform {
  status: string;
  summary: string;
  newAccountRestrictions?: string;
  rules: PlatformRule[];
}

interface TosData {
  lastUpdated: string;
  status: string;
  platforms: Record<string, Platform>;
}

const statusIcon = (s: "green" | "yellow" | "red") => {
  if (s === "green") return <span className="text-green-400 font-bold">✅</span>;
  if (s === "yellow") return <span className="text-yellow-400 font-bold">⚠️</span>;
  return <span className="text-red-400 font-bold">🚫</span>;
};

const statusBg = (s: "green" | "yellow" | "red") => {
  if (s === "green") return "border-l-green-500";
  if (s === "yellow") return "border-l-yellow-500";
  return "border-l-red-500";
};

export default function TosPage() {
  const [data, setData] = useState<TosData | null>(null);

  useEffect(() => {
    const load = () =>
      fetch("/tos.json?" + Date.now())
        .then((r) => r.json())
        .then(setData)
        .catch(() => {});
    load();
    const i = setInterval(load, 15000);
    return () => clearInterval(i);
  }, []);

  if (!data) return (
    <div className="min-h-screen flex items-center justify-center text-[var(--muted)]">Loading TOS research...</div>
  );

  const isComplete = data.status === "complete";

  return (
    <main className="min-h-screen px-4 py-12 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold">🛡️ Platform Rules & TOS</h1>
        <Link href="/dashboard" className="text-xs text-indigo-400 hover:underline">← Dashboard</Link>
      </div>
      <p className={`text-sm mb-8 ${isComplete ? "text-green-400" : "text-orange-400 animate-pulse"}`}>
        {isComplete ? "✅ Research complete" : "⏳ TOS guardian researching..."} · Updated: {data.lastUpdated} · Auto-refreshes every 15s
      </p>

      {!isComplete && (
        <div className="text-center py-12 text-[var(--muted)]">
          <div className="text-4xl mb-4">🔍</div>
          <p className="text-sm">TOS guardian agent is working...</p>
          <p className="text-xs mt-2">This page auto-updates every 15 seconds</p>
        </div>
      )}

      {Object.entries(data.platforms).map(([name, platform]) => (
        <section key={name} className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <h2 className="text-lg font-bold capitalize">{name}</h2>
            <span className={`text-xs px-2 py-0.5 rounded ${
              platform.status === "safe" ? "bg-green-500/20 text-green-400" :
              platform.status === "risky" ? "bg-red-500/20 text-red-400" :
              "bg-yellow-500/20 text-yellow-400"
            }`}>{platform.status}</span>
          </div>

          {platform.summary && (
            <p className="text-sm text-[var(--muted)] mb-3">{platform.summary}</p>
          )}

          {platform.newAccountRestrictions && (
            <div className="mb-3 px-4 py-2 rounded bg-yellow-500/10 border border-yellow-500/30 text-sm text-yellow-300">
              ⚠️ New account: {platform.newAccountRestrictions}
            </div>
          )}

          <div className="rounded-lg bg-[var(--card)] border border-[var(--border)] overflow-hidden">
            {platform.rules.map((rule, i) => (
              <div key={i} className={`flex gap-3 px-4 py-3 border-b border-[var(--border)] last:border-0 border-l-2 ${statusBg(rule.status)}`}>
                <div className="shrink-0 mt-0.5">{statusIcon(rule.status)}</div>
                <div>
                  <div className="text-sm font-medium">{rule.action}</div>
                  <div className="text-xs text-[var(--muted)] mt-1">{rule.note}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}

      <footer className="text-center text-xs text-[var(--muted)] pt-8">
        PageScore TOS Guardian · Private · Auto-refreshes every 15s
      </footer>
    </main>
  );
}
