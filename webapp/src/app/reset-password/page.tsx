"use client";

import { useState, FormEvent, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Nav from "@/components/Nav";
import { API_URL } from "@/lib/api";

/** Client-side password strength check: 8+ chars, ≥1 letter, ≥1 number */
function validatePassword(pw: string): string | null {
  if (pw.length < 8) return "Password must be at least 8 characters";
  if (!/[a-zA-Z]/.test(pw)) return "Password must contain at least one letter";
  if (!/[0-9]/.test(pw)) return "Password must contain at least one number";
  return null;
}

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordHint, setPasswordHint] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  function handlePasswordChange(value: string) {
    setPassword(value);
    if (value.length > 0) {
      setPasswordHint(validatePassword(value) ?? "");
    } else {
      setPasswordHint("");
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    // Client-side validation
    const pwError = validatePassword(password);
    if (pwError) {
      setError(pwError);
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (!token) {
      setError("Invalid or expired reset link.");
      return;
    }

    setSubmitting(true);

    try {
      const res = await fetch(`${API_URL}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });

      if (res.ok) {
        setSuccess(true);
      } else {
        const data = await res.json().catch(() => null);
        setError(data?.detail ?? "Invalid or expired reset link.");
      }
    } catch {
      setError("Something went wrong. Please try again later.");
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center space-y-5">
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
            Password Reset
          </h1>
          <p
            className="text-sm text-[var(--success)] font-medium"
            role="status"
          >
            Password reset! You can now sign in.
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
    );
  }

  if (!token) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center space-y-5">
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
            Invalid Link
          </h1>
          <p className="text-sm text-[var(--error)] font-medium" role="alert">
            Invalid or expired reset link.
          </p>
        </div>
        <Link
          href="/forgot-password"
          className="inline-block px-6 py-3 rounded-xl text-sm font-semibold text-[var(--brand)] border-[1.5px] border-[var(--border)] bg-[var(--bg)] hover:bg-[var(--surface)] transition-colors polish-hover-lift polish-focus-ring"
        >
          Request New Link
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <div className="space-y-6">
        <div className="text-center">
          <h1 className="text-xl font-bold text-[var(--text-primary)] mb-1">
            Reset Password
          </h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Enter your new password below.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <input
              type="password"
              required
              placeholder="New password"
              value={password}
              onChange={(e) => handlePasswordChange(e.target.value)}
              aria-label="New password"
              autoComplete="new-password"
              autoFocus
              minLength={8}
              className="w-full px-4 py-3.5 text-base rounded-xl outline-none border-[1.5px] border-[var(--border)] text-[var(--text-primary)] bg-[var(--bg)] polish-focus-ring"
            />
            {passwordHint && (
              <p className="text-xs text-[var(--text-tertiary)] mt-1 px-1">
                {passwordHint}
              </p>
            )}
          </div>

          <div>
            <input
              type="password"
              required
              placeholder="Confirm new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              aria-label="Confirm new password"
              autoComplete="new-password"
              minLength={8}
              className="w-full px-4 py-3.5 text-base rounded-xl outline-none border-[1.5px] border-[var(--border)] text-[var(--text-primary)] bg-[var(--bg)] polish-focus-ring"
            />
          </div>

          <div className="pt-1">
            <button
              type="submit"
              disabled={submitting}
              className="cursor-pointer w-full px-6 py-3.5 rounded-xl text-base font-semibold text-white polish-hover-lift polish-focus-ring disabled:opacity-50"
              style={{
                background: submitting
                  ? "var(--text-tertiary)"
                  : "linear-gradient(135deg, var(--brand), var(--primary-dim))",
              }}
            >
              {submitting ? "Resetting…" : "Reset Password"}
            </button>
          </div>

          {error && (
            <p
              className="text-sm text-center text-[var(--error)] font-medium"
              role="alert"
            >
              {error}
            </p>
          )}
        </form>

        <p className="text-sm text-center text-[var(--text-secondary)]">
          Remember your password?{" "}
          <Link
            href="/"
            className="text-[var(--brand)] font-semibold hover:underline polish-focus-ring rounded"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
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
        <ResetPasswordContent />
      </Suspense>
    </>
  );
}
