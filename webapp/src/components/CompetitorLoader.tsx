"use client";

import { useState, useEffect } from "react";
import StepProgress from "@/components/analysis/StepProgress";

const STEPS = [
  { icon: "🔎", label: "Finding similar products", sub: "Identifying competitors in your niche" },
  { icon: "🌐", label: "Fetching competitor pages", sub: "Loading product pages for comparison" },
  { icon: "📊", label: "Scoring competitors", sub: "Analyzing each page across 7 categories" },
  { icon: "⚖️", label: "Preparing comparison", sub: "Building your competitive breakdown" },
];

export default function CompetitorLoader({ url }: { url: string }) {
  const [activeStep, setActiveStep] = useState(0);
  const [stepsComplete, setStepsComplete] = useState(false);

  useEffect(() => {
    const timers = STEPS.map((_, i) =>
      setTimeout(() => setActiveStep(i), i * 6500)
    );
    // Mark all steps complete after the last one has had time to show
    const doneTimer = setTimeout(() => setStepsComplete(true), STEPS.length * 6500);
    return () => {
      timers.forEach(clearTimeout);
      clearTimeout(doneTimer);
    };
  }, []);

  const truncatedUrl = url.length > 60 ? url.slice(0, 60) + "…" : url;

  return (
    <section className="w-full flex justify-center mt-10 mb-8 px-4" aria-label="Competitor analysis in progress">
      <div className="max-w-[480px] w-full bg-[var(--surface)] border-[1.5px] border-[var(--border)] rounded-2xl px-8 py-9">
        {/* Header */}
        <div className="text-center mb-7">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-1.5">
            Analyzing competitors
          </h2>
          <p className="text-[13px] text-[var(--text-tertiary)] truncate">
            {truncatedUrl}
          </p>
        </div>

        <StepProgress
          steps={STEPS}
          activeStep={activeStep}
          stepsComplete={stepsComplete}
          transitionDuration="5s"
          progressCap={90}
        />

        {/* Estimated time */}
        <p className="text-xs text-[var(--text-tertiary)] text-center mt-5">
          Usually takes 20–30 seconds
        </p>
      </div>
    </section>
  );
}
