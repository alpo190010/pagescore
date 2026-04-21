"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import dynamic from "next/dynamic";
import { LinkIcon, ArrowRightIcon } from "@phosphor-icons/react";
import { isValidUrl, isProductPageUrl, extractDomain } from "@/lib/analysis/helpers";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";

const AuthModal = dynamic(() => import("@/components/AuthModal"), {
  ssr: false,
});

export default function HeroForm() {
  const router = useRouter();
  const pathname = usePathname();
  const { status } = useSession();
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [pendingDestination, setPendingDestination] = useState<string | null>(null);

  // Reset stuck submitting state when navigation bounces back to /
  useEffect(() => {
    if (submitting && pathname === "/") {
      setSubmitting(false);
    }
  }, [pathname, submitting]);

  // If user authenticates via the modal, continue to their intended destination.
  useEffect(() => {
    if (status === "authenticated" && pendingDestination) {
      router.push(pendingDestination);
      setPendingDestination(null);
    }
  }, [status, pendingDestination, router]);

  const handleUrlChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setUrl(e.target.value);
      if (error) setError("");
    },
    [error],
  );

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (submitting) return;
      const validUrl = isValidUrl(url);
      if (!validUrl) {
        setError(
          "Please enter a valid URL (e.g. yourstore.com or yourstore.com/products/...)",
        );
        return;
      }

      const destination = isProductPageUrl(validUrl)
        ? `/analyze?url=${encodeURIComponent(validUrl)}`
        : `/scan/${encodeURIComponent(extractDomain(validUrl) || validUrl)}`;

      if (status !== "authenticated") {
        // Require sign-in before running any scan. Remember where to go next.
        setPendingDestination(destination);
        setAuthModalOpen(true);
        return;
      }

      setSubmitting(true);
      router.push(destination);
    },
    [url, submitting, router, status],
  );

  return (
    <>
      <form id="hero-form" onSubmit={handleSubmit} className="max-w-2xl mx-auto">
        <div className="flex flex-col sm:flex-row p-2 bg-[var(--surface-container-lowest)] rounded-2xl sm:rounded-full shadow-[var(--shadow-subtle)] border border-[var(--outline-variant)]/15 focus-within:border-[var(--brand)]/40 transition-all duration-300">
          <div className="hidden sm:flex items-center pl-6 pr-2 text-[var(--outline)]">
            <LinkIcon size={20} weight="regular" />
          </div>
          <Input
            id="url-input"
            type="text"
            inputMode="url"
            autoCapitalize="none"
            autoCorrect="off"
            placeholder="Paste your store or product page URL..."
            value={url}
            onChange={handleUrlChange}
            aria-label="Product page URL"
            maxLength={2048}
            className="flex-1 bg-transparent border-none focus:ring-0 focus:outline-none text-base sm:text-lg placeholder:text-[var(--outline)] px-4 py-3 sm:py-0 text-[var(--on-surface)] rounded-none border-0"
            aria-describedby={error ? "url-error" : undefined}
          />
          <Button
            type="submit"
            variant="primary"
            size="lg"
            shape="pill"
            disabled={submitting}
            className="w-full sm:w-auto px-8 sm:px-10"
          >
            {submitting ? "Loading..." : "Analyze Free"}
            {!submitting && <ArrowRightIcon size={16} weight="bold" />}
          </Button>
        </div>
      </form>

      {error && (
        <div className="max-w-2xl mx-auto mt-4">
          <div
            id="url-error"
            className="p-4 rounded-xl text-sm border-l-4 bg-[var(--error-light)] border-l-[var(--error)] border border-[var(--error-border-light)]"
            role="alert"
          >
            <span className="text-[var(--error)] font-medium">{error}</span>
          </div>
        </div>
      )}

      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode="signup"
        heading="Sign up to run your first scan"
        subheading="It's free — 3 scans per month on the free plan."
      />
    </>
  );
}
