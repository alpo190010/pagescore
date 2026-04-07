"use client";

import ErrorCard from "@/components/ErrorCard";

export default function AdminError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <ErrorCard
      error={error}
      reset={reset}
      title="Admin Error"
      message="Something went wrong loading the admin panel. Please try again or return home."
      secondaryLabel="Go Home"
      secondaryHref="/"
    />
  );
}
