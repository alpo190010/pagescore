"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { authFetch } from "@/lib/auth-fetch";
import { API_URL } from "@/lib/api";
import { extractDomain, scoreColorText, scoreColorTintBg } from "@/lib/analysis";
import Nav from "@/components/Nav";
import NavAuthButton from "@/components/NavAuthButton";

interface Scan {
  id: string;
  url: string;
  score: number;
  productCategory: string;
  createdAt: string;
}

type PageState = "loading" | "ready" | "empty" | "error";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function DashboardPage() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [state, setState] = useState<PageState>("loading");

  const fetchScans = useCallback(async () => {
    setState("loading");
    try {
      const res = await authFetch(`${API_URL}/user/scans`);
      if (!res.ok) throw new Error(`Failed to load scans (${res.status})`);
      const data: Scan[] = await res.json();
      if (data.length === 0) {
        setState("empty");
      } else {
        setScans(data);
        setState("ready");
      }
    } catch {
      setState("error");
    }
  }, []);

  useEffect(() => {
    fetchScans();
  }, [fetchScans]);

  return (
    <>
      <Nav logoText="alpo.ai">
        <NavAuthButton />
      </Nav>

      <main
        id="main-content"
        className="min-h-screen bg-[var(--bg)] pt-24 sm:pt-28 pb-16 px-4 sm:px-8"
      >
        <div className="max-w-4xl mx-auto">
          <h1
            className="text-2xl sm:text-3xl font-extrabold text-[var(--on-surface)] mb-8 tracking-tight"
            style={{ fontFamily: "var(--font-manrope), Manrope, sans-serif" }}
          >
            Your Scans
          </h1>

          {/* Loading skeleton */}
          {state === "loading" && (
            <div className="grid gap-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-20 rounded-2xl animate-pulse"
                  style={{ background: "var(--surface-container-low)" }}
                />
              ))}
            </div>
          )}

          {/* Empty state */}
          {state === "empty" && (
            <div
              className="text-center py-16 rounded-2xl border border-[var(--outline-variant)]"
              style={{ background: "var(--surface-container-lowest)" }}
            >
              <p className="text-lg font-semibold text-[var(--on-surface)] mb-2">
                No scans yet
              </p>
              <p className="text-sm text-[var(--on-surface-variant)] mb-6">
                Scan a product page to see your results here.
              </p>
              <Link
                href="/"
                className="inline-block primary-gradient text-white px-8 py-3 rounded-full font-bold text-sm hover:scale-[1.02] active:scale-95 transition-all"
              >
                Scan Your First Page
              </Link>
            </div>
          )}

          {/* Error state */}
          {state === "error" && (
            <div
              className="text-center py-16 rounded-2xl border border-[var(--outline-variant)]"
              style={{ background: "var(--surface-container-lowest)" }}
            >
              <p className="text-lg font-semibold text-[var(--on-surface)] mb-2">
                Failed to load scans
              </p>
              <p className="text-sm text-[var(--on-surface-variant)] mb-6">
                Something went wrong. Please try again.
              </p>
              <button
                type="button"
                onClick={fetchScans}
                className="inline-block primary-gradient text-white px-8 py-3 rounded-full font-bold text-sm hover:scale-[1.02] active:scale-95 transition-all cursor-pointer"
              >
                Retry
              </button>
            </div>
          )}

          {/* Scan list */}
          {state === "ready" && (
            <div className="grid gap-4">
              {scans.map((scan) => {
                const domain = extractDomain(scan.url) || scan.url;
                return (
                  <Link
                    key={scan.id}
                    href={`/analyze?url=${encodeURIComponent(scan.url)}`}
                    className="flex items-center gap-4 p-5 rounded-2xl border border-[var(--outline-variant)] transition-all hover:border-[var(--brand)]/40 hover:shadow-md"
                    style={{ background: "var(--surface-container-lowest)" }}
                  >
                    {/* Score badge */}
                    <div
                      className="shrink-0 w-14 h-14 rounded-xl flex items-center justify-center font-extrabold text-lg"
                      style={{
                        background: scoreColorTintBg(scan.score),
                        color: scoreColorText(scan.score),
                        fontFamily: "var(--font-manrope), Manrope, sans-serif",
                      }}
                    >
                      {scan.score}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-[var(--on-surface)] truncate">
                        {domain}
                      </p>
                      <p className="text-xs text-[var(--on-surface-variant)] mt-0.5">
                        {formatDate(scan.createdAt)}
                        {scan.productCategory && (
                          <span> · {scan.productCategory}</span>
                        )}
                      </p>
                    </div>

                    {/* Arrow */}
                    <span className="shrink-0 text-[var(--on-surface-variant)] text-sm">
                      →
                    </span>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
