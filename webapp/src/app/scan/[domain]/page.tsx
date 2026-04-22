"use client";

import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import { useParams, useRouter, useSearchParams, usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import { WarningCircleIcon, PackageIcon, StorefrontIcon } from "@phosphor-icons/react";
import Button from "@/components/ui/Button";
import ProductListings from "@/components/ProductListings";
import StoreHealthResults from "@/components/StoreHealthResults";
import { API_URL } from "@/lib/api";
import { authFetch } from "@/lib/auth-fetch";
import { type FreeResult, type StoreAnalysisData, parseAnalysisResponse } from "@/lib/analysis";

type ScanTab = "products" | "health";

/* ═══════════════════════════════════════════════════════════════
   /scan/[domain] — Product discovery + split-view analysis
   URL arrives as domain only (e.g. /scan/example.com).
   Discovers products via the FastAPI discover-products endpoint, then renders
   the ProductListings split-view.
   ═══════════════════════════════════════════════════════════════ */

interface Product {
  url: string;
  slug: string;
  image?: string;
}

type ScanPhase = "discovering" | "ready" | "error" | "empty";

const delay = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

function ScanPageContent() {
  const params = useParams<{ domain: string }>();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { status } = useSession();
  const initialSku = searchParams.get("sku") || "";
  const rawDomain = params.domain ?? "";
  const domain = decodeURIComponent(rawDomain);

  const handleSkuChange = useCallback(
    (sku: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (sku) params.set("sku", sku);
      else params.delete("sku");
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  /* ── Active tab (URL-synced via ?view=health|products) ── */
  const initialTab: ScanTab = searchParams.get("view") === "health" ? "health" : "products";
  const [activeTab, setActiveTab] = useState<ScanTab>(initialTab);

  // Keep activeTab in sync with URL changes (back/forward button, external nav).
  useEffect(() => {
    const view = searchParams.get("view");
    setActiveTab(view === "health" ? "health" : "products");
  }, [searchParams]);

  const handleTabChange = useCallback(
    (tab: ScanTab) => {
      setActiveTab(tab);
      const params = new URLSearchParams(searchParams.toString());
      if (tab === "health") params.set("view", "health");
      else params.delete("view");
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const [phase, setPhase] = useState<ScanPhase>("discovering");
  const [products, setProducts] = useState<Product[]>([]);
  const [storeName, setStoreName] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [initialAnalyses, setInitialAnalyses] = useState<
    Map<string, FreeResult> | undefined
  >(undefined);
  const [storeAnalysis, setStoreAnalysis] = useState<StoreAnalysisData | null>(null);
  const [refreshingStore, setRefreshingStore] = useState(false);
  const [takingLong, setTakingLong] = useState(false);
  const autoPopulatedStoreHealthRef = useRef(false);

  // Reset auto-populate guard on domain change so each new store gets a chance.
  useEffect(() => {
    autoPopulatedStoreHealthRef.current = false;
  }, [domain]);

  const handleRefreshStoreAnalysis = useCallback(async () => {
    if (refreshingStore) return;
    setRefreshingStore(true);
    try {
      const res = await authFetch(
        `${API_URL}/store/${encodeURIComponent(domain)}/refresh-analysis`,
        { method: "POST" },
      );
      if (!res.ok) {
        console.warn("Store analysis refresh failed:", res.status);
        return;
      }
      const data = (await res.json()) as StoreAnalysisData;
      setStoreAnalysis(data);
    } catch (err) {
      console.warn("Store analysis refresh error:", err);
    } finally {
      setRefreshingStore(false);
    }
  }, [domain, refreshingStore]);

  // Auto-populate Store Health when an authenticated user lands on a scan page
  // whose cache has products but no StoreAnalysis row yet (e.g., scanned
  // anonymously before, or scanned before this feature existed).
  useEffect(() => {
    if (phase !== "ready") return;
    if (storeAnalysis) return;
    if (status !== "authenticated") return;
    if (autoPopulatedStoreHealthRef.current) return;
    autoPopulatedStoreHealthRef.current = true;
    handleRefreshStoreAnalysis();
  }, [phase, storeAnalysis, status, handleRefreshStoreAnalysis]);

  // Show "taking longer" feedback after 10s in discovering phase
  useEffect(() => {
    if (phase !== "discovering") {
      setTakingLong(false);
      return;
    }
    const timer = setTimeout(() => setTakingLong(true), 10_000);
    return () => clearTimeout(timer);
  }, [phase]);

  const discoverProducts = useCallback(async (signal?: AbortSignal) => {
    setPhase("discovering");
    setErrorMessage("");

    const url = `https://${domain}`;

    /* ── Cache-first: check DB via /api/store before hitting discover-products ── */
    try {
      const [cacheRes] = await Promise.all([
        authFetch(`${API_URL}/store/${encodeURIComponent(domain)}`, { signal }),
        delay(600), // D009: minimum 600ms in discovering phase
      ]);

      if (cacheRes.ok) {
        const data = await cacheRes.json();
        const cachedProducts: Product[] = data.products ?? [];
        const analyses: Record<string, Record<string, unknown>> =
          data.analyses ?? {};

        if (cachedProducts.length > 0) {
          const analysesMap = new Map<string, FreeResult>();
          for (const product of cachedProducts) {
            const dbEntry = analyses[product.url];
            if (dbEntry) {
              analysesMap.set(
                product.slug,
                parseAnalysisResponse(dbEntry as Record<string, unknown>),
              );
            }
          }

          setProducts(cachedProducts);
          setStoreName(data.store?.name || domain);
          if (analysesMap.size > 0) setInitialAnalyses(analysesMap);
          if (data.storeAnalysis) setStoreAnalysis(data.storeAnalysis);
          setPhase("ready");
          return;
        }
      }
      // 404 or empty products → fall through to discover-products
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      // Cache check failed (network error, etc.) — fall through to discover-products
    }

    /* ── Fallback: discover products via API ── */
    try {
      const res = await fetch(`${API_URL}/discover-products`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
        signal,
      });
      const data = await res.json();

      if (data.isProductPage) {
        const productPath = new URL(url).pathname;
        const slug = productPath.split("/").filter(Boolean).pop() || "product";
        setProducts([{ url, slug, image: "" }]);
        setStoreName(data.storeName || domain);
        setPhase("ready");
      } else if (data.products?.length > 0) {
        setProducts(data.products);
        setStoreName(data.storeName || domain);
        setStoreAnalysis(data.storeAnalysis ?? null);
        setPhase("ready");
      } else {
        setProducts([]);
        setPhase("empty");
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setErrorMessage("Failed to discover products. Please try again.");
      setPhase("error");
    }
  }, [domain]);

  // Discover products once session resolves (works for both auth and anon)
  useEffect(() => {
    if (status === "loading") return;
    if (!domain) return;

    const controller = new AbortController();

    // 45 s safety timeout — transition to error if discovery hangs
    const timeout = setTimeout(() => {
      controller.abort();
      setPhase("error");
      setErrorMessage(
        "Discovery is taking too long. The site may be unreachable.",
      );
    }, 45_000);

    discoverProducts(controller.signal).finally(() => clearTimeout(timeout));

    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [status, domain, discoverProducts]);

  /* ── Session loading — show spinner while auth resolves ── */
  if (status === "loading") {
    return (
      <div className="min-h-screen bg-[var(--bg)]">
        <div className="flex flex-col items-center justify-center min-h-screen px-6">
          <div className="inline-flex items-center gap-2.5 px-5 py-3 rounded-full bg-[var(--surface)] border border-[var(--border)]" style={{ boxShadow: "var(--shadow-subtle)" }}>
            <div className="w-4 h-4 rounded-full border-2 border-[var(--brand)] border-t-transparent" style={{ animation: "spin 0.8s linear infinite" }} />
            <span className="text-sm font-medium text-[var(--text-secondary)]">Loading…</span>
          </div>
        </div>
      </div>
    );
  }

  /* ── All non-loading phases share a single return so the aria-live region persists across transitions ── */
  return (
    <div className="h-full bg-[var(--bg)] flex flex-col">
      {/* Screen-reader announcements for phase transitions */}
      <div aria-live="polite" className="sr-only">
        {phase === "discovering" ? `Discovering products…${takingLong ? " This is taking longer than expected." : ""}` : phase === "error" ? "An error occurred." : phase === "empty" ? "No products found." : phase === "ready" ? "Products loaded." : ""}
      </div>

      {/* ── Discovering state ── */}
      {phase === "discovering" && (
        <div className="flex flex-col items-center justify-center h-full px-6">
          <div className="inline-flex items-center gap-2.5 px-5 py-3 rounded-full bg-[var(--surface)] border border-[var(--border)]" style={{ boxShadow: "var(--shadow-subtle)" }}>
            <div className="w-4 h-4 rounded-full border-2 border-[var(--brand)] border-t-transparent" style={{ animation: "spin 0.8s linear infinite" }} />
            <span className="text-sm font-medium text-[var(--text-secondary)]">Finding products on {domain}…</span>
          </div>
          {takingLong && (
            <p className="mt-4 text-sm text-[var(--text-tertiary)] animate-in fade-in">
              This is taking longer than expected. Hang tight…
            </p>
          )}
        </div>
      )}

      {/* ── Error / Empty state ── */}
      {(phase === "error" || phase === "empty") && (
        <div className="flex flex-col items-center justify-center h-full px-6 text-center">
          <div className="w-14 h-14 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--border)] flex items-center justify-center mb-4" style={{ animation: "fade-in-up 400ms var(--ease-out-quart) both" }}>
            {phase === "error" ? (
              <WarningCircleIcon size={24} weight="regular" color="var(--error)" />
            ) : (
              <PackageIcon size={24} weight="regular" color="var(--on-surface-variant)" />
            )}
          </div>
          <h2 className="font-display text-xl font-bold text-[var(--on-surface)] mb-2">
            {phase === "error" ? "Something went wrong" : "No products found"}
          </h2>
          <p className="text-sm text-[var(--on-surface-variant)] max-w-sm mb-5 leading-relaxed break-words">
            {phase === "error" ? errorMessage : `We couldn't find any products on ${domain}. Try a different store URL.`}
          </p>
          <div className="flex gap-3">
            {phase === "error" && (
              <Button type="button" variant="primary" size="sm" disabled={false} onClick={() => discoverProducts()}>
                Retry
              </Button>
            )}
            <Button type="button" variant="secondary" size="sm" onClick={() => router.push("/")}>
              Try Another URL
            </Button>
          </div>
        </div>
      )}

      {/* ── Ready — tab bar + split-view / store health ── */}
      {phase === "ready" && (
        <>
          {/* Tab bar */}
          <nav
            className="shrink-0 border-b border-[var(--border)] bg-[var(--surface)]"
            aria-label="Scan views"
          >
            <div className="flex items-center gap-1 px-3 py-2 max-w-[1400px] mx-auto">
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "health"}
                onClick={() => handleTabChange("health")}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]/40 ${
                  activeTab === "health"
                    ? "bg-[var(--ink)] text-[var(--paper)]"
                    : "text-[var(--on-surface-variant)] hover:bg-[var(--surface-container-low)]"
                }`}
              >
                <StorefrontIcon size={14} weight="fill" />
                Store Health
                {storeAnalysis && (
                  <span
                    className="tabular-nums text-xs font-bold"
                    style={{ opacity: activeTab === "health" ? 0.7 : 0.5 }}
                  >
                    {storeAnalysis.score}
                  </span>
                )}
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "products"}
                onClick={() => handleTabChange("products")}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]/40 ${
                  activeTab === "products"
                    ? "bg-[var(--ink)] text-[var(--paper)]"
                    : "text-[var(--on-surface-variant)] hover:bg-[var(--surface-container-low)]"
                }`}
              >
                <PackageIcon size={14} weight="fill" />
                Products
                {products.length > 0 && (
                  <span
                    className="tabular-nums text-xs font-bold"
                    style={{ opacity: activeTab === "products" ? 0.7 : 0.5 }}
                  >
                    {products.length}
                  </span>
                )}
              </button>
            </div>
          </nav>

          {/* Tab content */}
          <div className="flex-1 min-h-0">
            {activeTab === "products" && (
              <ProductListings
                products={products}
                storeName={storeName}
                domain={domain}
                initialSku={initialSku}
                onSkuChange={handleSkuChange}
                initialAnalyses={initialAnalyses}
                storeAnalysis={storeAnalysis}
                onRefreshStoreAnalysis={handleRefreshStoreAnalysis}
                refreshingStoreAnalysis={refreshingStore}
              />
            )}
            {activeTab === "health" && storeAnalysis && (
              <StoreHealthResults
                storeAnalysis={storeAnalysis}
                domain={domain}
                storeName={storeName}
                onRefresh={handleRefreshStoreAnalysis}
                refreshing={refreshingStore}
                onBackToProducts={() => handleTabChange("products")}
              />
            )}
            {activeTab === "health" && !storeAnalysis && (
              <div className="h-full flex flex-col items-center justify-center px-6 text-center">
                {refreshingStore ? (
                  <>
                    <div
                      className="w-10 h-10 rounded-full border-2 border-[var(--brand)] border-t-transparent mb-4"
                      style={{ animation: "spin 0.8s linear infinite" }}
                      aria-hidden="true"
                    />
                    <h2 className="font-display text-lg font-bold text-[var(--on-surface)] mb-1">
                      Analyzing store health…
                    </h2>
                    <p className="text-sm text-[var(--on-surface-variant)] max-w-sm">
                      Running 7 storefront-level checks. This usually takes 15–30 seconds.
                    </p>
                  </>
                ) : status !== "authenticated" ? (
                  <>
                    <div
                      className="w-14 h-14 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--border)] flex items-center justify-center mb-4"
                    >
                      <StorefrontIcon size={24} weight="regular" color="var(--on-surface-variant)" />
                    </div>
                    <h2 className="font-display text-xl font-bold text-[var(--on-surface)] mb-2">
                      Sign in to see Store Health
                    </h2>
                    <p className="text-sm text-[var(--on-surface-variant)] max-w-sm mb-5 leading-relaxed">
                      Store-wide analysis is available to signed-in users. It runs once per store and covers checkout, shipping, trust, page speed, and more.
                    </p>
                  </>
                ) : (
                  <>
                    <div
                      className="w-14 h-14 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--border)] flex items-center justify-center mb-4"
                    >
                      <StorefrontIcon size={24} weight="regular" color="var(--on-surface-variant)" />
                    </div>
                    <h2 className="font-display text-xl font-bold text-[var(--on-surface)] mb-2">
                      No store health data yet
                    </h2>
                    <p className="text-sm text-[var(--on-surface-variant)] max-w-sm mb-5 leading-relaxed">
                      Run a scan to get storefront-level insights for this domain.
                    </p>
                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      onClick={handleRefreshStoreAnalysis}
                    >
                      Run store scan
                    </Button>
                  </>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default function ScanPage() {
  return (
    <Suspense
      fallback={
        <div className="h-full bg-[var(--bg)] flex flex-col items-center justify-center px-6">
          <div className="inline-flex items-center gap-2.5 px-5 py-3 rounded-full bg-[var(--surface)] border border-[var(--border)]" style={{ boxShadow: "var(--shadow-subtle)" }}>
            <div className="w-4 h-4 rounded-full border-2 border-[var(--brand)] border-t-transparent" style={{ animation: "spin 0.8s linear infinite" }} />
            <span className="text-sm font-medium text-[var(--text-secondary)]">Loading…</span>
          </div>
        </div>
      }
    >
      <ScanPageContent />
    </Suspense>
  );
}
