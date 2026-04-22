import type { CSSProperties } from "react";

/* DS · Tokens → `.swatch`. Color chip + meta block showing the token name,
   hex/oklch value, and usage hint. */

export interface SwatchProps {
  token: string;
  value: string;
  use: string;
  /** CSS color/background to render on the chip. Defaults to `value`. */
  chipStyle?: CSSProperties;
  /** When the chip fill is dark, swap the meta block to use paper text. */
  inverse?: boolean;
}

export default function Swatch({
  token,
  value,
  use,
  chipStyle,
  inverse = false,
}: SwatchProps) {
  return (
    <div className="rounded-[14px] overflow-hidden border border-[var(--rule-2)] bg-[var(--paper)]">
      <div
        className="h-24 flex items-end p-3"
        style={chipStyle ?? { background: value }}
      />
      <div
        className={`px-3.5 pt-3 pb-3.5 font-mono text-[10px] leading-[1.5] ${
          inverse
            ? "bg-[#16130e] text-[color:rgba(255,255,255,.7)]"
            : "text-[var(--ink-3)]"
        }`}
      >
        <span
          className={`block text-[11px] font-semibold mb-0.5 ${
            inverse ? "text-white" : "text-[var(--ink)]"
          }`}
        >
          {token}
        </span>
        <span className="block">{value}</span>
        <span
          className={`block mt-1 font-sans text-[11px] leading-[1.4] ${
            inverse ? "text-[color:rgba(255,255,255,.7)]" : "text-[var(--ink-2)]"
          }`}
        >
          {use}
        </span>
      </div>
    </div>
  );
}
