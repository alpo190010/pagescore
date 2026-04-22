export function formatDate(
  iso: string | null,
  opts?: { includeYear?: boolean },
): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso.includes("T") ? iso : iso + "T00:00:00");
    const fmt: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
    if (opts?.includeYear !== false) fmt.year = "numeric";
    return d.toLocaleDateString("en-US", fmt);
  } catch {
    return "—";
  }
}
