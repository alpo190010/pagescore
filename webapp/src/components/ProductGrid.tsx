"use client";

import { memo } from "react";
import { PackageIcon, SidebarSimpleIcon } from "@phosphor-icons/react";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import { type FreeResult, scoreColorTintBg, scoreColorText } from "@/lib/analysis";

/* ══════════════════════════════════════════════════════════════
   ProductGrid — Collapsible product sidebar
   Expanded: full cards with thumbnail + name + status
   Collapsed: narrow rail with just thumbnails
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
  collapsed: boolean;
  onToggleCollapse: () => void;
}

/* ── Memoized product card — only re-renders when its own props change ── */
const ProductCard = memo(function ProductCard({
  product,
  index,
  isSelected,
  isAnalyzing,
  cachedResult,
  collapsed,
  onSelectProduct,
}: {
  product: Product;
  index: number;
  isSelected: boolean;
  isAnalyzing: boolean;
  cachedResult: FreeResult | undefined;
  collapsed: boolean;
  onSelectProduct: (index: number) => void;
}) {
  /* ── Collapsed: thumbnail-only buttons ── */
  if (collapsed) {
    return (
      <Button
        type="button"
        variant="ghost"
        size="md"
        role="listitem"
        onClick={() => onSelectProduct(index)}
        className={`
          w-full flex items-center justify-center
          rounded-2xl transition-all duration-150 relative p-0 h-auto
          ${isSelected
            ? "ring-2 ring-[var(--brand)] ring-offset-2 ring-offset-[var(--surface)]"
            : "hover:ring-2 hover:ring-[var(--outline-variant)] hover:ring-offset-2 hover:ring-offset-[var(--surface)]"
          }
        `}
        aria-current={isSelected ? "true" : undefined}
        aria-label={product.slug.replace(/-/g, " ")}
        title={product.slug.replace(/-/g, " ")}
      >
        <div className="w-16 h-16 rounded-2xl bg-[var(--surface-container-highest)] overflow-hidden shrink-0 relative">
          {product.image && (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={product.image}
              alt={product.slug.replace(/-/g, " ")}
              className="w-full h-full object-cover peer"
              loading="lazy"
              onError={(e) => {
                (e.target as HTMLImageElement).classList.add("hidden");
              }}
            />
          )}
          <div className={`absolute inset-0 flex items-center justify-center ${product.image ? "hidden peer-[.hidden]:flex" : "flex"}`}>
            <PackageIcon size={24} weight="regular" color="var(--outline)" />
          </div>

          {/* Analyzing spinner overlay */}
          {isAnalyzing && (
            <div className="absolute inset-0 bg-black/30 flex items-center justify-center rounded-2xl">
              <span
                className="w-5 h-5 rounded-full border-2 border-white border-t-transparent"
                style={{ animation: "spin 0.8s linear infinite" }}
              />
            </div>
          )}

          {/* Score dot */}
          {cachedResult && !isAnalyzing && (
            <div
              className="absolute -top-0.5 -right-0.5 w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-black border-2 border-[var(--surface)] font-display"
              style={{
                background: scoreColorTintBg(cachedResult.score),
                color: scoreColorText(cachedResult.score),
              }}
            >
              {cachedResult.score}
            </div>
          )}
        </div>
      </Button>
    );
  }

  /* ── Expanded: full card ── */
  return (
    <Button
      type="button"
      variant="ghost"
      size="md"
      role="listitem"
      onClick={() => onSelectProduct(index)}
      className={`cursor-pointer w-full text-left rounded-2xl transition-all duration-150 relative overflow-hidden border polish-focus-ring flex flex-col items-stretch justify-start !p-0 h-auto ${
        isSelected
          ? "border-[var(--brand)]"
          : "border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] hover:border-[var(--surface-container-high)]"
      }`}
      style={isSelected ? { background: "var(--brand-light)" } : undefined}
      aria-current={isSelected ? "true" : undefined}
      aria-label={product.slug.replace(/-/g, " ")}
    >
      <div className="flex items-start gap-4 p-4 w-full">
        {/* Thumbnail with score overlay */}
        <div className="w-16 h-16 rounded-full bg-[var(--surface-container-highest)] overflow-hidden shrink-0 relative">
          {product.image && (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={product.image}
              alt={product.slug.replace(/-/g, " ")}
              className="w-full h-full object-cover peer"
              loading="lazy"
              onError={(e) => {
                (e.target as HTMLImageElement).classList.add("hidden");
              }}
            />
          )}
          <div className={`absolute inset-0 flex items-center justify-center ${product.image ? "hidden peer-[.hidden]:flex" : "flex"}`}>
            <PackageIcon size={24} weight="regular" color="var(--outline)" />
          </div>
          {cachedResult && !isAnalyzing && (
            <div
              className="absolute inset-0 flex items-center justify-center"
              style={{ background: `color-mix(in oklch, ${scoreColorText(cachedResult.score)} 55%, transparent)` }}
            >
              <span
                className="text-white text-lg font-black font-display"
              >
                {cachedResult.score}
              </span>
            </div>
          )}
        </div>

        {/* Info column */}
        <div className="min-w-0 flex-1 flex flex-col gap-1.5">
          <p
            className="text-base font-bold text-[var(--on-surface)] line-clamp-2 break-words capitalize leading-snug font-display"
            title={product.slug.replace(/-/g, " ")}
          >
            {product.slug.replace(/-/g, " ")}
          </p>

          {isAnalyzing ? (
            <Badge variant="scanning" className="w-fit" />
          ) : cachedResult ? (
            <Badge
              variant={
                cachedResult.score >= 70
                  ? "ok"
                  : cachedResult.score >= 40
                    ? "warn"
                    : "err"
              }
              className="w-fit"
            >
              {cachedResult.score >= 70
                ? "Good"
                : cachedResult.score >= 40
                  ? "Needs work"
                  : "Critical"}{" "}
              · {cachedResult.score}/100
            </Badge>
          ) : (
            <Badge variant="muted" className="w-fit">
              Ready to scan
            </Badge>
          )}
        </div>
      </div>
    </Button>
  );
});

export default function ProductGrid({
  products,
  sortedIndices,
  selectedIndex,
  analyzingHandle,
  analyzedResults,
  onSelectProduct,
  collapsed,
  onToggleCollapse,
}: ProductGridProps) {
  return (
    <aside
      className="flex-1 min-h-0 flex flex-col"
      aria-label="Product list"
    >
      {/* Collapse toggle — only visible when the sidebar is collapsed to the 88px rail */}
      {collapsed && (
        <div className="flex items-center justify-center py-3 border-b border-[var(--border)]">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onToggleCollapse}
            aria-expanded={!collapsed}
            className="hidden md:flex w-8 h-8 rounded-xl shrink-0"
            aria-label="Expand product list"
            title="Expand product list"
          >
            <SidebarSimpleIcon
              size={18}
              weight="regular"
              color="var(--on-surface-variant)"
              style={{
                transform: "scaleX(-1)",
                transition: "transform 300ms var(--ease-out-quart)",
              }}
            />
          </Button>
        </div>
      )}

      {/* ── Product list ── */}
      <div
        className={`flex-1 ${collapsed ? "p-2 space-y-2" : "space-y-2"}`}
        role="list"
        aria-label="Products"
      >
        {sortedIndices.map((i) => (
          <ProductCard
            key={products[i].url}
            product={products[i]}
            index={i}
            isSelected={selectedIndex === i}
            isAnalyzing={analyzingHandle === products[i].slug}
            cachedResult={analyzedResults.get(products[i].slug)}
            collapsed={collapsed}
            onSelectProduct={onSelectProduct}
          />
        ))}
      </div>
    </aside>
  );
}
