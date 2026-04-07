"use client";

import ErrorCard from "@/components/ErrorCard";

export default function PricingError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <ErrorCard
      error={error}
      reset={reset}
      title="Something went wrong"
      message="We couldn't load the pricing information. Please try again in a moment."
      secondaryLabel="Go Home"
      secondaryHref="/"
    />
  );
}
