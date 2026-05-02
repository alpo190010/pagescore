"use client";

import type { DimensionCheck } from "@/lib/analysis/types";
import ChecksList from "@/components/checks/ChecksList";

/* ══════════════════════════════════════════════════════════════
   StoreHealthChecks — thin wrapper around the shared <ChecksList>
   primitive. The presentational logic (ChecksGroup, CheckRow,
   RuleList, InlineCodeSnippet, severity ladder) lives in
   webapp/src/components/checks/ and is reused by the per-product
   page-health surface (see AnalysisResults).

   The storewide dimension detail (StoreHealthDetail) renders its
   own celebration banner separately, so we don't pass an
   allPassingMessage here — empty state stays a clean null.
   ══════════════════════════════════════════════════════════════ */

interface StoreHealthChecksProps {
  checks: DimensionCheck[] | undefined;
}

export default function StoreHealthChecks({ checks }: StoreHealthChecksProps) {
  return <ChecksList checks={checks} />;
}
