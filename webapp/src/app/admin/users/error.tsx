"use client";

import ErrorCard from "@/components/ErrorCard";

export default function AdminUsersError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <ErrorCard
      error={error}
      reset={reset}
      title="Admin Error"
      message="Something went wrong loading user management. Please try again or go back to the admin panel."
      secondaryLabel="Back to Admin"
      secondaryHref="/admin"
    />
  );
}
