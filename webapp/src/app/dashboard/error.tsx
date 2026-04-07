"use client";

import ErrorCard from "@/components/ErrorCard";

export default function DashboardError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <ErrorCard
      error={error}
      reset={reset}
      title="Dashboard Error"
      message="Something went wrong loading your scan history. Please try again or return home."
      secondaryLabel="Go Home"
      secondaryHref="/"
    />
  );
}
