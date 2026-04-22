import Link from "next/link";

/* Design-system hub — three-card index linking to Tokens, Components, Brand. */

const cards = [
  {
    href: "/design-system/tokens",
    eyebrow: "01 · Foundation",
    title: "Tokens",
    body: "Type scale, colors, spacing, radii, shadows, and score-tier mapping. The alphabet every surface in alpo is built from.",
  },
  {
    href: "/design-system/components",
    eyebrow: "02 · Kit",
    title: "Components",
    body: "Every element used across the landing, scan, and results views — buttons, chips, the score ring, issue cards, the dollar-loss CTA.",
  },
  {
    href: "/design-system/brand",
    eyebrow: "03 · Voice",
    title: "Brand",
    body: "Logo, wordmark, voice, principles, and iconography — the softer layer that sits on top of tokens and components.",
  },
];

export default function DesignSystemIndexPage() {
  return (
    <>
      <header>
        <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--ink-3)] mb-3">
          Alpo Design System
        </p>
        <h1 className="font-serif font-normal text-5xl sm:text-6xl md:text-7xl leading-[0.95] tracking-[-0.03em] mb-4 text-[var(--ink)]">
          One source of <i className="text-[var(--accent)] font-medium">truth</i>.
        </h1>
        <p className="text-lg text-[var(--ink-2)] max-w-[680px] mb-14">
          A living reference for every token, primitive, and principle in alpo.
          When design changes, change it here first — the components render from
          the same tokens the reference does, so the docs stay in sync.
        </p>
      </header>

      <div className="grid gap-5 md:grid-cols-3">
        {cards.map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="group block bg-[var(--paper)] border border-[var(--rule-2)] rounded-2xl p-7 transition-all hover:-translate-y-0.5 hover:shadow-[var(--shadow-card-hover)] hover:border-[color:color-mix(in_oklch,var(--ink)_25%,transparent)]"
          >
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--ink-3)] mb-3">
              {card.eyebrow}
            </p>
            <h2 className="font-serif text-[32px] font-normal tracking-[-0.02em] text-[var(--ink)] mb-3">
              {card.title}
            </h2>
            <p className="text-[14px] leading-[1.55] text-[var(--ink-2)]">
              {card.body}
            </p>
            <span className="mt-5 inline-flex items-center gap-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--ink)]">
              Explore <span className="transition-transform group-hover:translate-x-1">→</span>
            </span>
          </Link>
        ))}
      </div>
    </>
  );
}
