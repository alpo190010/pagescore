"use client";

import { useState, useCallback } from "react";
import { type FreeResult, captureEvent } from "@/lib/analysis";

/* ══════════════════════════════════════════════════════════════
   useEmailModal — email submission + modal state
   Extracted from useProductAnalysis to keep each hook focused.
   ══════════════════════════════════════════════════════════════ */

interface UseEmailModalParams {
  selectedUrl: string;
  analysisResult: FreeResult | null;
}

export function useEmailModal({ selectedUrl, analysisResult }: UseEmailModalParams) {
  const [email, setEmail] = useState("");
  const [emailSubmitting, setEmailSubmitting] = useState(false);
  const [emailError, setEmailError] = useState("");
  const [selectedLeak, setSelectedLeak] = useState<string | null>(null);
  const [competitorCTAName, setCompetitorCTAName] = useState<string | null>(null);
  const [emailStep, setEmailStep] = useState<"form" | "queued" | "pricing" | "sent" | null>(null);

  /** Reset all email / modal state (called on product switch & new analysis). */
  const resetEmailState = useCallback(() => {
    setEmail("");
    setEmailError("");
    setEmailStep(null);
    setSelectedLeak(null);
    setCompetitorCTAName(null);
  }, []);

  /** Submit the report-request email. */
  const submitEmail = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (emailSubmitting) return;
      setEmailSubmitting(true);
      setEmailError("");
      try {
        const res = await fetch("/api/request-report", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email.trim(),
            url: selectedUrl,
            score: analysisResult?.score,
            summary: analysisResult?.summary,
            tips: analysisResult?.tips,
            categories: analysisResult?.categories,
            competitorName: competitorCTAName,
          }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          if (res.status === 429)
            throw new Error("Too many requests. Please wait a moment and try again.");
          throw new Error(data.error || "Failed to send. Please try again.");
        }
        setEmailStep("queued");
        captureEvent("report_email_submitted", { url: selectedUrl, score: analysisResult?.score });
      } catch (err: unknown) {
        setEmailError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      } finally {
        setEmailSubmitting(false);
      }
    },
    [email, selectedUrl, analysisResult, emailSubmitting, competitorCTAName],
  );

  /** Open the modal for a specific leak category. */
  const handleIssueClick = useCallback((key: string) => {
    setSelectedLeak(key);
    setCompetitorCTAName(null);
    setEmailStep("form");
    captureEvent("issue_clicked", { category: key });
  }, []);

  /** Close the email / issue modal. */
  const handleCloseModal = useCallback(() => {
    setEmailStep(null);
    setSelectedLeak(null);
    setCompetitorCTAName(null);
    setEmailError("");
  }, []);

  return {
    email,
    emailSubmitting,
    emailError,
    selectedLeak,
    competitorCTAName,
    emailStep,
    setEmail,
    setEmailStep,
    submitEmail,
    handleIssueClick,
    handleCloseModal,
    resetEmailState,
  };
}
