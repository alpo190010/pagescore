"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Nav from "@/components/Nav";
import { API_URL } from "@/lib/api";

type VerifyState = "loading" | "success" | "error";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [state, setState] = useState<VerifyState>("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setState("error");
      setMessage("Invalid or expired verification link.");
      return;
    }

    let cancelled = false;

    async function verify() {
      try {
        const res = await fetch(`${API_URL}/auth/verify-email`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });

        if (cancelled) return;

        if (res.ok) {
          setState("success");
          setMessage("Email verified! You can now sign in.");
        } else {
          setState("error");
          const data = await res.json().catch(() => null);
          setMessage(data?.detail ?? "Invalid or expired verification link.");
        }
      } catch {
        if (!cancelled) {
          setState("error");
          setMessage("Something went wrong. Please try again later.");
        }
      }
    }

    verify();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="max-w-md mx-auto px-4 py-16 text-center">
      {state === "loading" && (
        <div className="space-y-4">
          <div
            className="w-10 h-10 mx-auto rounded-full border-[3px] border-[var(--border)] border-t-[var(--brand)] animate-spin"
            aria-label="Verifying"
          />
          <p className="text-[var(--text-secondary)] text-sm font-medium">
            Verifying your email…
          </p>
        </div>
      )}

      {state === "success" && (
        <div className="space-y-5">
          <div className="w-14 h-14 mx-auto rounded-full bg-[var(--success-light)] border border-[var(--success-border)] flex items-center justify-center">
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--success)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)] mb-2">
              Email Verified
            </h1>
            <p
              className="text-sm text-[var(--success)] font-medium"
              role="status"
            >
              {message}
            </p>
          </div>
          <Link
            href="/"
            className="inline-block px-6 py-3 rounded-xl text-sm font-semibold text-white polish-hover-lift polish-focus-ring"
            style={{
              background:
                "linear-gradient(135deg, var(--brand), var(--primary-dim))",
            }}
          >
            Go to Home
          </Link>
        </div>
      )}

      {state === "error" && (
        <div className="space-y-5">
          <div className="w-14 h-14 mx-auto rounded-full bg-[var(--error-light)] border border-[var(--error-border-light)] flex items-center justify-center">
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--error)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)] mb-2">
              Verification Failed
            </h1>
            <p className="text-sm text-[var(--error)] font-medium" role="alert">
              {message}
            </p>
          </div>
          <Link
            href="/"
            className="inline-block px-6 py-3 rounded-xl text-sm font-semibold text-[var(--brand)] border-[1.5px] border-[var(--border)] bg-[var(--bg)] hover:bg-[var(--surface)] transition-colors polish-hover-lift polish-focus-ring"
          >
            Go to Home
          </Link>
        </div>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <>
      <Nav variant="simple" />
      <Suspense
        fallback={
          <div className="max-w-md mx-auto px-4 py-16 text-center">
            <div
              className="w-10 h-10 mx-auto rounded-full border-[3px] border-[var(--border)] border-t-[var(--brand)] animate-spin"
              aria-label="Loading"
            />
          </div>
        }
      >
        <VerifyEmailContent />
      </Suspense>
    </>
  );
}
