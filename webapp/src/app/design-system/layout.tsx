import type { ReactNode } from "react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Design System · alpo",
  description:
    "alpo.ai editorial design system — tokens, components, and brand. The source of truth for every surface in the product.",
  robots: { index: false, follow: false },
};

export default function DesignSystemLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <main className="bg-[var(--bg)] min-h-full">
      <div className="max-w-[1200px] mx-auto px-6 sm:px-10 md:px-12 pt-14 pb-24">
        {children}
      </div>
      <footer className="max-w-[1200px] mx-auto px-6 sm:px-10 md:px-12 pb-16">
        <div className="border-t border-[var(--rule-2)] pt-8 flex items-center justify-between font-mono text-[11px] text-[var(--ink-3)]">
          <span>alpo · design system · v0.1</span>
          <span>
            Source:{" "}
            <a
              href="https://claude.ai/design"
              target="_blank"
              rel="noreferrer"
              className="text-[var(--ink)] font-semibold hover:underline"
            >
              claude.ai/design
            </a>
          </span>
        </div>
      </footer>
    </main>
  );
}
