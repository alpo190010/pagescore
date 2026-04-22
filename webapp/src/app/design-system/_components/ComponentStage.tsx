import type { ReactNode } from "react";

/* Stage card used throughout the Components reference page.
   Matches DS · Components `.comp` layout:
   - 1fr stage column with a subtle -45° stripe texture
   - 320px meta column on desktop with name / sub / tokens dl / note
   - stacks below md */

export interface ComponentStageProps {
  name: string;
  sub?: string;
  tokens?: Record<string, ReactNode>;
  note?: ReactNode;
  /** Use a flow (column-stretch) stage for lists of samples. */
  flow?: boolean;
  /** Override the stage background (e.g. a bg-elev band for on-dark buttons). */
  stageStyle?: React.CSSProperties;
  stageClassName?: string;
  children: ReactNode;
}

const stripeBg =
  "repeating-linear-gradient(-45deg, var(--paper) 0 10px, color-mix(in srgb, var(--ink) 2%, var(--paper)) 10px 11px)";

export default function ComponentStage({
  name,
  sub,
  tokens,
  note,
  flow = false,
  stageStyle,
  stageClassName = "",
  children,
}: ComponentStageProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[1fr_320px] mb-5 bg-[var(--paper)] border border-[var(--rule-2)] rounded-2xl overflow-hidden">
      <div
        className={`p-8 min-h-[140px] flex ${
          flow
            ? "flex-col gap-4 items-stretch justify-center p-6"
            : "items-center justify-center"
        } ${stageClassName}`}
        style={{ background: stripeBg, ...stageStyle }}
      >
        {children}
      </div>
      <div className="p-6 md:border-l md:border-t-0 border-t border-[var(--rule-2)] bg-[var(--paper)] font-mono text-[11px] leading-[1.6] text-[var(--ink-2)]">
        <div className="font-sans text-sm font-bold text-[var(--ink)] mb-1.5">
          {name}
        </div>
        {sub && (
          <div className="font-sans text-[12px] text-[var(--ink-3)] mb-3.5 leading-[1.5]">
            {sub}
          </div>
        )}
        {tokens && Object.keys(tokens).length > 0 && (
          <dl className="grid grid-cols-[80px_1fr] gap-x-3 gap-y-1 m-0">
            {Object.entries(tokens).map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-[var(--ink-3)] font-medium">{k}</dt>
                <dd className="m-0 text-[var(--ink)] font-semibold">{v}</dd>
              </div>
            ))}
          </dl>
        )}
        {note && (
          <div className="mt-3 pt-3 border-t border-dashed border-[var(--rule-2)] text-[10px] text-[var(--ink-3)]">
            {note}
          </div>
        )}
      </div>
    </div>
  );
}

/** Inline code token used in stage meta / note. */
export function TokenCode({ children }: { children: ReactNode }) {
  return (
    <code className="text-[var(--ink)] bg-[var(--bg-elev)] px-1.5 py-px rounded text-[10.5px] font-mono">
      {children}
    </code>
  );
}
