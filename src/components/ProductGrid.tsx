"use client";

import { PackageIcon } from "@phosphor-icons/react";
import { type FreeResult, scoreColorTintBg, scoreColorText } from "@/lib/analysis";

/* ══════════════════════════════════════════════════════════════
   ProductGrid — Scrollable product card list with status badges
   ══════════════════════════════════════════════════════════════ */

interface Product {
  url: string;
  slug: string;
  image?: string;
}

export interface ProductGridProps {
  products: Product[];
  sortedIndices: number[];
  selectedIndex: number | null;
  analyzingHandle: string | null;
  analyzedResults: Map<string, FreeResult>;
  storeName: string;
  domain: string;
  onSelectProduct: (index: number) => void;
}

export default function ProductGrid({
  products,
  sortedIndices,
  selectedIndex,
  analyzingHandle,
  analyzedResults,
  storeName,
  domain,
  onSelectProduct,
}: ProductGridProps) {
  return (
    <aside
      className="w-full lg:w-[35%] lg:max-w-[420px] lg:min-w-[280px] lg:h-[calc(100vh-72px)] lg:sticky lg:top-[72px] border-b lg:border-b-0 lg:border-r border-[var(--border)] bg-[var(--surface-dim)] flex flex-col"
      aria-label="Product list"
    >
      {/* Sticky header */}
      <div className="sticky top-0 z-10 px-5 py-4 bg-[var(--surface-dim)] border-b border-[var(--border)]">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-8 h-8 rounded-xl bg-[var(--brand-light)] border border-[var(--brand-border)] flex items-center justify-center shrink-0">
            <PackageIcon size={16} weight="regular" color="var(--brand)" />
          </div>
          <div className="min-w-0">
            <h2
              className="text-base font-bold text-[var(--on-surface)] truncate leading-tight"
              style={{ fontFamily: "var(--font-manrope), Manrope, sans-serif" }}
            >
              {storeName || domain}
            </h2>
            <p className="text-xs text-[var(--on-surface-variant)]">
              {products.length} product{products.length !== 1 ? "s" : ""} found
            </p>
          </div>
        </div>
      </div>

      {/* Scrollable product list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2" role="list" aria-label="Products">
        {sortedIndices.map((i) => {
          const product = products[i];
          const isSelected = selectedIndex === i;
          const isAnalyzing = analyzingHandle === product.slug;
          const cachedResult = analyzedResults.get(product.slug);

          return (
            <button
              key={product.url}
              type="button"
              role="listitem"
              onClick={() => onSelectProduct(i)}
              className={`cursor-pointer w-full text-left p-4 rounded-2xl transition-all duration-150 relative border-2 ${
                isSelected
                  ? "border-[var(--brand)]"
                  : "border-slate-200 bg-white hover:border-slate-300"
              }`}
              style={isSelected ? { background: "var(--brand-light)" } : undefined}
              aria-current={isSelected ? "true" : undefined}
            >
              <div className="flex items-start gap-4">
                {/* Thumbnail */}
                <div className="w-16 h-16 rounded-full bg-slate-400 overflow-hidden shrink-0">
                  {product.image ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={product.image}
                      alt=""
                      className="w-full h-full object-cover"
                      loading="lazy"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <PackageIcon size={24} weight="regular" color="var(--outline)" />
                    </div>
                  )}
                </div>

                {/* Info column */}
                <div className="min-w-0 flex-1 flex flex-col gap-1.5">
                  <p
                    className="text-base font-bold text-slate-900 truncate capitalize leading-snug"
                    style={{ fontFamily: "var(--font-manrope), Manrope, sans-serif" }}
                  >
                    {product.slug.replace(/-/g, " ")}
                  </p>

                  {/* Status badge */}
                  <div className="flex items-center gap-2">
                    {isAnalyzing ? (
                      <span
                        className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide shrink-0"
                        style={{
                          fontFamily: "var(--font-manrope), Manrope, sans-serif",
                          background: "var(--surface-brand-subtle)",
                          color: "var(--brand)",
                        }}
                      >
                        <span
                          className="w-3 h-3 rounded-full border-[1.5px] border-[var(--brand)] border-t-transparent inline-block"
                          style={{ animation: "spin 0.8s linear infinite" }}
                        />
                        Scanning
                      </span>
                    ) : cachedResult ? (
                      <span
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase shrink-0"
                        style={{
                          fontFamily: "var(--font-manrope), Manrope, sans-serif",
                          background: scoreColorTintBg(cachedResult.score),
                          color: scoreColorText(cachedResult.score),
                        }}
                      >
                        Score {cachedResult.score}/100
                      </span>
                    ) : (
                      <span
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide shrink-0"
                        style={{
                          fontFamily: "var(--font-manrope), Manrope, sans-serif",
                          background: "var(--surface-muted)",
                          color: "var(--text-tertiary)",
                        }}
                      >
                        Ready to scan
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
