import DsHeader, {
  DsSection,
  DsSubhead,
} from "../_components/DsHeader";
import Swatch from "../_components/Swatch";

/* DS · 01 — Tokens & foundation.
   Mirrors /tmp/alpo-design-new/alpo/project/DS · Tokens.html 1:1.
   Swatches render with inline values so the reference reflects the literal
   hex/oklch the rest of the app uses — edit globals.css and this page
   updates alongside. */

const sections = [
  { href: "#type", label: "Type" },
  { href: "#colors", label: "Colors" },
  { href: "#score", label: "Score" },
  { href: "#spacing", label: "Spacing" },
  { href: "#radii", label: "Radii" },
  { href: "#shadows", label: "Shadows" },
];

const typeRoles = [
  {
    meta: { tag: "Display", use: "Hero. One per page." },
    sample: (
      <span className="font-serif font-normal text-[56px] leading-none tracking-[-0.02em]">
        Turn <i className="text-[var(--accent)] font-medium">revenue</i> loss
        into wins.
      </span>
    ),
    spec: "Source Serif 4 · 72/0.95 · −0.03em",
  },
  {
    meta: { tag: "H1", use: "Page title, product name" },
    sample: (
      <span className="font-serif font-normal text-[40px] leading-[1.05] tracking-[-0.02em]">
        Arrival 5&quot; Shorts
      </span>
    ),
    spec: "Source Serif 4 · 40/1.05 · 400",
  },
  {
    meta: { tag: "H2", use: "Section title" },
    sample: (
      <span className="font-serif font-semibold text-[28px] leading-[1.1] tracking-[-0.01em]">
        Issues Found
      </span>
    ),
    spec: "Source Serif 4 · 28/1.1 · 600",
  },
  {
    meta: { tag: "H3", use: "Card / group heading" },
    sample: (
      <span className="font-serif font-bold text-[20px] leading-[1.2]">
        Trust &amp; Transparency
      </span>
    ),
    spec: "Source Serif 4 · 20/1.2 · 700",
  },
  {
    meta: { tag: "Numeral", use: "Score, price, stats" },
    sample: (
      <span
        className="font-serif font-extrabold text-[42px] leading-none tracking-[-0.02em]"
        style={{ fontVariantNumeric: "tabular-nums" }}
      >
        42
      </span>
    ),
    spec: "Source Serif 4 · 42/1 · 800 · tabular",
  },
  {
    meta: { tag: "Body", use: "Long-form copy" },
    sample: (
      <span className="text-base leading-[1.55] text-[var(--ink-2)]">
        Every product page has revenue leaks. We find them in 15 seconds and
        tell you exactly what to fix.
      </span>
    ),
    spec: "Inter · 16/1.55 · 400",
  },
  {
    meta: { tag: "Body S", use: "Secondary" },
    sample: (
      <span className="text-[13px] leading-[1.55] text-[var(--ink-2)]">
        Significant gaps in reviews, structured data, and trust signals.
      </span>
    ),
    spec: "Inter · 13/1.55 · 400",
  },
  {
    meta: { tag: "Label", use: "Eyebrow, chips" },
    sample: (
      <span className="text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--ink-3)]">
        Store-wide · Applies to all
      </span>
    ),
    spec: "Inter · 10/1 · 700 · 0.1em · UPPER",
  },
  {
    meta: { tag: "Mono", use: "Spec, count, code" },
    sample: (
      <span className="font-mono text-[11px] leading-[1.5] text-[var(--ink-2)] tracking-[0.02em]">
        gymshark.com/products/arrival-5-shorts
      </span>
    ),
    spec: "JetBrains Mono · 11/1.5 · 400",
  },
];

const spacingScale = [
  ["2xs · 4", 4, "0.25rem"],
  ["xs · 8", 8, "0.5rem"],
  ["sm · 12", 12, "0.75rem"],
  ["md · 16", 16, "1rem"],
  ["lg · 20", 20, "1.25rem"],
  ["xl · 24", 24, "1.5rem"],
  ["2xl · 32", 32, "2rem"],
  ["3xl · 48", 48, "3rem"],
  ["4xl · 64", 64, "4rem"],
] as const;

const radiiScale = [
  ["xs", 4],
  ["sm", 8],
  ["md · chip", 12],
  ["lg · card", 16],
  ["xl · hero", 20],
  ["pill", 999],
] as const;

const shadows = [
  {
    name: "--shadow-subtle",
    shadow: "0 2px 8px rgba(22,19,14,.04)",
    use: "Cards at rest",
  },
  {
    name: "--shadow-brand-md",
    shadow: "0 8px 32px rgba(22,19,14,.08)",
    use: "CTAs, score cards",
  },
  {
    name: "--shadow-elevated",
    shadow: "0 25px 50px rgba(22,19,14,.06)",
    use: "App shell, modals",
  },
];

export default function TokensPage() {
  return (
    <>
      <DsHeader
        eyebrow="Alpo Design System · 01"
        title={
          <>
            Tokens &amp; <i>foundation</i>
          </>
        }
        lede={
          <>
            The shared alphabet for every surface in Alpo. Editorial cream,
            coral accent, Source Serif 4 display, Inter for UI, JetBrains
            Mono for spec labels. Tokens live on{" "}
            <code className="font-mono text-[12px] bg-[var(--bg-elev)] px-1.5 py-px rounded text-[var(--ink)]">
              :root
            </code>
            .
          </>
        }
        activeHref="/design-system/tokens"
        sections={sections}
      />

      {/* TYPE */}
      <DsSection
        id="type"
        title="Type"
        lede="Source Serif 4 carries every display, numeral, and heading. Inter handles UI copy. JetBrains Mono tags specs and eyebrow labels. Coral italic is the single tonal accent — used on one hero word, key numerals, and state color."
      >
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          {[
            {
              label: "Display · Serif",
              sample: "Aa",
              family: "Source Serif 4 · 400/500 italic",
              sampleClass: "font-serif font-normal",
            },
            {
              label: "UI · Sans",
              sample: "Aa",
              family: "Inter · 400/500/600/700/800",
              sampleClass: "font-sans font-semibold",
            },
            {
              label: "Spec · Mono",
              sample: "Aa",
              family: "JetBrains Mono · 400/500/600",
              sampleClass: "font-mono font-medium",
            },
          ].map((f) => (
            <div
              key={f.label}
              className="bg-[var(--paper)] border border-[var(--rule-2)] rounded-2xl p-6"
            >
              <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--ink-3)]">
                {f.label}
              </p>
              <p
                className={`text-5xl leading-none mt-3 mb-1.5 tracking-[-0.02em] text-[var(--ink)] ${f.sampleClass}`}
              >
                {f.sample}
              </p>
              <p className="font-mono text-[11px] text-[var(--ink)]">
                {f.family}
              </p>
            </div>
          ))}
        </div>

        <DsSubhead>Roles</DsSubhead>
        <div className="rounded-2xl overflow-hidden border border-[var(--rule-2)] divide-y divide-[var(--rule-2)]">
          {typeRoles.map(({ meta, sample, spec }) => (
            <div
              key={meta.tag}
              className="bg-[var(--paper)] px-7 py-6 grid grid-cols-1 md:grid-cols-[180px_1fr_auto] gap-6 items-center"
            >
              <div className="font-mono text-[11px] text-[var(--ink-3)] leading-[1.6]">
                <b className="block text-[var(--ink)] font-semibold uppercase tracking-[0.08em] text-[10px] mb-1">
                  {meta.tag}
                </b>
                {meta.use}
              </div>
              <div className="text-[var(--ink)]">{sample}</div>
              <div className="font-mono text-[11px] text-[var(--ink-3)] md:text-right whitespace-nowrap">
                {spec}
              </div>
            </div>
          ))}
        </div>
      </DsSection>

      {/* COLORS */}
      <DsSection
        id="colors"
        title="Colors"
        lede={
          <>
            Warm editorial neutrals (cream paper on cream surface) with a
            single coral accent. Every semantic color is derived from these
            primitives using{" "}
            <code className="font-mono text-[12px] bg-[var(--bg-elev)] px-1.5 py-px rounded text-[var(--ink)]">
              color-mix
            </code>{" "}
            so the palette stays coherent.
          </>
        }
      >
        <DsSubhead>Neutrals — warm cream</DsSubhead>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
          <Swatch token="--bg" value="#f3efe7" use="App chrome behind content" />
          <Swatch
            token="--bg-elev"
            value="#ebe5d8"
            use="Raised hover / container"
          />
          <Swatch
            token="--paper"
            value="#faf7f0"
            use="Cards, surfaces, input bg"
          />
          <Swatch
            token="--ink"
            value="#16130e"
            use="Primary text, CTAs"
            inverse
          />
        </div>

        <DsSubhead>Text tiers</DsSubhead>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
          <Swatch token="--ink" value="#16130e" use="Headings, body primary" />
          <Swatch
            token="--ink-2"
            value="#3a342a"
            use="Body secondary, lede"
          />
          <Swatch
            token="--ink-3"
            value="#6b6458"
            use="Metadata, captions"
          />
          <Swatch
            token="--rule-2"
            value="ink @ 10%"
            use="Dividers, card borders"
            chipStyle={{
              background: "rgba(22, 20, 16, 0.1)",
              border: "1px solid var(--rule-2)",
            }}
          />
        </div>

        <DsSubhead>Accent — coral</DsSubhead>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
          <Swatch
            token="--accent"
            value="oklch(.63 .18 28)"
            use={'"Revenue" italic, critical states, dollar loss'}
            chipStyle={{ background: "oklch(0.63 0.18 28)" }}
          />
          <Swatch
            token="--accent-soft"
            value="oklch(.93 .05 28)"
            use="Soft coral backgrounds"
            chipStyle={{ background: "oklch(0.93 0.05 28)" }}
          />
          <Swatch
            token="--accent-dim"
            value="oklch(.50 .18 28)"
            use="Hover / pressed coral"
            chipStyle={{ background: "oklch(0.50 0.18 28)" }}
          />
          <Swatch
            token="--accent-ink"
            value="#ffffff"
            use="On-coral text"
            chipStyle={{ background: "#ffffff" }}
          />
        </div>

        <DsSubhead>Status</DsSubhead>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-5">
          <Swatch
            token="--ok"
            value="oklch(.58 .12 150)"
            use="Score ≥ 70, passing signals"
            chipStyle={{ background: "oklch(0.58 0.12 150)" }}
          />
          <Swatch
            token="--warn"
            value="oklch(.70 .14 70)"
            use="Score 40–69, needs work"
            chipStyle={{ background: "oklch(0.70 0.14 70)" }}
          />
          <Swatch
            token="--error"
            value="= --accent"
            use="Score < 40, critical"
            chipStyle={{ background: "oklch(0.63 0.18 28)" }}
          />
          <Swatch
            token="--muted"
            value="ink @ 12%"
            use="Neutral chip, ready state"
            chipStyle={{
              background: "#ebe5d8",
              border: "1px solid var(--rule-2)",
            }}
          />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
          <StatusLine variant="ok" label="Good · 70+" />
          <StatusLine variant="warn" label="Needs work · 40–69" />
          <StatusLine variant="err" label="Critical · <40" />
        </div>
      </DsSection>

      {/* SCORE COLOR MAPPING */}
      <DsSection
        id="score"
        title="Score color"
        lede={
          <>
            Every numeric score maps to one of three tiers via{" "}
            <code className="font-mono text-[12px] bg-[var(--bg-elev)] px-1.5 py-px rounded text-[var(--ink)]">
              scoreColor()
            </code>
            . Tint-bg is the light surface, text color is the darker tone for
            the numeral.
          </>
        }
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { score: 82, label: "Good", kind: "ok" as const },
            { score: 55, label: "Needs work", kind: "warn" as const },
            { score: 42, label: "Needs work (low)", kind: "warn" as const },
            { score: 15, label: "Critical", kind: "err" as const },
          ].map((t) => (
            <div
              key={t.label}
              className="bg-[var(--paper)] border border-[var(--rule-2)] rounded-2xl p-4 text-center"
            >
              <span
                className="inline-block px-3 py-1.5 rounded-full font-serif font-extrabold text-lg mb-1.5"
                style={
                  t.kind === "ok"
                    ? {
                        background: "var(--success-light)",
                        color: "var(--success-text)",
                      }
                    : t.kind === "warn"
                      ? {
                          background: "var(--warning-light)",
                          color: "var(--warning-text)",
                        }
                      : {
                          background: "var(--error-light)",
                          color: "var(--accent)",
                        }
                }
              >
                {t.score}
              </span>
              <div className="text-[11px] text-[var(--ink-3)] font-mono">
                {t.label}
              </div>
            </div>
          ))}
        </div>
      </DsSection>

      {/* SPACING */}
      <DsSection
        id="spacing"
        title="Spacing"
        lede="4px base unit. Cards and sections favor 16 / 20 / 24 for internal padding and 32 / 48 / 64 for section rhythm."
      >
        <div className="flex flex-col gap-2.5 bg-[var(--paper)] rounded-2xl border border-[var(--rule-2)] px-6 py-5">
          {spacingScale.map(([label, px, rem]) => (
            <div
              key={label}
              className="grid grid-cols-[120px_1fr_auto] gap-6 items-center py-1.5"
            >
              <span className="font-mono text-[11px] text-[var(--ink)]">
                {label}
              </span>
              <span
                className="h-3.5 bg-[var(--ink)] rounded"
                style={{ width: `${px}px` }}
              />
              <span className="font-mono text-[11px] text-[var(--ink-3)] text-right">
                {px}px · {rem}
              </span>
            </div>
          ))}
        </div>
      </DsSection>

      {/* RADII */}
      <DsSection
        id="radii"
        title="Radii"
        lede="Cards are soft but assertive. 16–20px for cards, 12px for pills inside cards, 999px for chips and CTAs."
      >
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          {radiiScale.map(([name, px]) => (
            <div
              key={name}
              className="bg-[var(--paper)] border border-[var(--rule-2)] p-5 rounded-[14px] text-center"
            >
              <div
                className="h-[72px] bg-[var(--ink)] mb-3"
                style={{ borderRadius: px === 999 ? 999 : `${px}px` }}
              />
              <div className="font-mono text-[10px] text-[var(--ink)]">
                {name}
              </div>
              <div className="font-mono text-[10px] text-[var(--ink-3)]">
                {px === 999 ? "999px" : `${px}px`}
              </div>
            </div>
          ))}
        </div>
      </DsSection>

      {/* SHADOWS */}
      <DsSection
        id="shadows"
        title="Shadows"
        lede="Shadows are soft and brown-tinted (ink @ low alpha), never grey-black. Three levels."
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {shadows.map((s) => (
            <div
              key={s.name}
              className="bg-[var(--paper)] rounded-2xl p-7 border border-[var(--rule-2)]"
            >
              <div
                className="h-24 bg-[var(--paper)] rounded-xl mb-3.5 border border-[var(--rule-2)]"
                style={{ boxShadow: s.shadow }}
              />
              <div className="font-mono text-[11px] font-semibold text-[var(--ink)]">
                {s.name}
              </div>
              <div className="font-mono text-[10px] text-[var(--ink-3)] mt-1 leading-[1.4]">
                {s.shadow}
                <br />
                {s.use}
              </div>
            </div>
          ))}
        </div>
      </DsSection>
    </>
  );
}

function StatusLine({
  variant,
  label,
}: {
  variant: "ok" | "warn" | "err";
  label: string;
}) {
  const style =
    variant === "ok"
      ? {
          background:
            "color-mix(in srgb, var(--ok) 12%, var(--paper))",
          color: "color-mix(in srgb, var(--ok) 80%, var(--ink))",
        }
      : variant === "warn"
        ? {
            background:
              "color-mix(in srgb, var(--warn) 14%, var(--paper))",
            color: "color-mix(in srgb, var(--warn) 70%, var(--ink))",
          }
        : {
            background:
              "color-mix(in srgb, var(--accent) 8%, var(--paper))",
            color: "var(--accent)",
          };

  return (
    <div
      className="flex items-center gap-2.5 px-4 py-3.5 rounded-xl"
      style={style}
    >
      <span
        className="w-2 h-2 rounded-full"
        style={{ background: "currentColor" }}
      />
      <span className="font-mono text-[12px] font-semibold uppercase tracking-[0.06em]">
        {label}
      </span>
    </div>
  );
}
