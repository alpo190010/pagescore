"use client";

import ErrorCard from "@/components/ErrorCard";

export default function SettingsError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <ErrorCard
      error={error}
      reset={reset}
      title="Settings Error"
      message="Something went wrong loading your account settings. Please try again or go back to the dashboard."
      secondaryLabel="Go to Dashboard"
      secondaryHref="/dashboard"
    />
  );
}
