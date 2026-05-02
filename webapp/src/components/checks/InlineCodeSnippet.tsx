"use client";

import { useCallback, useState } from "react";
import { CheckIcon, CopyIcon } from "@phosphor-icons/react";

/* ══════════════════════════════════════════════════════════════
   InlineCodeSnippet — compact <pre> block with a Copy button.
   Used inside check-row disclosure drawers (storewide + product).
   ══════════════════════════════════════════════════════════════ */

export default function InlineCodeSnippet({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API unavailable — silently no-op.
    }
  }, [code]);

  return (
    <div
      className="relative rounded-[10px] font-mono text-[11.5px] leading-[1.55] overflow-x-auto"
      style={{
        background: "var(--code-bg)",
        color: "var(--code-fg)",
        border: "1px solid var(--code-border)",
      }}
    >
      <button
        type="button"
        onClick={handleCopy}
        className="absolute top-2 right-2 inline-flex items-center gap-1 rounded-[6px] px-2 py-1 text-[10.5px] font-bold transition-opacity"
        style={{
          background: "var(--code-button-bg)",
          color: "var(--code-button-fg)",
          border: "1px solid var(--code-button-border)",
          letterSpacing: "0.04em",
        }}
        aria-label={copied ? "Copied" : "Copy code"}
      >
        {copied ? (
          <>
            <CheckIcon size={11} weight="bold" /> Copied
          </>
        ) : (
          <>
            <CopyIcon size={11} weight="bold" /> Copy
          </>
        )}
      </button>
      <pre
        className="px-3.5 py-3 pr-16 m-0 whitespace-pre-wrap"
        style={{ fontFamily: "inherit" }}
      >
        {code}
      </pre>
    </div>
  );
}
