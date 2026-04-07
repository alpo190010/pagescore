"use client";

import ErrorCard from "@/components/ErrorCard";

export default function AdminUserDetailError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <ErrorCard
      error={error}
      reset={reset}
      title="Admin Error"
      message="Something went wrong loading user details. Please try again or go back to the users list."
      secondaryLabel="Back to Users"
      secondaryHref="/admin/users"
    />
  );
}
