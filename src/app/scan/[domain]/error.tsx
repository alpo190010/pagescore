"use client";

import { WarningCircleIcon } from "@phosphor-icons/react";
import Link from "next/link";

export default function ScanError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen bg-[var(--bg)] flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center space-y-6 anim-phase-enter">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-[var(--error-light)] flex items-center justify-center">
          <WarningCircleIcon size={28} weight="regular" color="var(--error)" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)] mb-2">Something went wrong</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            {error.message || "Failed to load the store scan."}
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            type="button"
            onClick={reset}
            className="cursor-pointer inline-flex items-center justify-center gap-2 px-6 py-3 primary-gradient text-white rounded-full font-bold text-sm hover:brightness-110 transition-all"
          >
            Try Again
          </button>
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full font-bold text-sm text-[var(--on-surface)] bg-[var(--surface-container-low)] border border-[var(--border)] hover:bg-[var(--surface-container)] transition-all"
          >
            Try Another URL
          </Link>
        </div>
      </div>
    </div>
  );
}
