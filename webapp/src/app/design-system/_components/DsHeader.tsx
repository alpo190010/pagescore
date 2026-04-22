import Link from "next/link";
import type { ReactNode } from "react";

/* Shared page header for DS · Tokens / Components / Brand.
   Eyebrow + serif display headline with coral italic + lede + TOC pills. */

const tabs = [
  { href: "/design-system/tokens", label: "Tokens" },
  { href: "/design-system/components", label: "Components" },
  { href: "/design-system/brand", label: "Brand" },
];

export interface DsHeaderProps {
  eyebrow: string;
  /** The h1 content. Wrap the accent word in <i/> to get the coral italic. */
  title: ReactNode;
  lede: ReactNode;
  activeHref: string;
  /** Optional in-page anchors (Tokens/Components pages use a long TOC). */
  sections?: { href: string; label: string }[];
}

export default function DsHeader({
  eyebrow,
  title,
  lede,
  activeHref,
  sections,
}: DsHeaderProps) {
  return (
    <header>
      <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--ink-3)] mb-3">
        {eyebrow}
      </p>
      <h1 className="font-serif font-normal text-5xl sm:text-6xl md:text-7xl leading-[0.95] tracking-[-0.03em] mb-4 text-[var(--ink)] [&>i]:text-[var(--accent)] [&>i]:font-medium">
        {title}
      </h1>
      <p className="text-lg text-[var(--ink-2)] max-w-[680px] mb-6">{lede}</p>
      <nav className="flex gap-2 flex-wrap mb-14">
        {tabs.map((tab) => {
          const active = tab.href === activeHref;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`text-[13px] font-medium px-3.5 py-2 rounded-full transition-colors ${
                active
                  ? "bg-[var(--ink)] text-[var(--paper)]"
                  : "bg-[var(--bg-elev)] text-[var(--ink-2)] hover:bg-[var(--ink)] hover:text-[var(--paper)]"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
        {sections && sections.length > 0 && (
          <span
            aria-hidden
            className="hidden sm:inline-block w-px self-stretch bg-[var(--rule-2)] mx-1"
          />
        )}
        {sections?.map((s) => (
          <a
            key={s.href}
            href={s.href}
            className="text-[13px] font-medium px-3.5 py-2 rounded-full bg-[var(--bg-elev)] text-[var(--ink-2)] hover:bg-[var(--ink)] hover:text-[var(--paper)] transition-colors"
          >
            {s.label}
          </a>
        ))}
      </nav>
    </header>
  );
}

/** Section wrapper matching DS HTML layout — hairline top rule + generous padding. */
export function DsSection({
  id,
  title,
  lede,
  children,
}: {
  id: string;
  title: ReactNode;
  lede?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      className="border-t border-[var(--rule-2)] py-14 first:border-t-0 scroll-mt-6"
    >
      <h2 className="font-serif font-normal text-[36px] sm:text-[40px] leading-[1.05] tracking-[-0.02em] mb-2 text-[var(--ink)] [&>i]:text-[var(--accent)] [&>i]:font-medium">
        {title}
      </h2>
      {lede && (
        <p className="text-[15px] text-[var(--ink-2)] max-w-[640px] mb-9">
          {lede}
        </p>
      )}
      {children}
    </section>
  );
}

/** H3 heading used inside a DsSection. */
export function DsSubhead({ children }: { children: ReactNode }) {
  return (
    <h3 className="font-serif text-[22px] font-semibold tracking-[-0.01em] mt-9 mb-4 text-[var(--ink)]">
      {children}
    </h3>
  );
}
