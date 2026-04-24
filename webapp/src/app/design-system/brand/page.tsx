"use client";

import DsHeader, {
  DsSection,
} from "../_components/DsHeader";
import {
  StarIcon,
  ShieldCheckIcon,
  LightningIcon,
  TruckIcon,
  GlobeIcon,
  CoinIcon,
  ChartBarIcon,
  CheckCircleIcon,
} from "@phosphor-icons/react";

/* DS · 03 — Brand & voice.
   Logo locks, wordmark rules, voice cards, principles, iconography style. */

const sections = [
  { href: "#logo", label: "Logo" },
  { href: "#voice", label: "Voice" },
  { href: "#principles", label: "Principles" },
  { href: "#icons", label: "Iconography" },
];

function LogoMark({ color = "var(--ink)" }: { color?: string }) {
  return (
    <svg width={56} height={56} viewBox="0 0 164 164" aria-hidden>
      <circle
        cx="82"
        cy="78"
        r="32"
        fill={color}
        fillOpacity={color === "#fff" ? 0.15 : 0.08}
        stroke={color}
        strokeWidth="3"
      />
      <circle cx="73" cy="74" r="3.5" fill={color} />
      <circle cx="91" cy="74" r="3.5" fill={color} />
      <path
        d="M74 90 Q82 91 90 90"
        fill="none"
        stroke={color}
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M106 102 L114.5 110.5"
        stroke={color}
        strokeWidth="5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function LogoLock({ color = "var(--ink)" }: { color?: string }) {
  return (
    <div className="flex items-center gap-3" style={{ color }}>
      <LogoMark color={color} />
      <span
        className="font-serif font-medium text-[38px] tracking-[-0.02em]"
        style={{ color }}
      >
        alpo
      </span>
    </div>
  );
}

const voiceCards = [
  {
    title: "Specific, not generic",
    body: "Name the number, the lift, the action. Vague copy feels like every other tool.",
    example: (
      <>
        Going from 0→5 reviews delivers a{" "}
        <i className="text-[var(--accent)] font-medium">270%</i> conversion
        lift.
      </>
    ),
    avoid: '"Reviews help your conversion rate."',
  },
  {
    title: "Verbs over nouns",
    body: "Sentences earn their keep. Cut adjectives; keep action words.",
    example: (
      <>
        Turn <i className="text-[var(--accent)] font-medium">revenue</i> loss
        into wins.
      </>
    ),
    avoid: '"An AI-powered analytics platform."',
  },
  {
    title: "One italic per screen",
    body: "The coral italic is a spotlight. Overuse dilutes it. One word per hero, one word per card title.",
    example: (
      <>
        You&rsquo;re losing{" "}
        <i className="text-[var(--accent)] font-medium">$2,140</i> per 1,000
        visitors.
      </>
    ),
    avoid: '"You\'re losing $2,140 today." (every word italic)',
  },
  {
    title: "Diagnose, don't scold",
    body: "We find problems without blame. The merchant already feels behind — our job is to be the competent friend.",
    example: <>No visible reviews. Here&rsquo;s the 15-minute fix.</>,
    avoid: '"You\'re missing critical social proof!"',
  },
];

const principles = [
  {
    num: "01",
    title: "Editorial, not enterprise",
    body: "Cream paper, serif display, generous whitespace. We're a magazine feature about your store, not a SaaS dashboard.",
  },
  {
    num: "02",
    title: "One accent, used sparingly",
    body: "Coral is a scalpel, not a paintbrush. One italic word per screen; one coral surface per view.",
  },
  {
    num: "03",
    title: "Numbers do the talking",
    body: "Every claim pairs with a specific number — a score, a percentage, a dollar amount. Vague proof is no proof.",
  },
  {
    num: "04",
    title: "Soft shapes, sharp ideas",
    body: "Pills, rounded cards, warm shadows. The shapes disarm; the copy confronts.",
  },
];

export default function BrandPage() {
  return (
    <>
      <DsHeader
        eyebrow="Alpo Design System · 03"
        title={
          <>
            Brand &amp; <i>voice</i>
          </>
        }
        lede="Logo, wordmark, voice, principles, and iconography style — the softer layer that sits on top of tokens and components."
        activeHref="/design-system/brand"
        sections={sections}
      />

      {/* LOGO */}
      <DsSection
        id="logo"
        title={<>Logo &amp; wordmark</>}
        lede='A friendly magnifier-face: a loupe that looks back. The mark always pairs with the "alpo" wordmark set in Source Serif 4 at 500.'
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-[var(--paper)] border border-[var(--rule-2)] rounded-2xl p-10 flex items-center justify-center min-h-[180px]">
            <LogoLock color="var(--ink)" />
          </div>
          <div className="bg-[var(--ink)] rounded-2xl p-10 flex items-center justify-center min-h-[180px]">
            <LogoLock color="#fff" />
          </div>
          <div
            className="rounded-2xl p-10 flex items-center justify-center min-h-[180px]"
            style={{ background: "var(--accent)" }}
          >
            <LogoLock color="#fff" />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
          <div className="font-mono text-[11px] text-[var(--ink-3)] px-2">
            <b className="block text-[var(--ink)] font-semibold text-[10px] uppercase tracking-[0.1em] mb-0.5">
              Default
            </b>
            Ink mark on cream. Primary.
          </div>
          <div className="font-mono text-[11px] text-[var(--ink-3)] px-2">
            <b className="block text-[var(--ink)] font-semibold text-[10px] uppercase tracking-[0.1em] mb-0.5">
              Inverse
            </b>
            White mark on ink. Dark CTA cards, footer.
          </div>
          <div className="font-mono text-[11px] text-[var(--ink-3)] px-2">
            <b className="block text-[var(--ink)] font-semibold text-[10px] uppercase tracking-[0.1em] mb-0.5">
              Coral
            </b>
            White on coral. Brand moments only.
          </div>
        </div>

        <div className="mt-8 p-6 bg-[var(--paper)] border border-[var(--rule-2)] rounded-2xl">
          <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--ink-3)] mb-3.5">
            Clearspace &amp; minimums
          </div>
          <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr_1fr] gap-6 text-[13px] text-[var(--ink-2)] leading-[1.6]">
            <div>
              <b className="text-[var(--ink)]">Clearspace:</b> keep at least
              0.5× mark height of empty space on all sides. Never crop the
              circle.
            </div>
            <div>
              <b className="text-[var(--ink)]">Min size:</b> 24px mark / 14px
              wordmark.
            </div>
            <div>
              <b className="text-[var(--ink)]">Gap:</b> wordmark sits 0.3×
              mark-height to the right.
            </div>
          </div>
        </div>
      </DsSection>

      {/* VOICE */}
      <DsSection
        id="voice"
        title="Voice"
        lede="Confident diagnostician, not a motivator. We speak in specific numbers, short sentences, and the occasional italicized verb."
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {voiceCards.map((card) => (
            <div
              key={card.title}
              className="bg-[var(--paper)] border border-[var(--rule-2)] rounded-2xl p-6"
            >
              <h3 className="font-serif font-semibold text-[20px] tracking-[-0.01em] mb-2 text-[var(--ink)]">
                {card.title}
              </h3>
              <p className="text-[13px] text-[var(--ink-2)] mb-3 leading-[1.55]">
                {card.body}
              </p>
              <div className="font-serif font-medium text-[18px] leading-[1.35] text-[var(--ink)] px-4 py-3.5 bg-[var(--bg)] rounded-[10px] border border-[var(--rule-2)]">
                {card.example}
              </div>
              <div className="text-[12px] text-[var(--ink-3)] mt-2.5 font-mono">
                <b className="text-[var(--ink-2)] font-semibold">Avoid:</b>{" "}
                {card.avoid}
              </div>
            </div>
          ))}
        </div>
      </DsSection>

      {/* PRINCIPLES */}
      <DsSection
        id="principles"
        title="Principles"
        lede="Four rules that settle design arguments."
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {principles.map((p) => (
            <div
              key={p.num}
              className="bg-[var(--paper)] border border-[var(--rule-2)] rounded-2xl p-[22px]"
            >
              <div className="font-serif font-extrabold text-[28px] text-[var(--accent)] leading-none mb-2.5">
                {p.num}
              </div>
              <h3 className="font-serif font-bold text-[16px] m-0 mb-1.5 text-[var(--ink)]">
                {p.title}
              </h3>
              <p className="text-[13px] text-[var(--ink-2)] m-0 leading-[1.55]">
                {p.body}
              </p>
            </div>
          ))}
        </div>
      </DsSection>

      {/* ICONS */}
      <DsSection
        id="icons"
        title="Iconography"
        lede={
          <>
            Phosphor Fill at 20–24px. Rendered in{" "}
            <code className="font-mono text-[12px] bg-[var(--bg-elev)] px-1.5 py-px rounded text-[var(--ink)]">
              --ink-2
            </code>{" "}
            inside a 40×40{" "}
            <code className="font-mono text-[12px] bg-[var(--bg-elev)] px-1.5 py-px rounded text-[var(--ink)]">
              --bg-elev
            </code>{" "}
            tile (r14) or a 24×24 tier-tinted tile (r12).
          </>
        }
      >
        <div className="grid grid-cols-4 md:grid-cols-8 gap-2.5">
          {[
            StarIcon,
            ShieldCheckIcon,
            LightningIcon,
            TruckIcon,
            GlobeIcon,
            CoinIcon,
            ChartBarIcon,
            CheckCircleIcon,
          ].map((Icon, i) => (
            <div
              key={i}
              className="aspect-square bg-[var(--paper)] border border-[var(--rule-2)] rounded-xl flex items-center justify-center text-[var(--ink-2)]"
            >
              <Icon size={22} weight="fill" />
            </div>
          ))}
        </div>
      </DsSection>
    </>
  );
}
