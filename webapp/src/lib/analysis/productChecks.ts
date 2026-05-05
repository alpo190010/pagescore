/**
 * productChecks.ts
 *
 * Builds a flat list of {@link DimensionCheck} entries from the rich
 * `signals` payload of a {@link FreeResult}. Each `*Checks` builder
 * mirrors one of the legacy `*Checklist` JSX functions in
 * `webapp/src/components/analysis/IssueCard.tsx` 1:1 — every
 * `<SignalRow>` in the JSX becomes one `DimensionCheck` in the output.
 *
 * The check list feeds the new "What's working / What's missing"
 * two-list layout that the products-page deep-analyze view shares
 * with the storewide dimensions.
 *
 * Severity weight scheme (mirrors storewide thresholds in
 * `severityFor`: ≥15 critical, ≥7 major, else minor):
 *
 *  - 15 (critical): foundational signals whose absence is a
 *    show-stopper for the dimension (e.g. Product schema missing,
 *    no H1, no product images, viewport meta absent).
 *  - 8  (major): high-impact secondary signals (brand, full
 *    schema offers, modern image format, sticky mobile CTA, etc.).
 *  - 3  (minor): polish / amplifier signals that primarily refine
 *    an already-working baseline.
 */
import type {
  AccessibilitySignals,
  AiDiscoverabilitySignals,
  CategoryScores,
  CheckoutSignals,
  ContentFreshnessSignals,
  CrossSellSignals,
  DescriptionSignals,
  DimensionCheck,
  FreeResult,
  ImageSignals,
  LeakCard,
  MobileCtaSignals,
  PageSpeedSignals,
  PricingSignals,
  ShippingSignals,
  SizeGuideSignals,
  SocialCommerceSignals,
  SocialProofSignals,
  StructuredDataSignals,
  TitleSignals,
  TrustSignals,
  VariantUxSignals,
} from "@/lib/analysis/types";
import {
  CATEGORY_LABELS,
  DIMENSION_GROUPS,
  PRODUCT_LEVEL_DIMENSIONS,
} from "@/lib/analysis/constants";

/* ────────────────────────────────────────────────────────────────
   Grouped output — one entry per dimension. Used by the per-product
   AnalysisResults view to render a collapsible accordion (each
   dimension is its own section with score, counts, and an inner
   What's working / What's missing list).
   ──────────────────────────────────────────────────────────────── */
export interface ProductDimensionGroup {
  /** Dimension key, e.g. "structuredData", "pageSpeed". */
  key: string;
  /** Human-readable label from `CATEGORY_LABELS`. */
  label: string;
  /** Category score 0–100 from `result.categories`. */
  score: number;
  /** Conversion-loss percent from the matching leak (0 if no leak). */
  conversionLoss: number;
  /** All checks for this dimension (passing + failing). */
  checks: DimensionCheck[];
}

/* ────────────────────────────────────────────────────────────────
   Thematic-group view — pools the per-dimension data into the five
   `DIMENSION_GROUPS` buckets (Buying Experience, Trust &
   Transparency, etc.). Drives the Score breakdown card grid in the
   product analysis surface.
   ──────────────────────────────────────────────────────────────── */
export interface ProductGroupView {
  /** Group id, e.g. "buying", "trust". */
  id: string;
  /** Group label, e.g. "Buying Experience". */
  label: string;
  /** Group's framing question from `DIMENSION_GROUPS`. */
  question: string;
  /** Average of contained dimensions' scores (0–100). */
  avgScore: number;
  /** Sum of contained dimensions' conversion-loss percent. */
  conversionLoss: number;
  /** Pooled checks across the group's dimensions. */
  checks: DimensionCheck[];
  /** Per-check dimension provenance, keyed by check `id`. */
  checkDimensionKey: Record<string, string>;
  /** The contained per-dimension groups, for sub-display. */
  dimensions: ProductDimensionGroup[];
}

/* ────────────────────────────────────────────────────────────────
   Shared helpers
   ──────────────────────────────────────────────────────────────── */

/**
 * Hook for future per-signal leak merging. Currently a no-op:
 * dimension-level fix copy lives in the `<DimensionFixCallout>`
 * banner above the missing list (rendered by `AnalysisResults`),
 * not on every failing row's expand drawer. Stamping the same
 * `leak.tip` onto every row produced repetitive expansions —
 * removed in favour of the single dimension-level callout.
 *
 * Kept as a one-liner so future work can stamp signal-specific
 * remediation per row without touching the 18 builder call sites.
 */
function applyLeakMerge(
  checks: DimensionCheck[],
  _leak: LeakCard | undefined,
): DimensionCheck[] {
  return checks;
}

/* ────────────────────────────────────────────────────────────────
   Social Proof — ported from IssueCard.tsx inline JSX (1447–1501)
   ──────────────────────────────────────────────────────────────── */
export function buildSocialProofChecks(
  sp: SocialProofSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const starInOptimalRange =
    sp.starRating !== null && sp.starRating >= 4.2 && sp.starRating <= 4.7;
  const starOutOfRangeDetail =
    sp.starRating !== null && (sp.starRating < 4.2 || sp.starRating > 4.7)
      ? "Optimal range is 4.2–4.7 stars"
      : undefined;

  const reviewCount = sp.reviewCount;
  const reviewCountDetail =
    reviewCount !== null && reviewCount < 5
      ? "Products with 5+ reviews see 270% higher conversion"
      : reviewCount !== null && reviewCount < 30
        ? "Aim for 30+ reviews for maximum impact"
        : undefined;

  const checks: DimensionCheck[] = [
    {
      id: "socialProof.reviewApp",
      label: sp.reviewApp ? `Review app: ${sp.reviewApp}` : "No review app detected",
      passed: sp.reviewApp !== null,
      weight: 8,
      remediation:
        "Install a review app (Judge.me, Loox, or Yotpo) and turn on the post-purchase email so every fulfilled order gets a review request.",
    },
    {
      id: "socialProof.starRating",
      label:
        sp.starRating !== null
          ? `Star rating: ${sp.starRating}/5`
          : "No star rating found",
      passed: sp.starRating !== null && starInOptimalRange,
      weight: 8,
      detail: starOutOfRangeDetail,
      remediation:
        sp.starRating === null
          ? "Surface your aggregate rating in the product header — most review apps expose a one-click widget to drop into the theme."
          : "Aim for 4.2–4.7. If you're below, reply publicly to negative reviews and follow up with happy customers; if you're above 4.7, ask all buyers — perfect averages read as fake.",
    },
    {
      id: "socialProof.reviewCount",
      label:
        reviewCount !== null ? `${reviewCount} reviews` : "No review count found",
      passed: reviewCount !== null && reviewCount >= 30,
      weight: 8,
      detail: reviewCountDetail,
      remediation:
        "Run a 3 / 14 / 30-day post-delivery email sequence asking for a review. Offer a small incentive (loyalty points or 5% off) on the second touch.",
    },
    {
      id: "socialProof.photoReviews",
      label: "Photo reviews",
      passed: sp.hasPhotoReviews,
      weight: 8,
      detail: !sp.hasPhotoReviews ? "Photo reviews boost conversion by 106%" : undefined,
      remediation:
        "Offer 50–100 loyalty points or a coupon for photo reviews — every major review app has a built-in photo-incentive flow.",
    },
    {
      id: "socialProof.videoReviews",
      label: "Video reviews",
      passed: sp.hasVideoReviews,
      weight: 3,
      remediation:
        "Switch on video uploads in your review app and reach out to your most engaged customers — even one video lifts engagement on the page.",
    },
    {
      id: "socialProof.starAboveFold",
      label: "Star rating above fold",
      passed: sp.starRatingAboveFold,
      weight: 8,
      detail: !sp.starRatingAboveFold
        ? "56% of shoppers check reviews before anything else"
        : undefined,
      remediation:
        "Drop the star widget directly under the product title in the theme editor — most themes expose a 'reviews summary' block you can pin above the buy box.",
    },
    {
      id: "socialProof.reviewFiltering",
      label: "Review filtering & sorting",
      passed: sp.hasReviewFiltering,
      weight: 3,
      detail: !sp.hasReviewFiltering
        ? "Shoppers who filter reviews are 2x more likely to convert"
        : undefined,
      remediation:
        "Upgrade to a review app tier that supports filtering by rating / photo / verified-buyer — Yotpo, Stamped, and Judge.me Pro all include it.",
    },
  ];

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Structured Data — IssueCard.tsx 100–193
   ──────────────────────────────────────────────────────────────── */
export function buildStructuredDataChecks(
  sd: StructuredDataSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const requiredFields = [sd.hasName, sd.hasImage, sd.hasDescription, sd.hasOffers];
  const requiredCount = requiredFields.filter(Boolean).length;

  const offersPresent = [sd.hasPrice, sd.hasPriceCurrency, sd.hasAvailability];
  const offersCount = offersPresent.filter(Boolean).length;

  const recommendedFields = [
    sd.hasSku,
    sd.hasGtin,
    sd.hasAggregateRating,
    sd.hasPriceValidUntil,
  ];
  const recommendedCount = recommendedFields.filter(Boolean).length;

  const shippingCount = [sd.hasShippingDetails, sd.hasReturnPolicy].filter(Boolean).length;

  const errorItems: string[] = [];
  if (sd.hasCurrencyInPrice) errorItems.push("currency symbol in price value");
  if (sd.hasInvalidAvailability) errorItems.push("invalid availability value");
  if (sd.duplicateProductCount > 0)
    errorItems.push(`${sd.duplicateProductCount} duplicate Product schema(s)`);
  if (sd.jsonParseErrors > 0)
    errorItems.push(`${sd.jsonParseErrors} JSON-LD parse error(s)`);

  const checks: DimensionCheck[] = [
    {
      id: "structuredData.productSchema",
      label: sd.hasProductSchema
        ? "Product schema detected"
        : "No Product schema found",
      passed: sd.hasProductSchema,
      weight: 15,
      detail: !sd.hasProductSchema
        ? "Product schema is required for rich results in Google Shopping"
        : undefined,
      remediation:
        "Most Shopify themes ship a Product JSON-LD block — switch it on in theme settings, or paste a Product schema generator's output into theme.liquid. Validate with the Rich Results test.",
    },
    {
      id: "structuredData.requiredFields",
      label: `${requiredCount} of 4 required fields present`,
      passed: requiredCount === 4,
      weight: 8,
      detail:
        requiredCount < 4
          ? `Missing: ${[
              !sd.hasName && "name",
              !sd.hasImage && "image",
              !sd.hasDescription && "description",
              !sd.hasOffers && "offers",
            ]
              .filter(Boolean)
              .join(", ")}`
          : undefined,
      remediation:
        "Open the Product JSON-LD block in your theme and confirm `name`, `image`, `description`, and `offers` are wired to the product object — these are the four Google requires for any rich card.",
    },
    {
      id: "structuredData.offersDetail",
      label: `Offers detail: ${offersCount} of 3 (price, currency, availability)`,
      passed: offersCount === 3,
      weight: 8,
      detail:
        offersCount < 3
          ? `Missing: ${[
              !sd.hasPrice && "price",
              !sd.hasPriceCurrency && "priceCurrency",
              !sd.hasAvailability && "availability",
            ]
              .filter(Boolean)
              .join(", ")}`
          : undefined,
      remediation:
        "Inside the Offer object, populate `price`, `priceCurrency` (ISO 4217 — e.g. USD), and `availability` (`InStock` / `OutOfStock`). Without all three, Google will drop the listing from Shopping results.",
    },
    {
      id: "structuredData.brand",
      label: sd.hasBrand ? "Brand present" : "Brand missing",
      passed: sd.hasBrand && !sd.hasMissingBrand,
      weight: 8,
      detail: sd.hasMissingBrand
        ? "Brand field exists but value is empty or invalid"
        : !sd.hasBrand
          ? "Adding brand improves merchant listing quality"
          : undefined,
      remediation:
        "Add `brand: { '@type': 'Brand', name: 'Your Brand' }` to the Product JSON-LD. In Shopify, set the product's vendor field — most themes pipe vendor → brand automatically.",
    },
    {
      id: "structuredData.recommendedFields",
      label: `${recommendedCount} of 4 recommended fields (SKU, GTIN, rating, priceValidUntil)`,
      passed: recommendedCount >= 3,
      weight: 3,
      detail:
        recommendedCount < 3
          ? `Missing: ${[
              !sd.hasSku && "SKU",
              !sd.hasGtin && "GTIN",
              !sd.hasAggregateRating && "aggregateRating",
              !sd.hasPriceValidUntil && "priceValidUntil",
            ]
              .filter(Boolean)
              .join(", ")}`
          : undefined,
      remediation:
        "Wire SKU and GTIN/UPC from the variant; expose `aggregateRating` from your review app's structured data block; set `priceValidUntil` if you run scheduled discounts.",
    },
    {
      id: "structuredData.shippingReturns",
      label: `Shipping & returns: ${shippingCount} of 2`,
      passed: shippingCount === 2,
      weight: 8,
      detail:
        shippingCount < 2
          ? `Missing: ${[
              !sd.hasShippingDetails && "shippingDetails",
              !sd.hasReturnPolicy && "returnPolicy",
            ]
              .filter(Boolean)
              .join(", ")}`
          : undefined,
      remediation:
        "Add `shippingDetails` (with `shippingRate` and `deliveryTime`) and `hasMerchantReturnPolicy` to the Offer block. Google now requires both for free Shopping listings.",
    },
    {
      id: "structuredData.breadcrumbList",
      label: "BreadcrumbList schema",
      passed: sd.hasBreadcrumbList,
      weight: 3,
      detail: !sd.hasBreadcrumbList
        ? "Breadcrumbs improve search appearance and click-through rate"
        : undefined,
      remediation:
        "Render a BreadcrumbList JSON-LD block alongside Product schema (Home → Collection → Product). Most themes have this as a separate liquid include — enable it in theme settings.",
    },
    {
      id: "structuredData.organization",
      label: "Organization schema",
      passed: sd.hasOrganization,
      weight: 3,
      detail: !sd.hasOrganization
        ? "Organization schema helps Google display business info in search"
        : undefined,
      remediation:
        "Add Organization JSON-LD to the homepage layout (`name`, `url`, `logo`, `sameAs` for social profiles). One block in the master layout covers every page.",
    },
  ];

  if (errorItems.length > 0) {
    checks.push({
      id: "structuredData.errors",
      label: `${errorItems.length} error${errorItems.length > 1 ? "s" : ""} found`,
      passed: false,
      weight: 8,
      detail: errorItems.join("; "),
      remediation:
        "Run the URL through Google's Rich Results Test (search.google.com/test/rich-results) — it pinpoints which JSON-LD field is rejecting and shows the exact line. Fix one error at a time and re-test.",
    });
  }

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Checkout — IssueCard.tsx 194–394
   ──────────────────────────────────────────────────────────────── */
export function buildCheckoutChecks(
  co: CheckoutSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const liveChecked = co.reachedCheckout === true;
  const wallets = co.wallets;
  const bnpl = co.bnpl;
  const checks: DimensionCheck[] = [];

  if (liveChecked && wallets) {
    checks.push(
      {
        id: "checkout.shopPay",
        label: "Shop Pay on checkout",
        passed: wallets.shopPay,
        weight: 15,
        detail: !wallets.shopPay
          ? "Shop Pay drives a 50% checkout-to-order lift for returning buyers"
          : undefined,
      },
      {
        id: "checkout.applePay",
        label: "Apple Pay on checkout",
        passed: wallets.applePay,
        weight: 15,
        detail: !wallets.applePay
          ? "Apple Pay roughly doubles mobile checkout conversion"
          : undefined,
      },
      {
        id: "checkout.googlePay",
        label: "Google Pay on checkout",
        passed: wallets.googlePay,
        weight: 15,
        detail: !wallets.googlePay
          ? "43% of Android shoppers abandon without Google Pay"
          : undefined,
      },
      {
        id: "checkout.paypal",
        label: "PayPal on checkout",
        passed: wallets.paypal,
        weight: 8,
        detail: !wallets.paypal
          ? "PayPal reaches 400M+ active buyers globally"
          : undefined,
      },
    );
    if (wallets.amazonPay || wallets.metaPay || wallets.stripeLink) {
      checks.push({
        id: "checkout.otherWallet",
        label: "Amazon / Meta / Stripe Link wallet",
        passed: wallets.amazonPay || wallets.metaPay || wallets.stripeLink,
        weight: 3,
      });
    }
  } else {
    checks.push(
      {
        id: "checkout.acceleratedCheckout",
        label: "Shop Pay / accelerated-checkout wrapper on product page",
        passed: co.hasAcceleratedCheckout,
        weight: 15,
        detail: !co.hasAcceleratedCheckout
          ? "Accelerated checkout can boost conversion 1.7×"
          : undefined,
      },
      {
        id: "checkout.dynamicCheckoutButton",
        label: "Dynamic checkout button on product page",
        passed: co.hasDynamicCheckoutButton,
        weight: 8,
        detail: !co.hasDynamicCheckoutButton
          ? "Shows the buyer's preferred payment at checkout"
          : undefined,
      },
      {
        id: "checkout.paypalPdp",
        label: "PayPal (product page)",
        passed: co.hasPaypal,
        weight: 8,
        detail: !co.hasPaypal
          ? "PayPal reaches 400M+ active buyers globally"
          : undefined,
      },
    );
  }

  if (liveChecked && bnpl) {
    checks.push(
      {
        id: "checkout.shopPayInstallments",
        label: "Shop Pay Installments on checkout",
        passed: bnpl.shopPayInstallments,
        weight: 3,
        detail: !bnpl.shopPayInstallments
          ? "Shop Pay Installments lifts AOV for orders $50+"
          : undefined,
      },
      {
        id: "checkout.klarna",
        label: "Klarna on checkout",
        passed: bnpl.klarna,
        weight: 3,
        detail: !bnpl.klarna ? "BNPL options increase AOV by up to 45%" : undefined,
      },
      {
        id: "checkout.afterpay",
        label: "Afterpay / Clearpay on checkout",
        passed: bnpl.afterpay || bnpl.clearpay,
        weight: 3,
        detail: !(bnpl.afterpay || bnpl.clearpay)
          ? "Afterpay drives repeat purchases at 2× the rate"
          : undefined,
      },
      {
        id: "checkout.affirm",
        label: "Affirm on checkout",
        passed: bnpl.affirm,
        weight: 3,
        detail: !bnpl.affirm
          ? "Affirm reduces cart abandonment on high-AOV items"
          : undefined,
      },
    );
  } else {
    checks.push(
      {
        id: "checkout.klarnaPdp",
        label: "Klarna (product page)",
        passed: co.hasKlarna,
        weight: 3,
        detail: !co.hasKlarna ? "BNPL options increase AOV by up to 45%" : undefined,
      },
      {
        id: "checkout.afterpayPdp",
        label: "Afterpay (product page)",
        passed: co.hasAfterpay,
        weight: 3,
        detail: !co.hasAfterpay
          ? "Afterpay drives repeat purchases at 2× the rate"
          : undefined,
      },
      {
        id: "checkout.affirmPdp",
        label: "Affirm (product page)",
        passed: co.hasAffirm,
        weight: 3,
        detail: !co.hasAffirm
          ? "Affirm reduces cart abandonment on high-AOV items"
          : undefined,
      },
      {
        id: "checkout.sezzlePdp",
        label: "Sezzle (product page)",
        passed: co.hasSezzle,
        weight: 3,
        detail: !co.hasSezzle
          ? "Sezzle targets younger demographics effectively"
          : undefined,
      },
    );
  }

  if (liveChecked) {
    checks.push(
      {
        id: "checkout.guestCheckout",
        label: co.forcedAccountCreation
          ? "Forced account creation"
          : "Guest checkout supported",
        passed: co.guestCheckoutAvailable === true && !co.forcedAccountCreation,
        weight: 8,
        detail: !co.guestCheckoutAvailable
          ? "24% of shoppers abandon carts when forced to sign up"
          : undefined,
      },
      {
        id: "checkout.stepCount",
        label:
          co.checkoutStepCount === 1
            ? "One-page checkout"
            : `${co.checkoutStepCount ?? "?"}-step checkout`,
        passed: co.checkoutStepCount === 1,
        weight: 8,
        detail:
          (co.checkoutStepCount ?? 0) > 1
            ? "One-page checkouts convert 13% better than multi-step"
            : undefined,
      },
      {
        id: "checkout.discountCode",
        label: "Discount-code field on checkout",
        passed: co.hasDiscountCodeField === true,
        weight: 3,
        detail: !co.hasDiscountCodeField
          ? "Expose a code field — buyers who leave to search for codes rarely return"
          : undefined,
      },
      {
        id: "checkout.addressAutocomplete",
        label: "Address autocomplete on checkout",
        passed: co.hasAddressAutocomplete === true,
        weight: 3,
        detail: !co.hasAddressAutocomplete
          ? "Autocomplete reduces address typing by 20%"
          : undefined,
      },
    );
  }

  checks.push(
    {
      id: "checkout.paymentMethodCount",
      label: `${co.paymentMethodCount} of 5 payment methods detected on product page`,
      passed: co.paymentMethodCount >= 3,
      weight: 8,
      detail:
        co.paymentMethodCount < 3
          ? "Offer 3+ payment methods to reduce checkout friction"
          : undefined,
    },
    {
      id: "checkout.drawerCart",
      label: "Drawer / slide-out cart",
      passed: co.hasDrawerCart,
      weight: 3,
      detail: !co.hasDrawerCart ? "Drawer carts keep shoppers on the page" : undefined,
    },
    {
      id: "checkout.ajaxCart",
      label: "AJAX add-to-cart",
      passed: co.hasAjaxCart,
      weight: 3,
      detail: !co.hasAjaxCart
        ? "AJAX cart avoids disruptive page reloads"
        : undefined,
    },
    {
      id: "checkout.stickyCheckout",
      label: "Sticky checkout button",
      passed: co.hasStickyCheckout,
      weight: 3,
      detail: !co.hasStickyCheckout
        ? "Sticky buttons keep CTA visible while scrolling"
        : undefined,
    },
  );

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Pricing Psychology — IssueCard.tsx 395–479
   ──────────────────────────────────────────────────────────────── */
export function buildPricingChecks(
  pr: PricingSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const checks: DimensionCheck[] = [
    {
      id: "pricing.compareAtPrice",
      label:
        pr.hasCompareAtPrice || pr.hasStrikethroughPrice
          ? "Price anchoring detected (compare-at / strikethrough)"
          : "No price anchoring",
      passed: pr.hasCompareAtPrice || pr.hasStrikethroughPrice,
      weight: 8,
      detail:
        !(pr.hasCompareAtPrice || pr.hasStrikethroughPrice)
          ? "Strikethrough anchoring produces a 25–40% conversion lift"
          : undefined,
      remediation:
        "Set a Compare-at price on each variant in the Shopify admin — most themes auto-render it as a strikethrough next to the sale price. No code change needed.",
    },
    {
      id: "pricing.charmPricing",
      label:
        pr.priceValue != null
          ? pr.hasCharmPricing
            ? `Charm pricing detected ($${pr.priceValue})`
            : pr.isRoundPrice
              ? `Round price ($${pr.priceValue}) — consider .99 ending`
              : `Price: $${pr.priceValue}`
          : "No price extracted",
      passed: pr.hasCharmPricing,
      weight: 3,
      detail:
        !pr.hasCharmPricing && pr.isRoundPrice
          ? "MIT field experiments show 24% sales increase from .99 endings"
          : undefined,
      remediation:
        "Drop the price by one cent (e.g. $40 → $39.99). For premium positioning, prefer round numbers; for value-driven catalogs, .99 endings consistently outperform.",
    },
    {
      id: "pricing.bnplNearPrice",
      label: pr.hasBnplNearPrice
        ? "BNPL installment messaging present"
        : "No BNPL installment messaging",
      passed: pr.hasBnplNearPrice,
      weight: 8,
      detail: !pr.hasBnplNearPrice
        ? "'Pay in 4' framing increases conversion 20–35% on items over $50"
        : undefined,
      remediation:
        "Install Shop Pay Installments (free with Shopify Payments), Klarna, or Afterpay and place their messaging block directly under the price — apps include drop-in widgets for every theme.",
    },
    {
      id: "pricing.countdownTimer",
      label: pr.hasCountdownTimer
        ? "Countdown timer present"
        : "No countdown timer",
      passed: pr.hasCountdownTimer && !pr.hasFakeTimerRisk,
      weight: 3,
      detail: pr.hasFakeTimerRisk
        ? "Timer may be fake — Princeton research found ~40% of e-commerce timers are artificial"
        : !pr.hasCountdownTimer
          ? "Truthful countdown timers increase conversion up to 17.8%"
          : undefined,
      remediation: pr.hasFakeTimerRisk
        ? "Tie the timer to a real promotion end date (e.g. Hextom or Bold Sale Motivator). FTC has begun citing fake-urgency timers — the legal risk isn't worth the lift."
        : "Run a time-bound promotion (Sale ends midnight Sunday) and surface a real countdown via a Shopify timer app — Hextom Ultimate Sales Boost or Bold Sale Motivator both work.",
    },
    {
      id: "pricing.scarcityMessaging",
      label: pr.hasScarcityMessaging
        ? "Stock scarcity messaging present"
        : "No scarcity messaging",
      passed: pr.hasScarcityMessaging,
      weight: 3,
      detail: !pr.hasScarcityMessaging
        ? "Real-time stock levels ('Only 3 left') drive urgency and increase conversions"
        : undefined,
      remediation:
        "Surface real inventory below a threshold (e.g. show 'Only N left' when stock < 10). Most scarcity apps (Hurrify, Sales Pop) tie to live inventory — never hardcode a fake number.",
    },
  ];

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Product Images — IssueCard.tsx 480–555
   ──────────────────────────────────────────────────────────────── */
export function buildImagesChecks(
  im: ImageSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const altPct = Math.round(im.altTextScore * 100);

  const checks: DimensionCheck[] = [
    {
      id: "images.imageCount",
      label: `${im.imageCount} product image${im.imageCount !== 1 ? "s" : ""} detected`,
      passed: im.imageCount >= 5,
      weight: 15,
      detail:
        im.imageCount < 3
          ? "56% of shoppers explore images first — aim for 5–8 images"
          : im.imageCount < 5
            ? "Good start, but 5–8 images is optimal for conversion"
            : undefined,
      remediation:
        "Add product images covering: front / back / detail / scale-reference / packaging / lifestyle. Brief your photographer (or supplier) for at least 5 distinct angles per SKU.",
    },
    {
      id: "images.video",
      label: im.hasVideo ? "Product video present" : "No product video",
      passed: im.hasVideo,
      weight: 8,
      detail: !im.hasVideo ? "Product video increases add-to-cart by 37%" : undefined,
      remediation:
        "Upload a 15–30 second clip showing the product in use to the product gallery (Shopify supports MP4 directly). Even a phone-shot video outperforms a static gallery.",
    },
    {
      id: "images.view360",
      label: im.has360View ? "360° view available" : "No 360° view",
      passed: im.has360View,
      weight: 3,
      detail: !im.has360View ? "360° views increase conversion by 27%" : undefined,
      remediation:
        "Use a 360 spin app (Magic 360, Spinify, or WebRotate) — most accept a folder of 24–36 sequenced images. Worth the effort on hero SKUs only.",
    },
    {
      id: "images.zoom",
      label: im.hasZoom ? "Zoom/magnify enabled" : "No zoom capability",
      passed: im.hasZoom,
      weight: 3,
      detail: !im.hasZoom
        ? "42% of shoppers gauge size from images (Baymard)"
        : undefined,
      remediation:
        "Switch on hover-zoom or click-to-expand in your theme settings — modern Shopify themes (Dawn, Impulse, Prestige) include it by default. Or install Magic Zoom Plus.",
    },
    {
      id: "images.altText",
      label: `Alt text quality: ${altPct}%`,
      passed: im.altTextScore >= 0.7,
      weight: 8,
      detail:
        im.altTextScore < 0.5
          ? "Descriptive alt text increases organic traffic by 30%"
          : im.altTextScore < 0.7
            ? "Alt text is decent but could be more descriptive and unique"
            : undefined,
      remediation:
        "Edit each image in the product admin and write a unique alt text that includes the product name, color/size, and angle (e.g. 'Navy crew sweater, front view'). Avoid 'image1.jpg'.",
    },
    {
      id: "images.modernFormat",
      label: im.hasModernFormat
        ? "WebP/AVIF format detected"
        : "No modern image formats",
      passed: im.hasModernFormat,
      weight: 8,
      detail: !im.hasModernFormat
        ? "WebP/AVIF saves 25–50% file size vs JPEG"
        : undefined,
      remediation:
        "Shopify CDN auto-serves WebP — upgrade to a 2.0+ theme that emits WebP via the `image_url` filter, or install an image-optimizer app (TinyIMG, Crush.pics) to convert in bulk.",
    },
    {
      id: "images.heroQuality",
      label: im.hasHighRes
        ? "High-resolution images"
        : "No high-res images detected",
      passed: im.hasHighRes,
      weight: 3,
      detail: !im.hasHighRes
        ? "Serve images at 1000px+ width for quality zoom experience"
        : undefined,
      remediation:
        "Re-upload product images at 2000–3000px on the long edge. Shopify will downscale per breakpoint automatically; you only need to provide the high-res master.",
    },
    {
      id: "images.lifestyle",
      label: im.hasLifestyleImages
        ? "Lifestyle/context images detected"
        : "No lifestyle images detected",
      passed: im.hasLifestyleImages,
      weight: 8,
      detail: !im.hasLifestyleImages
        ? "Contextual imagery drives 38% higher conversion"
        : undefined,
      remediation:
        "Add 1–2 in-context shots: model wearing the apparel, product in a styled room, food on a plate. Repurposing UGC from Instagram (with permission) is the cheapest source.",
    },
    {
      id: "images.cdn",
      label: im.cdnHosted ? "CDN-hosted images" : "Images not on CDN",
      passed: im.cdnHosted,
      weight: 3,
      detail: !im.cdnHosted
        ? "CDN delivery improves page load and global performance"
        : undefined,
      remediation:
        "Move images off your origin server. Shopify's built-in CDN handles this for theme-uploaded assets; for third-party-hosted images, route through Cloudflare Images or imgix.",
    },
  ];

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Title & SEO — IssueCard.tsx 556–628
   ──────────────────────────────────────────────────────────────── */
export function buildTitleChecks(
  ti: TitleSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const truncatedH1 =
    ti.h1Text && ti.h1Text.length > 50 ? ti.h1Text.slice(0, 50) + "…" : ti.h1Text;

  const checks: DimensionCheck[] = [
    {
      id: "title.h1Present",
      label: ti.hasH1 ? `H1: "${truncatedH1}"` : "No H1 tag found",
      passed: ti.hasH1,
      weight: 15,
      detail: !ti.hasH1
        ? "Products with proper heading hierarchy see 12–15% better CTR"
        : undefined,
      remediation:
        "Make sure your theme's product template wraps the product name in `<h1>` (Dawn / Sense / Impulse all do this by default). Don't replace it with `<div class='product-title'>`.",
    },
    {
      id: "title.singleH1",
      label: `${ti.h1Count} H1 tag${ti.h1Count !== 1 ? "s" : ""} on page`,
      passed: ti.hasSingleH1,
      weight: 8,
      detail:
        ti.h1Count > 1
          ? "Multiple H1s confuse search engine crawlers"
          : ti.h1Count === 0
            ? "Every page needs exactly one H1"
            : undefined,
      remediation:
        "Audit the theme for stray `<h1>`s in headers, hero blocks, or section titles — demote those to `<h2>` and reserve the H1 for the product name only.",
    },
    {
      id: "title.h1Length",
      label: ti.hasH1 ? `H1 length: ${ti.h1Length} chars` : "H1 length: N/A",
      passed: ti.hasH1 && ti.h1Length <= 80,
      weight: 3,
      detail:
        ti.h1Length > 80
          ? `${ti.h1Length - 80} characters over the 80-char limit`
          : undefined,
      remediation:
        "Shorten the product name to under 80 characters. Move secondary specs (material, dimensions) into the description; keep the H1 to brand + core product type + key descriptor.",
    },
    {
      id: "title.metaTitleLength",
      label: ti.metaTitle
        ? `Meta title: ${ti.metaTitleLength} chars`
        : "No meta title found",
      passed: ti.metaTitle != null && ti.metaTitleLength <= 60,
      weight: 8,
      detail:
        ti.metaTitleLength > 60
          ? `${ti.metaTitleLength - 60} chars over SERP limit — title will be truncated`
          : undefined,
      remediation:
        "In the product's SEO section (admin → Search engine listing), write a custom title under 60 chars: `[Product] – [Key Benefit] | [Brand]`. Don't let Shopify auto-generate.",
    },
    {
      id: "title.brandInTitle",
      label: ti.hasBrandInTitle
        ? `Brand "${ti.brandName}" in title`
        : ti.brandName
          ? `Brand "${ti.brandName}" missing from title`
          : "Brand not detected",
      passed: ti.hasBrandInTitle,
      weight: 8,
      detail:
        !ti.hasBrandInTitle && ti.brandName
          ? "97% of top-performing titles include the brand"
          : undefined,
      remediation:
        "Append the brand to the meta title (e.g. 'Trino® Cozy Crew Sweater | Wool & Prince'). Easiest done in the theme's `theme.liquid` — append `| {{ shop.name }}` to `<title>`.",
    },
    {
      id: "title.keywordStuffing",
      label: ti.hasKeywordStuffing
        ? "Keyword stuffing detected"
        : "No keyword stuffing",
      passed: !ti.hasKeywordStuffing,
      weight: 8,
      detail: ti.hasKeywordStuffing
        ? "Repeated keywords reduce trust and risk Google penalties"
        : undefined,
      remediation:
        "Rewrite the title to read like a human description: each meaningful word should appear at most twice. Replace duplicates with synonyms or remove them entirely.",
    },
    {
      id: "title.allCaps",
      label: ti.isAllCaps ? "Title is ALL CAPS" : "Proper case used",
      passed: !ti.isAllCaps,
      weight: 3,
      detail: ti.isAllCaps
        ? "Mixed case is 40% more readable and trustworthy"
        : undefined,
      remediation:
        "Switch to title case in the product admin. If your theme is forcing uppercase via CSS (`text-transform: uppercase`), remove that rule from the product-title selector.",
    },
    {
      id: "title.promotionalText",
      label: ti.hasPromotionalText
        ? "Promotional text in title"
        : "No promotional text",
      passed: !ti.hasPromotionalText,
      weight: 3,
      detail: ti.hasPromotionalText
        ? "SEO titles should describe the product, not the deal"
        : undefined,
      remediation:
        "Strip 'SALE', 'NEW', or 'FREE SHIPPING' from the product title — those belong on a banner or badge, not in metadata Google indexes for search.",
    },
    {
      id: "title.h1MetaDiffer",
      label: ti.h1MetaDiffer
        ? "H1 and meta title are different"
        : "H1 and meta title are identical",
      passed: ti.h1MetaDiffer,
      weight: 3,
      detail:
        !ti.h1MetaDiffer && ti.hasH1 && ti.metaTitle
          ? "Optimize meta title for SERP display separately from the on-page H1"
          : undefined,
      remediation:
        "Set a custom Page Title in the product's Search engine listing section that's optimized for click-through (include benefit + brand), distinct from the on-page H1.",
    },
    {
      id: "title.specifics",
      label: ti.hasSpecifics
        ? "Product specifics detected (color, size, material)"
        : "Title lacks product specifics",
      passed: ti.hasSpecifics,
      weight: 3,
      detail: !ti.hasSpecifics
        ? "Adding color, size, or material improves search specificity"
        : undefined,
      remediation:
        "Bake one or two concrete specs into the title — e.g. 'Merino Wool Crew Sweater – Navy' beats 'Cozy Crew Sweater'. Pick the spec shoppers Google for.",
    },
  ];

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Description Quality — IssueCard.tsx 629–735
   ──────────────────────────────────────────────────────────────── */
export function buildDescriptionChecks(
  de: DescriptionSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const benefitPct = Math.round(de.benefitRatio * 100);
  const emotionalPct = (de.emotionalDensity * 100).toFixed(1);

  const checks: DimensionCheck[] = [
    {
      id: "description.descriptionFound",
      label: de.descriptionFound
        ? "Product description detected"
        : "No product description found",
      passed: de.descriptionFound,
      weight: 15,
      detail: !de.descriptionFound
        ? "87% of shoppers consider descriptions the most important purchase factor"
        : undefined,
      remediation:
        "Open the product in admin and paste at least one paragraph (~100 words) into the Description field. Lead with the problem this product solves, then list specs.",
    },
    {
      id: "description.wordCount",
      label: `${de.wordCount} words`,
      passed: de.wordCount >= 100 && de.wordCount <= 400,
      weight: 8,
      detail:
        de.wordCount < 50
          ? "Too thin — aim for 100–400 words"
          : de.wordCount < 100
            ? "A bit short — 100–400 words is optimal"
            : de.wordCount > 600
              ? "Over 600 words risks losing readers before the buy button"
              : de.wordCount > 400
                ? "Slightly long — 100–400 words is the sweet spot"
                : undefined,
      remediation:
        de.wordCount > 400
          ? "Trim to 100–400 words. Move spec tables, FAQs, and care instructions into expandable sections below the main copy."
          : "Expand to at least 100 words: 1 hook line, 3 benefit bullets, 1 paragraph of detail, 1 reassurance line. Don't pad — every line should answer a buyer question.",
    },
    {
      id: "description.readingLevel",
      label: `Reading level: grade ${de.fleschKincaidGrade.toFixed(1)}`,
      passed: de.fleschKincaidGrade >= 4 && de.fleschKincaidGrade <= 10,
      weight: 8,
      detail:
        de.fleschKincaidGrade > 10
          ? "Too complex — grade 6–8 maximises comprehension"
          : de.fleschKincaidGrade < 4 && de.descriptionFound
            ? "Very simple — grade 6–8 is the target"
            : undefined,
      remediation:
        de.fleschKincaidGrade > 10
          ? "Run the copy through Hemingway Editor and rewrite anything flagged red. Replace technical synonyms with everyday words ('utilize' → 'use', 'commence' → 'start')."
          : "Add a touch more substance — concrete sensory detail and richer noun phrases will lift the reading level into the 6–8 sweet spot without making it harder to read.",
    },
    {
      id: "description.avgSentence",
      label: `Avg sentence: ${de.avgSentenceLength.toFixed(0)} words`,
      passed: de.avgSentenceLength >= 10 && de.avgSentenceLength <= 20,
      weight: 8,
      detail:
        de.avgSentenceLength > 25
          ? "Sentences are too long — target 10–20 words per sentence"
          : de.avgSentenceLength < 8 && de.descriptionFound
            ? "Sentences are very short — 10–20 words is ideal"
            : undefined,
      remediation:
        de.avgSentenceLength > 20
          ? "Find any sentence over 25 words and break it at the conjunction (' and ', ' but ', ' which '). Two clear sentences always beat one long one."
          : "Combine choppy sentences with a comma or conjunction — but only when ideas naturally flow. Don't pad; just ensure rhythm varies.",
    },
    {
      id: "description.benefitRatio",
      label: `Benefit vs feature ratio: ${benefitPct}% benefit-focused`,
      passed: de.benefitRatio >= 0.3 && de.benefitRatio <= 0.7,
      weight: 8,
      detail:
        de.benefitRatio < 0.3 && de.benefitWordCount + de.featureWordCount > 3
          ? "Feature-heavy — lead with benefits over features for 12–24% higher conversion"
          : de.benefitRatio > 0.7 && de.benefitWordCount + de.featureWordCount > 3
            ? "Add more feature details — shoppers need specs to confirm their decision"
            : undefined,
      remediation:
        de.benefitRatio < 0.3
          ? "Rewrite each feature bullet as a benefit using the 'so you can…' test. ('Merino wool' → 'Merino wool stays warm even when wet — so you can hike all day.')"
          : "Add a concrete spec table or bullet list: dimensions, weight, materials, warranty terms. Buyers need spec confirmation before they hit Add to Cart.",
    },
    {
      id: "description.emotional",
      label: `Emotional language: ${emotionalPct}%`,
      passed: de.emotionalDensity >= 0.02 && de.emotionalDensity <= 0.1,
      weight: 8,
      detail:
        de.emotionalDensity < 0.01 && de.descriptionFound
          ? "Copy feels flat — 3–8% emotional words drives higher engagement"
          : undefined,
      remediation:
        "Sprinkle in 2–4 sensory or emotional words (cozy, butter-soft, effortless, dependable). Match the brand voice — luxury skews calm; outdoors skews bold; baby skews tender.",
    },
    {
      id: "description.htmlVariety",
      label: `${de.htmlTagVariety} formatting tag types`,
      passed: de.htmlTagVariety >= 4,
      weight: 8,
      detail:
        de.htmlTagVariety === 0 && de.descriptionFound
          ? "Plain text wall — add bold, bullets, and images"
          : de.htmlTagVariety < 4 && de.descriptionFound
            ? "Basic formatting — add more variety for better scannability"
            : undefined,
      remediation:
        "In the rich-text editor, add at least: 1 H2 heading, 1 bulleted list, 1 bold key phrase, and 1 image. That mix alone hits 4 tag types and makes the copy scannable.",
    },
    {
      id: "description.structure",
      label:
        de.hasHeadings && de.hasBulletLists
          ? "Structured layout (headings + bullets)"
          : de.hasHeadings
            ? "Has headings but no bullet lists"
            : de.hasBulletLists
              ? "Has bullets but no section headings"
              : "No structural elements",
      passed: de.hasHeadings && de.hasBulletLists,
      weight: 8,
      detail:
        !de.hasHeadings && de.descriptionFound
          ? "Add H2/H3 headings to break content into scannable sections"
          : !de.hasBulletLists && de.descriptionFound
            ? "Add bullet points — only 16% of users read word-for-word"
            : undefined,
      remediation:
        "Restructure the copy as: H2 'What it does' + benefit bullets, H2 'Specs' + spec bullets, H2 'In the box' + included items. Use the editor's Heading 2 / List buttons.",
    },
  ];

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Shipping Transparency — IssueCard.tsx 736–814
   ──────────────────────────────────────────────────────────────── */
export function buildShippingChecks(
  sh: ShippingSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const checks: DimensionCheck[] = [
    {
      id: "shipping.freeShipping",
      label: sh.hasFreeShipping
        ? "Free shipping detected"
        : "No free shipping messaging",
      passed: sh.hasFreeShipping,
      weight: 15,
      detail: !sh.hasFreeShipping
        ? "62% of shoppers won't purchase without free shipping"
        : undefined,
    },
    {
      id: "shipping.threshold",
      label: sh.hasFreeShippingThreshold
        ? `Free shipping threshold: $${sh.freeShippingThresholdValue ?? "?"}`
        : "No free shipping threshold",
      passed: sh.hasFreeShippingThreshold,
      weight: 3,
      detail:
        !sh.hasFreeShippingThreshold && sh.hasFreeShipping
          ? "Set threshold 10–15% above AOV — 58% of shoppers add items to qualify"
          : undefined,
    },
    {
      id: "shipping.deliveryDate",
      label: sh.hasDeliveryDate
        ? "Specific delivery date found"
        : "No specific delivery date",
      passed: sh.hasDeliveryDate,
      weight: 8,
      detail: !sh.hasDeliveryDate
        ? "'Arrives by Thursday, Feb 12' outperforms '3–5 business days' by 24%"
        : undefined,
    },
    {
      id: "shipping.deliveryEstimate",
      label: sh.hasDeliveryEstimate
        ? "Business-day estimate present"
        : "No delivery time estimate",
      passed: sh.hasDeliveryEstimate || sh.hasDeliveryDate,
      weight: 8,
      detail:
        !sh.hasDeliveryEstimate && !sh.hasDeliveryDate
          ? "75% of shoppers say delivery dates influence purchase decisions"
          : sh.hasDeliveryEstimate && !sh.hasDeliveryDate
            ? "Upgrade to a specific date for better conversion"
            : undefined,
    },
    {
      id: "shipping.eddApp",
      label: sh.hasEddApp ? "Delivery date app detected" : "No EDD app installed",
      passed: sh.hasEddApp,
      weight: 3,
      detail: !sh.hasEddApp
        ? "Apps like AfterShip EDD or Synctrack automate delivery estimates"
        : undefined,
    },
    {
      id: "shipping.costShown",
      label: sh.hasShippingCostShown
        ? "Shipping cost visible"
        : "No shipping cost shown",
      passed: sh.hasShippingCostShown,
      weight: 8,
      detail: !sh.hasShippingCostShown
        ? "Hidden extra costs cause 48% of all cart abandonment"
        : undefined,
    },
    {
      id: "shipping.structuredData",
      label: sh.hasShippingInStructuredData
        ? "shippingDetails in schema"
        : "No shippingDetails in schema",
      passed: sh.hasShippingInStructuredData,
      weight: 3,
      detail: !sh.hasShippingInStructuredData
        ? "Enables shipping info in Google Shopping and AI citations"
        : undefined,
    },
    {
      id: "shipping.policyLink",
      label: sh.hasShippingPolicyLink
        ? "Shipping policy link found"
        : "No shipping policy link",
      passed: sh.hasShippingPolicyLink,
      weight: 8,
      detail: !sh.hasShippingPolicyLink
        ? "A visible policy link reduces pre-purchase hesitation"
        : undefined,
    },
    {
      id: "shipping.returnsMentioned",
      label: sh.hasReturnsMentioned
        ? "Returns/refund info present"
        : "No returns info mentioned",
      passed: sh.hasReturnsMentioned,
      weight: 8,
      detail: !sh.hasReturnsMentioned
        ? "Combined shipping + returns transparency builds buyer confidence"
        : undefined,
    },
  ];

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Trust & Guarantees — IssueCard.tsx 815–891
   ──────────────────────────────────────────────────────────────── */
export function buildTrustChecks(
  tr: TrustSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const checks: DimensionCheck[] = [
    {
      id: "trust.moneyBackGuarantee",
      label: tr.hasMoneyBackGuarantee
        ? "Money-back guarantee detected"
        : "No money-back guarantee",
      passed: tr.hasMoneyBackGuarantee,
      weight: 8,
      detail: !tr.hasMoneyBackGuarantee
        ? "Money-back guarantees increase conversion up to 32%"
        : undefined,
    },
    {
      id: "trust.returnPolicy",
      label: tr.hasReturnPolicy
        ? "Return policy visible"
        : "No return policy visible",
      passed: tr.hasReturnPolicy,
      weight: 8,
      detail: !tr.hasReturnPolicy
        ? "Visible return policy lifts conversion 8–14% for products over $75"
        : undefined,
    },
    {
      id: "trust.securityBadge",
      label: tr.hasSecurityBadge ? "Security badge detected" : "No security badge",
      passed: tr.hasSecurityBadge,
      weight: 8,
      detail: !tr.hasSecurityBadge
        ? "Norton/McAfee badges increase conversion 12.2%"
        : undefined,
    },
    {
      id: "trust.safeCheckoutBadge",
      label: tr.hasSafeCheckoutBadge
        ? '"Guaranteed Safe Checkout" badge'
        : "No safe checkout badge",
      passed: tr.hasSafeCheckoutBadge,
      weight: 8,
      detail: !tr.hasSafeCheckoutBadge
        ? "Payment security icons lift conversion 11%"
        : undefined,
    },
    {
      id: "trust.badgeCount",
      label: `${tr.trustBadgeCount} trust badge${tr.trustBadgeCount !== 1 ? "s" : ""} found`,
      passed: tr.trustBadgeCount >= 2,
      weight: 8,
      detail:
        tr.trustBadgeCount === 0
          ? "Aim for 2–3 trust badges at 60–80px wide"
          : tr.trustBadgeCount > 3
            ? "More than 3 badges creates visual clutter"
            : undefined,
    },
    {
      id: "trust.secureCheckoutText",
      label: tr.hasSecureCheckoutText
        ? "Secure checkout messaging"
        : "No secure checkout text",
      passed: tr.hasSecureCheckoutText,
      weight: 3,
    },
    {
      id: "trust.paymentIcons",
      label: tr.hasPaymentIcons
        ? "Payment trust icons visible"
        : "No payment trust icons",
      passed: tr.hasPaymentIcons,
      weight: 8,
      detail: !tr.hasPaymentIcons
        ? "Familiar payment logos reduce checkout anxiety"
        : undefined,
    },
    {
      id: "trust.liveChat",
      label: tr.hasLiveChat ? "Live chat available" : "No live chat detected",
      passed: tr.hasLiveChat,
      weight: 3,
      detail: !tr.hasLiveChat
        ? "Live chat increases conversion 20% on average"
        : undefined,
    },
    {
      id: "trust.phoneNumber",
      label: tr.hasPhoneNumber ? "Phone number visible" : "No phone number",
      passed: tr.hasPhoneNumber,
      weight: 8,
      detail: !tr.hasPhoneNumber
        ? "Phone visibility is the #1 global trust symbol"
        : undefined,
    },
    {
      id: "trust.freeShippingBadge",
      label: tr.hasFreeShippingBadge
        ? "Free shipping messaging"
        : "No free shipping badge",
      passed: tr.hasFreeShippingBadge,
      weight: 3,
    },
    {
      id: "trust.nearAtc",
      label: tr.hasTrustNearAtc
        ? "Trust signals near Add to Cart"
        : "No trust signals near ATC",
      passed: tr.hasTrustNearAtc,
      weight: 8,
      detail: !tr.hasTrustNearAtc
        ? "Trust badges near ATC deliver 8–19% conversion lift"
        : undefined,
    },
  ];

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Page Speed — IssueCard.tsx 929–1004
   Special: emits one headline check carrying the full
   PageSpeedSignals payload (so the disclosure drawer can render
   <PageSpeedScorecard>) plus 1:1 ports of every HTML-derived
   <SignalRow> below.
   ──────────────────────────────────────────────────────────────── */
export function buildPageSpeedChecks(
  ps: PageSpeedSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const score = ps.performanceScore ?? 0;
  const headline: DimensionCheck = {
    id: "pageSpeed.overall",
    label:
      score >= 90
        ? `Page speed: ${score}/100`
        : `Page speed needs work: ${score}/100`,
    passed: score >= 90,
    weight: 15,
    detail:
      score >= 90
        ? "Lab Lighthouse score is in the green band"
        : "Slower pages lose ~7% conversion per second of load delay",
    pageSpeedSignals: ps,
  };

  const checks: DimensionCheck[] = [headline];

  checks.push(
    {
      id: "pageSpeed.thirdPartyScripts",
      label: `${ps.thirdPartyScriptCount} third-party script${ps.thirdPartyScriptCount !== 1 ? "s" : ""}`,
      passed: ps.thirdPartyScriptCount <= 5,
      weight: 8,
      detail:
        ps.thirdPartyScriptCount > 10
          ? "Over 10 third-party scripts significantly slows page load"
          : ps.thirdPartyScriptCount > 5
            ? "Consider auditing which scripts are essential"
            : undefined,
    },
    {
      id: "pageSpeed.renderBlocking",
      label: `${ps.renderBlockingScriptCount} render-blocking script${ps.renderBlockingScriptCount !== 1 ? "s" : ""}`,
      passed: ps.renderBlockingScriptCount === 0,
      weight: 8,
      detail:
        ps.renderBlockingScriptCount > 0
          ? "Defer or async non-critical scripts to unblock rendering"
          : undefined,
    },
    {
      id: "pageSpeed.lazyLoading",
      label: ps.hasLazyLoading
        ? "Lazy loading enabled"
        : "No lazy loading detected",
      passed: ps.hasLazyLoading,
      weight: 8,
      detail: !ps.hasLazyLoading
        ? "Lazy loading below-fold images saves bandwidth and speeds up FCP"
        : undefined,
    },
    {
      id: "pageSpeed.lcpImageLazyLoaded",
      label: ps.lcpImageLazyLoaded
        ? "⚠ LCP image is lazy-loaded"
        : "LCP image not lazy-loaded",
      passed: !ps.lcpImageLazyLoaded,
      weight: 8,
      detail: ps.lcpImageLazyLoaded
        ? "Never lazy-load the hero/LCP image — it delays the largest paint"
        : undefined,
    },
    {
      id: "pageSpeed.modernImageFormats",
      label: ps.hasModernImageFormats
        ? "WebP/AVIF images detected"
        : "No modern image formats",
      passed: ps.hasModernImageFormats,
      weight: 8,
      detail: !ps.hasModernImageFormats
        ? "WebP/AVIF saves 25–50% file size vs JPEG/PNG"
        : undefined,
    },
    {
      id: "pageSpeed.fontDisplaySwap",
      label: ps.hasFontDisplaySwap
        ? "font-display: swap used"
        : "No font-display: swap",
      passed: ps.hasFontDisplaySwap,
      weight: 3,
      detail: !ps.hasFontDisplaySwap
        ? "font-display: swap prevents invisible text during web font loading"
        : undefined,
    },
    {
      id: "pageSpeed.preconnect",
      label: ps.hasPreconnectHints
        ? "Preconnect hints found"
        : "No preconnect hints",
      passed: ps.hasPreconnectHints,
      weight: 3,
      detail: !ps.hasPreconnectHints
        ? "Preconnect to key origins saves 100–500ms per resource"
        : undefined,
    },
    {
      id: "pageSpeed.heroPreload",
      label: ps.hasHeroPreload ? "Hero image preloaded" : "No hero preload",
      passed: ps.hasHeroPreload,
      weight: 8,
      detail: !ps.hasHeroPreload
        ? "Preloading the hero image improves LCP significantly"
        : undefined,
    },
  );

  if (ps.detectedTheme) {
    checks.push({
      id: "pageSpeed.detectedTheme",
      label: `Theme: ${ps.detectedTheme}`,
      passed: true,
      weight: 3,
    });
  }

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Mobile CTA — IssueCard.tsx 1005–1079
   ──────────────────────────────────────────────────────────────── */
export function buildMobileCtaChecks(
  mc: MobileCtaSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const checks: DimensionCheck[] = [
    {
      id: "mobileCta.atcReachable",
      label: mc.ctaFound
        ? `CTA found: "${mc.ctaText ?? "Add to Cart"}"`
        : "No Add to Cart button detected",
      passed: mc.ctaFound,
      weight: 15,
      detail: !mc.ctaFound
        ? "A visible Add to Cart button is essential for conversion"
        : undefined,
      remediation:
        "Inspect the product template — the Add to Cart button may be hidden behind a JS-only flow or sold-out flag. Restore a visible `<button name='add'>` rendered in the initial HTML.",
    },
    {
      id: "mobileCta.viewportMeta",
      label: mc.hasViewportMeta
        ? "Viewport meta tag present"
        : "Missing viewport meta tag",
      passed: mc.hasViewportMeta,
      weight: 15,
      detail: !mc.hasViewportMeta
        ? "Viewport meta is required for proper mobile rendering"
        : undefined,
      remediation:
        "Add `<meta name='viewport' content='width=device-width, initial-scale=1'>` to the `<head>` in `theme.liquid`. Without it, mobile browsers render at desktop width and zoom out.",
    },
    {
      id: "mobileCta.responsiveMeta",
      label: mc.hasResponsiveMeta
        ? "Responsive viewport configured"
        : "Non-responsive viewport",
      passed: mc.hasResponsiveMeta,
      weight: 8,
      detail: !mc.hasResponsiveMeta
        ? "Use width=device-width for responsive layout"
        : undefined,
      remediation:
        "Update the viewport tag to include `width=device-width, initial-scale=1`. Avoid `user-scalable=no` — it's an accessibility violation on iOS.",
    },
    {
      id: "mobileCta.tapTarget",
      label:
        mc.meetsMin44px === null
          ? "Button tap target: not measured"
          : mc.meetsOptimal60_72px
            ? `Button: ${mc.buttonHeightPx}px tall — optimal`
            : mc.meetsMin44px
              ? `Button: ${mc.buttonHeightPx}px tall — meets minimum`
              : `Button: ${mc.buttonHeightPx}px tall — too small`,
      passed: mc.meetsMin44px === true,
      weight: 8,
      detail:
        mc.meetsMin44px === false
          ? "Minimum 44px tap target (Apple HIG) — 60–72px is optimal for thumb reach"
          : mc.meetsMin44px === true && !mc.meetsOptimal60_72px
            ? "Meets minimum but 60–72px height converts better on mobile"
            : undefined,
      remediation:
        "In your theme's CSS, set the buy button's `min-height` to 56–64px on mobile (`@media (max-width: 749px)`). Add `padding: 18px 24px` for comfortable tap area.",
    },
    {
      id: "mobileCta.aboveFold",
      label:
        mc.aboveFold === null
          ? "Fold position: not measured"
          : mc.aboveFold
            ? "CTA above the fold"
            : "CTA below the fold",
      passed: mc.aboveFold === true,
      weight: 8,
      detail:
        mc.aboveFold === false
          ? "70% of mobile users never scroll — keep CTA visible immediately"
          : undefined,
      remediation:
        "Tighten the mobile product layout: reduce hero image height, hide secondary specs behind an accordion, and ensure the Add to Cart button lives within the first 750px of viewport.",
    },
    {
      id: "mobileCta.sticky",
      label: mc.isSticky ? "Sticky CTA enabled" : "No sticky CTA",
      passed: mc.isSticky === true,
      weight: 8,
      detail: !mc.isSticky
        ? "Sticky buy buttons keep the CTA visible during scroll"
        : mc.hasStickyApp
          ? `via ${mc.hasStickyApp}`
          : undefined,
      remediation:
        "Install a sticky buy button (Hextom Sticky Add to Cart, Sticky Buy Button by ShopPad) or add `position: sticky; bottom: 0` to a duplicate ATC bar at mobile breakpoints.",
    },
    {
      id: "mobileCta.fullWidth",
      label: mc.isFullWidth ? "Full-width button" : "Button is not full-width",
      passed: mc.isFullWidth === true,
      weight: 3,
      detail:
        mc.isFullWidth === false
          ? "Full-width buttons are easier to tap on mobile"
          : undefined,
      remediation:
        "Set `width: 100%` on the buy button at mobile breakpoints in your theme's CSS — full-width is the modern Shopify default and reduces miss-taps.",
    },
    {
      id: "mobileCta.thumbZone",
      label:
        mc.inThumbZone === null
          ? "Thumb zone: not measured"
          : mc.inThumbZone
            ? "CTA in thumb zone"
            : "CTA outside thumb zone",
      passed: mc.inThumbZone === true,
      weight: 3,
      detail:
        mc.inThumbZone === false
          ? "Place primary CTA in the bottom-center thumb zone for one-handed use"
          : undefined,
      remediation:
        "Use a sticky bottom-bar that pins the buy button within the bottom 200px of viewport — the natural reach zone for one-handed use on phones over 6'.",
    },
  ];

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Cross-Sell — IssueCard.tsx 1080–1148
   ──────────────────────────────────────────────────────────────── */
export function buildCrossSellChecks(
  cs: CrossSellSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const checks: DimensionCheck[] = [
    {
      id: "crossSell.section",
      label: cs.hasCrossSellSection
        ? "Cross-sell section detected"
        : "No cross-sell section found",
      passed: cs.hasCrossSellSection,
      weight: 8,
      detail: !cs.hasCrossSellSection
        ? "Cross-sell recommendations increase AOV by 10–30%"
        : undefined,
      remediation:
        "Add a 'You might also like' or 'Frequently bought together' block below the main product details. Shopify's built-in `recommended_products` API or apps like ReConvert or Frequently Bought Together both work.",
    },
  ];

  if (cs.crossSellApp) {
    checks.push({
      id: "crossSell.app",
      label: `App: ${cs.crossSellApp}`,
      passed: true,
      weight: 3,
    });
  }
  if (cs.widgetType) {
    checks.push({
      id: "crossSell.widgetType",
      label: `Widget type: ${cs.widgetType}`,
      passed: true,
      weight: 3,
    });
  }

  checks.push(
    {
      id: "crossSell.productCount",
      label: `${cs.productCount} recommended product${cs.productCount !== 1 ? "s" : ""}`,
      passed: cs.recommendationCountOptimal,
      weight: 8,
      detail:
        cs.productCount === 0
          ? "Show 3–6 complementary products"
          : !cs.recommendationCountOptimal
            ? "Optimal is 3–6 recommendations — too many causes decision fatigue"
            : undefined,
      remediation:
        cs.productCount === 0
          ? "Hand-curate or auto-populate 3–6 complementary items via Shopify's product recommendations API. Pin the highest-margin SKUs as fallback."
          : "Trim the recommendation rail to 3–6 products. Use Search & Discovery's manual rules to demote slow-movers and promote attach products.",
    },
    {
      id: "crossSell.bundlePricing",
      label: cs.hasBundlePricing ? "Bundle pricing available" : "No bundle pricing",
      passed: cs.hasBundlePricing,
      weight: 3,
      detail:
        !cs.hasBundlePricing && cs.hasCrossSellSection
          ? "Bundle discounts increase cross-sell acceptance 25%"
          : undefined,
      remediation:
        "Build a bundle through Shopify's native Bundles app (free) or Frequently Bought Together. Show the combined price with the bundle savings called out.",
    },
    {
      id: "crossSell.bundleDiscount",
      label: cs.hasDiscountOnBundle
        ? "Bundle discount shown"
        : "No bundle discount",
      passed: cs.hasDiscountOnBundle,
      weight: 3,
      detail:
        !cs.hasDiscountOnBundle && cs.hasCrossSellSection
          ? "'Save 15% when bought together' is a proven conversion driver"
          : undefined,
      remediation:
        "Apply a 10–15% automatic discount when both items are in cart (Shopify Functions or apps like Bundler). Surface the savings as a callout: 'Save $12 when bundled.'",
    },
    {
      id: "crossSell.addAllToCart",
      label: cs.hasAddAllToCart
        ? "Add All to Cart button"
        : "No quick-add for bundle",
      passed: cs.hasAddAllToCart,
      weight: 3,
      detail:
        !cs.hasAddAllToCart && cs.hasCrossSellSection
          ? "One-click bundle add reduces friction"
          : undefined,
      remediation:
        "Pick a cross-sell app that supports a single 'Add Bundle to Cart' button (FBT by Code Black Belt, ReConvert). Avoid making shoppers click each item individually.",
    },
    {
      id: "crossSell.checkboxSelection",
      label: cs.hasCheckboxSelection
        ? "Checkbox selection available"
        : "No item selection checkboxes",
      passed: cs.hasCheckboxSelection,
      weight: 3,
      detail:
        !cs.hasCheckboxSelection && cs.hasCrossSellSection
          ? "Let shoppers pick which items to add"
          : undefined,
      remediation:
        "Use a 'Frequently Bought Together' widget that lets shoppers tick which add-ons they want. The total price updates live as boxes are checked.",
    },
    {
      id: "crossSell.nearBuyButton",
      label: cs.nearBuyButton
        ? "Cross-sell near Buy button"
        : "Cross-sell not near Buy button",
      passed: cs.nearBuyButton,
      weight: 3,
      detail:
        !cs.nearBuyButton && cs.hasCrossSellSection
          ? "Proximity to the Buy button drives higher engagement"
          : undefined,
      remediation:
        "Move the cross-sell rail directly above or below the Add to Cart button (not at the bottom of the page). Most theme editors let you drag sections to reorder.",
    },
  );

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Variant UX — IssueCard.tsx 1149–1215
   ──────────────────────────────────────────────────────────────── */
export function buildVariantUxChecks(
  vu: VariantUxSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const checks: DimensionCheck[] = [
    {
      id: "variantUx.hasVariants",
      label: vu.hasVariants
        ? "Product variants detected"
        : "No product variants found",
      passed: vu.hasVariants,
      weight: 8,
      remediation:
        "If this product comes in multiple sizes or colors, configure them as variants in the admin (Shopify → Product → Variants). For single-SKU products, ignore this check.",
    },
    {
      id: "variantUx.visualSwatches",
      label: vu.hasVisualSwatches ? "Visual color swatches" : "No visual swatches",
      passed: vu.hasVisualSwatches,
      weight: 8,
      detail:
        !vu.hasVisualSwatches && vu.hasVariants
          ? vu.colorUsesDropdown
            ? "Replace the color dropdown with visual swatches — 60% of shoppers prefer them"
            : "Visual swatches increase engagement 26% vs text-only selectors"
          : undefined,
      remediation:
        "Switch on color swatches in the theme editor (Dawn 13+, Sense, Impulse, Prestige all support them) or install Swatch King / Variant Image Wizard. Upload a small color square per variant.",
    },
    {
      id: "variantUx.variantImageLink",
      label: vu.hasVariantImageLink
        ? "Variants update product image"
        : "Variant selection doesn't update image",
      passed: vu.hasVariantImageLink,
      weight: 3,
      detail:
        !vu.hasVariantImageLink && vu.hasVariants
          ? "Linking variants to images reduces return rate 5–10%"
          : undefined,
      remediation:
        "On each variant in the admin, set 'Image' to the matching photo. Most themes auto-swap the gallery; if yours doesn't, install Variant Image Wizard.",
    },
    {
      id: "variantUx.stockIndicator",
      label: vu.hasStockIndicator ? "Stock indicator present" : "No stock indicator",
      passed: vu.hasStockIndicator,
      weight: 8,
      detail:
        !vu.hasStockIndicator && vu.hasVariants
          ? "Per-variant stock status reduces disappointment at checkout"
          : undefined,
      remediation:
        "Show 'In stock' / 'Low stock' / 'Sold out' next to the variant selector. Most themes have an `inventory_management` block — enable it in section settings.",
    },
    {
      id: "variantUx.lowStockUrgency",
      label: vu.hasLowStockUrgency
        ? "Low-stock urgency messaging"
        : "No low-stock urgency",
      passed: vu.hasLowStockUrgency,
      weight: 3,
      detail:
        !vu.hasLowStockUrgency && vu.hasVariants
          ? "'Only 3 left' messaging drives urgency and faster decisions"
          : undefined,
      remediation:
        "Surface real inventory below a threshold (show 'Only N left' when stock < 5). Most stock-indicator themes already support this — switch on the threshold in section settings.",
    },
    {
      id: "variantUx.soldOutHandling",
      label: vu.hasSoldOutHandling
        ? "Sold-out variants handled"
        : "No sold-out handling",
      passed: vu.hasSoldOutHandling,
      weight: 8,
      detail:
        !vu.hasSoldOutHandling && vu.hasVariants
          ? "Gray out or label sold-out variants instead of hiding them"
          : undefined,
      remediation:
        "In section settings, enable 'Show sold-out variants as disabled' (rather than hiding them). Add CSS `.swatch.unavailable { opacity: 0.4; text-decoration: line-through }`.",
    },
    {
      id: "variantUx.notifyMe",
      label: vu.hasNotifyMe
        ? "Back-in-stock notification"
        : "No notify-me option",
      passed: vu.hasNotifyMe,
      weight: 3,
      detail:
        !vu.hasNotifyMe && vu.hasVariants
          ? "Back-in-stock alerts recover 5–15% of otherwise lost sales"
          : undefined,
      remediation:
        "Install a back-in-stock app (Klaviyo Back in Stock, Restock Rocket, or Notify Me) — they replace the disabled 'Sold Out' button with a 'Notify Me' email-capture form.",
    },
  ];

  if (vu.swatchApp) {
    checks.push({
      id: "variantUx.swatchApp",
      label: `Swatch app: ${vu.swatchApp}`,
      passed: true,
      weight: 3,
    });
  }

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Size Guide — IssueCard.tsx 1216–1283
   ──────────────────────────────────────────────────────────────── */
export function buildSizeGuideChecks(
  sg: SizeGuideSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const checks: DimensionCheck[] = [
    {
      id: "sizeGuide.linkPresent",
      label: sg.hasSizeGuideLink ? "Size guide link present" : "No size guide link",
      passed: sg.hasSizeGuideLink,
      weight: 8,
      detail:
        !sg.hasSizeGuideLink && sg.categoryApplicable
          ? "Size guides reduce returns by 32% in apparel/footwear"
          : undefined,
      remediation:
        "Add a 'Size guide' link directly under the size selector. In Shopify, create a snippet `size-guide.liquid` with the chart and include it via a modal trigger.",
    },
    {
      id: "sizeGuide.popup",
      label: sg.hasSizeGuidePopup
        ? "Size guide opens in popup/modal"
        : "No size guide popup",
      passed: sg.hasSizeGuidePopup,
      weight: 3,
      detail:
        !sg.hasSizeGuidePopup && sg.hasSizeGuideLink
          ? "Popup keeps shoppers on the product page while checking sizing"
          : undefined,
      remediation:
        "Wrap the size guide in a modal overlay (most themes ship a `<details>` or modal helper) — never link to a separate page; you'll lose the buying context.",
    },
    {
      id: "sizeGuide.chartTable",
      label: sg.hasSizeChartTable
        ? "Size chart table found"
        : "No size chart table",
      passed: sg.hasSizeChartTable,
      weight: 8,
      detail:
        !sg.hasSizeChartTable && sg.categoryApplicable
          ? "Comparison tables make size selection faster and more confident"
          : undefined,
      remediation:
        "Inside the size guide, render an actual `<table>` with rows for each size and columns for chest/waist/length. Include both inches and cm — international shoppers thank you.",
    },
    {
      id: "sizeGuide.fitFinder",
      label: sg.hasFitFinder ? "Fit finder / quiz detected" : "No fit finder tool",
      passed: sg.hasFitFinder,
      weight: 3,
      detail:
        !sg.hasFitFinder && sg.categoryApplicable
          ? "Interactive fit finders increase conversion 20% and reduce returns"
          : undefined,
      remediation:
        "Install a fit-finder app like Kiwi Sizing or True Fit — they ask 3–5 quick questions (height/weight/preferred fit) and recommend a size. Worth the cost on apparel SKUs.",
    },
    {
      id: "sizeGuide.modelMeasurements",
      label: sg.hasModelMeasurements
        ? "Model measurements shown"
        : "No model measurements",
      passed: sg.hasModelMeasurements,
      weight: 3,
      detail:
        !sg.hasModelMeasurements && sg.categoryApplicable
          ? "'Model is 5'10\" wearing size M' gives a concrete reference point"
          : undefined,
      remediation:
        "Add a one-line note under the gallery or in the description: 'Model is 5'10\" / 178cm wearing size M.' Shoppers anchor their own size against the model.",
    },
    {
      id: "sizeGuide.fitRecommendation",
      label: sg.hasFitRecommendation
        ? "Fit recommendation present"
        : "No fit recommendation",
      passed: sg.hasFitRecommendation,
      weight: 3,
      detail:
        !sg.hasFitRecommendation && sg.categoryApplicable
          ? "'Runs true to size' or 'Order one size up' reduces hesitation"
          : undefined,
      remediation:
        "Bake one short fit line into the description: 'True to size,' 'Runs small — order one size up,' or 'Relaxed fit.' Lean on actual return data to phrase it accurately.",
    },
    {
      id: "sizeGuide.measurementInstructions",
      label: sg.hasMeasurementInstructions
        ? "How-to-measure instructions"
        : "No measurement instructions",
      passed: sg.hasMeasurementInstructions,
      weight: 3,
      detail:
        !sg.hasMeasurementInstructions && sg.categoryApplicable
          ? "Self-measurement guides reduce sizing errors"
          : undefined,
      remediation:
        "In the size-guide modal, add a 'How to measure' section with a labelled diagram and bullet instructions for chest, waist, hips, inseam. Reusable across the catalog.",
    },
    {
      id: "sizeGuide.nearSizeSelector",
      label: sg.nearSizeSelector
        ? "Size guide near size selector"
        : "Size guide not near selector",
      passed: sg.nearSizeSelector,
      weight: 3,
      detail:
        !sg.nearSizeSelector && sg.hasSizeGuideLink
          ? "Place the size guide link directly next to the size dropdown"
          : undefined,
      remediation:
        "In the variant-picker template, render the size-guide trigger inline with the size label (`Size [Size guide ›]`). It's the moment shoppers actually need it.",
    },
  ];

  if (sg.sizeGuideApp) {
    checks.push({
      id: "sizeGuide.app",
      label: `App: ${sg.sizeGuideApp}`,
      passed: true,
      weight: 3,
    });
  }

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   AI Discoverability — IssueCard.tsx 1284–1362
   ──────────────────────────────────────────────────────────────── */
export function buildAiDiscoverabilityChecks(
  ad: AiDiscoverabilitySignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const ogPresent = [ad.hasOgType, ad.hasOgTitle, ad.hasOgDescription, ad.hasOgImage]
    .filter(Boolean).length;

  const checks: DimensionCheck[] = [
    {
      id: "aiDiscoverability.robotsTxt",
      label:
        ad.robotsTxtExists === null
          ? "robots.txt: could not check"
          : ad.robotsTxtExists
            ? "robots.txt exists"
            : "No robots.txt found",
      passed: ad.robotsTxtExists === true,
      weight: 8,
      detail:
        ad.robotsTxtExists === false
          ? "robots.txt tells AI crawlers what they can and can't index"
          : undefined,
    },
    {
      id: "aiDiscoverability.wildcardBlock",
      label: ad.hasWildcardBlock
        ? "⚠ Wildcard User-agent block detected"
        : "No wildcard bot block",
      passed: !ad.hasWildcardBlock,
      weight: 8,
      detail: ad.hasWildcardBlock
        ? "Disallow * blocks all bots including AI search — use targeted rules instead"
        : undefined,
    },
    {
      id: "aiDiscoverability.aiBotsAllowed",
      label: `${ad.aiSearchBotsAllowedCount} AI search bot${ad.aiSearchBotsAllowedCount !== 1 ? "s" : ""} allowed`,
      passed: ad.aiSearchBotsAllowedCount >= 2,
      weight: 8,
      detail:
        ad.aiSearchBotsAllowedCount === 0
          ? "Allow OAI-SearchBot, PerplexityBot, and ClaudeBot for AI search visibility"
          : undefined,
    },
    {
      id: "aiDiscoverability.oaiSearchBot",
      label: ad.hasOaiSearchbotAllowed
        ? "OAI-SearchBot allowed"
        : "OAI-SearchBot not allowed",
      passed: ad.hasOaiSearchbotAllowed,
      weight: 3,
    },
    {
      id: "aiDiscoverability.perplexityBot",
      label: ad.hasPerplexitybotAllowed
        ? "PerplexityBot allowed"
        : "PerplexityBot not allowed",
      passed: ad.hasPerplexitybotAllowed,
      weight: 3,
    },
    {
      id: "aiDiscoverability.claudeBot",
      label: ad.hasClaudeSearchbotAllowed
        ? "ClaudeBot allowed"
        : "ClaudeBot not allowed",
      passed: ad.hasClaudeSearchbotAllowed,
      weight: 3,
    },
    {
      id: "aiDiscoverability.llmsTxt",
      label:
        ad.llmsTxtExists === null
          ? "llms.txt: could not check"
          : ad.llmsTxtExists
            ? "llms.txt exists"
            : "No llms.txt found",
      passed: ad.llmsTxtExists === true,
      weight: 3,
      detail:
        ad.llmsTxtExists === false
          ? "llms.txt provides structured context for AI assistants"
          : undefined,
    },
    {
      id: "aiDiscoverability.openGraphTags",
      label: `OpenGraph tags: ${ogPresent} of 4`,
      passed: ogPresent === 4,
      weight: 8,
      detail:
        ogPresent < 4
          ? `Missing: ${[
              !ad.hasOgType && "og:type",
              !ad.hasOgTitle && "og:title",
              !ad.hasOgDescription && "og:description",
              !ad.hasOgImage && "og:image",
            ]
              .filter(Boolean)
              .join(", ")}`
          : undefined,
    },
    {
      id: "aiDiscoverability.structuredSpecs",
      label: ad.hasStructuredSpecs
        ? "Structured specifications found"
        : "No structured specs",
      passed: ad.hasStructuredSpecs,
      weight: 8,
      detail: !ad.hasStructuredSpecs
        ? "Structured specs help AI extract concrete product attributes"
        : undefined,
    },
    {
      id: "aiDiscoverability.faqContent",
      label: ad.hasFaqContent ? "FAQ content detected" : "No FAQ section",
      passed: ad.hasFaqContent,
      weight: 8,
      detail: !ad.hasFaqContent
        ? "FAQ sections are prime targets for AI answer extraction"
        : undefined,
    },
    {
      id: "aiDiscoverability.entityDensity",
      label: `Entity density: ${(ad.entityDensityScore * 100).toFixed(0)}%`,
      passed: ad.entityDensityScore >= 0.03,
      weight: 8,
      detail:
        ad.entityDensityScore < 0.03
          ? "Low entity density — add more concrete specs, measurements, and data points"
          : undefined,
    },
  ];

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Content Freshness — IssueCard.tsx 1363–1441
   ──────────────────────────────────────────────────────────────── */
export function buildContentFreshnessChecks(
  cf: ContentFreshnessSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const ageLabel = (days: number | null) => {
    if (days == null) return null;
    if (days < 30) return `${days}d ago`;
    if (days < 365) return `${Math.round(days / 30)}mo ago`;
    return `${(days / 365).toFixed(1)}yr ago`;
  };

  const checks: DimensionCheck[] = [
    {
      id: "contentFreshness.copyrightYear",
      label: cf.copyrightYear
        ? `Copyright year: ${cf.copyrightYear}`
        : "No copyright year found",
      passed: cf.copyrightYearIsCurrent,
      weight: 3,
      detail:
        cf.copyrightYear && !cf.copyrightYearIsCurrent
          ? "Outdated copyright year makes the site look abandoned"
          : undefined,
      remediation:
        "Replace the hardcoded year in the footer with `{{ 'now' | date: '%Y' }}` (Liquid) or `new Date().getFullYear()` (JS) so it auto-updates every January 1st.",
    },
    {
      id: "contentFreshness.expiredPromotion",
      label: cf.hasExpiredPromotion
        ? `Expired promotion detected`
        : "No expired promotions",
      passed: !cf.hasExpiredPromotion,
      weight: 3,
      detail: cf.hasExpiredPromotion
        ? cf.expiredPromotionText
          ? `"${cf.expiredPromotionText.slice(0, 60)}${cf.expiredPromotionText.length > 60 ? "…" : ""}"`
          : "Expired deals erode trust — remove or update them"
        : undefined,
      remediation:
        "Search the page for the dated promo copy and either remove it or schedule a recurring announcement-bar campaign so the call-out stays in sync with active sales.",
    },
    {
      id: "contentFreshness.seasonalMismatch",
      label: cf.hasSeasonalMismatch
        ? "Seasonal content mismatch"
        : "No seasonal mismatch",
      passed: !cf.hasSeasonalMismatch,
      weight: 3,
      detail: cf.hasSeasonalMismatch
        ? "Off-season promotions make the page look neglected"
        : undefined,
      remediation:
        "Set up Shopify's scheduled publishing on seasonal banners and product copy. Add a recurring calendar reminder to swap holiday/season callouts within 7 days of the date.",
    },
    {
      id: "contentFreshness.newLabel",
      label: cf.hasNewLabel
        ? cf.newLabelIsStale
          ? "'New' label but product is stale"
          : "'New' label present"
        : "No 'New' label",
      passed: cf.hasNewLabel && !cf.newLabelIsStale,
      weight: 3,
      detail: cf.newLabelIsStale
        ? "Remove 'New' badges from products older than 90 days"
        : undefined,
      remediation: cf.newLabelIsStale
        ? "Use a dynamic 'New' badge that auto-expires (most badge apps tag based on product `published_at`). Set the threshold to 90 days from publish date."
        : "Add a 'New' badge tied to product publish date. Frame it tightly — 30–60 days max — so the label always feels meaningful.",
    },
    {
      id: "contentFreshness.latestReview",
      label: cf.mostRecentReviewDateIso
        ? `Latest review: ${ageLabel(cf.reviewAgeDays) ?? cf.mostRecentReviewDateIso.slice(0, 10)}`
        : "No review dates found",
      passed: cf.reviewStaleness === "fresh" || cf.reviewStaleness === "moderate",
      weight: 3,
      detail:
        cf.reviewStaleness === "stale"
          ? "Reviews older than 12 months erode buyer confidence"
          : cf.reviewStaleness === "moderate"
            ? "Recent reviews would strengthen trust — consider a review request campaign"
            : undefined,
      remediation:
        "Re-engage past customers with a one-time review-request email targeting orders from the last 6 months. Offer a small loyalty incentive (50 points, 5% off) for completing a review.",
    },
    {
      id: "contentFreshness.freshestSignal",
      label:
        cf.freshestSignalAgeDays != null
          ? `Freshest signal: ${ageLabel(cf.freshestSignalAgeDays)}`
          : "No freshness signals detected",
      passed: cf.freshestSignalAgeDays != null && cf.freshestSignalAgeDays < 90,
      weight: 3,
      detail:
        cf.freshestSignalAgeDays != null && cf.freshestSignalAgeDays > 365
          ? "All content signals are over a year old — page appears dormant to both users and AI"
          : undefined,
      remediation:
        "Touch the product page at least once per quarter — refresh a hero image, update copy, or post a new review. Schedule a recurring task in your project tool to keep the page from going dormant.",
    },
  ];

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Accessibility — IssueCard.tsx 892–910
   Special: emit synthesized critical/serious/moderate/minor
   bucket checks (driven by the *Count fields on AccessibilitySignals)
   plus a `rules` catch-all — `CheckRow` renders rules in the
   disclosure drawer via the `RuleList` component.
   When `scanCompleted === false` the dimension was never scanned,
   so we emit an empty array.
   ──────────────────────────────────────────────────────────────── */
export function buildAccessibilityChecks(
  ac: AccessibilitySignals,
  leak?: LeakCard,
): DimensionCheck[] {
  if (ac.scanCompleted === false) return [];

  // Mirror IssueCard.tsx's AccessibilityChecklist 1:1 — six specific
  // violation rows, not bucketed severity counts. Weights are derived
  // from the storewide axe `impactToWeight` ladder (contrast/alt-text
  // are critical; empty link/button + form labels are serious; doc
  // language is moderate).
  const checks: DimensionCheck[] = [
    {
      id: "accessibility.contrast",
      label:
        ac.contrastViolations === 0
          ? "Color contrast passes"
          : `${ac.contrastViolations} contrast violation(s)`,
      passed: ac.contrastViolations === 0,
      weight: 15,
    },
    {
      id: "accessibility.altText",
      label:
        ac.altTextViolations === 0
          ? "All images have alt text"
          : `${ac.altTextViolations} missing alt text`,
      passed: ac.altTextViolations === 0,
      weight: 15,
    },
    {
      id: "accessibility.formLabels",
      label:
        ac.formLabelViolations === 0
          ? "All form inputs labeled"
          : `${ac.formLabelViolations} unlabeled input(s)`,
      passed: ac.formLabelViolations === 0,
      weight: 8,
    },
    {
      id: "accessibility.emptyLinks",
      label:
        ac.emptyLinkViolations === 0
          ? "All links have names"
          : `${ac.emptyLinkViolations} empty link(s)`,
      passed: ac.emptyLinkViolations === 0,
      weight: 8,
    },
    {
      id: "accessibility.emptyButtons",
      label:
        ac.emptyButtonViolations === 0
          ? "All buttons have names"
          : `${ac.emptyButtonViolations} empty button(s)`,
      passed: ac.emptyButtonViolations === 0,
      weight: 8,
    },
    {
      id: "accessibility.documentLanguage",
      label:
        ac.documentLanguageViolations === 0
          ? "Document language set"
          : "Missing document language",
      passed: ac.documentLanguageViolations === 0,
      weight: 4,
    },
  ];

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Social Commerce — IssueCard.tsx 911–928
   ──────────────────────────────────────────────────────────────── */
export function buildSocialCommerceChecks(
  sc: SocialCommerceSignals,
  leak?: LeakCard,
): DimensionCheck[] {
  const checks: DimensionCheck[] = [
    {
      id: "socialCommerce.instagram",
      label: "Instagram embed detected",
      passed: sc.hasInstagramEmbed,
      weight: 3,
    },
    {
      id: "socialCommerce.tiktok",
      label: "TikTok embed detected",
      passed: sc.hasTiktokEmbed,
      weight: 3,
    },
    {
      id: "socialCommerce.pinterest",
      label: "Pinterest integration detected",
      passed: sc.hasPinterest,
      weight: 3,
    },
    {
      id: "socialCommerce.ugcGallery",
      label: sc.ugcGalleryApp
        ? `UGC gallery: ${sc.ugcGalleryApp}`
        : "UGC gallery app detected",
      passed: sc.hasUgcGallery,
      weight: 8,
    },
    {
      id: "socialCommerce.platformCount",
      label: `${sc.platformCount} platform(s) integrated`,
      passed: sc.platformCount >= 2,
      weight: 3,
    },
  ];

  return applyLeakMerge(checks, leak);
}

/* ────────────────────────────────────────────────────────────────
   Top-level dispatch
   ──────────────────────────────────────────────────────────────── */
export function buildProductChecks(
  result: FreeResult,
  productLeaks: LeakCard[],
): DimensionCheck[] {
  const signals = result.signals;
  if (!signals) return [];
  const out: DimensionCheck[] = [];
  const leakFor = (key: string) => productLeaks.find((l) => l.key === key);

  if (signals.socialProof)
    out.push(...buildSocialProofChecks(signals.socialProof, leakFor("socialProof")));
  if (signals.structuredData)
    out.push(
      ...buildStructuredDataChecks(signals.structuredData, leakFor("structuredData")),
    );
  if (signals.checkout)
    out.push(...buildCheckoutChecks(signals.checkout, leakFor("checkout")));
  if (signals.pricing)
    out.push(...buildPricingChecks(signals.pricing, leakFor("pricing")));
  if (signals.images)
    out.push(...buildImagesChecks(signals.images, leakFor("images")));
  if (signals.title)
    out.push(...buildTitleChecks(signals.title, leakFor("title")));
  if (signals.description)
    out.push(...buildDescriptionChecks(signals.description, leakFor("description")));
  if (signals.shipping)
    out.push(...buildShippingChecks(signals.shipping, leakFor("shipping")));
  if (signals.trust)
    out.push(...buildTrustChecks(signals.trust, leakFor("trust")));
  if (signals.pageSpeed)
    out.push(...buildPageSpeedChecks(signals.pageSpeed, leakFor("pageSpeed")));
  if (signals.mobileCta)
    out.push(...buildMobileCtaChecks(signals.mobileCta, leakFor("mobileCta")));
  if (signals.crossSell)
    out.push(...buildCrossSellChecks(signals.crossSell, leakFor("crossSell")));
  if (signals.variantUx)
    out.push(...buildVariantUxChecks(signals.variantUx, leakFor("variantUx")));
  if (signals.sizeGuide)
    out.push(...buildSizeGuideChecks(signals.sizeGuide, leakFor("sizeGuide")));
  if (signals.aiDiscoverability)
    out.push(
      ...buildAiDiscoverabilityChecks(
        signals.aiDiscoverability,
        leakFor("aiDiscoverability"),
      ),
    );
  if (signals.contentFreshness)
    out.push(
      ...buildContentFreshnessChecks(
        signals.contentFreshness,
        leakFor("contentFreshness"),
      ),
    );
  if (signals.accessibility)
    out.push(
      ...buildAccessibilityChecks(signals.accessibility, leakFor("accessibility")),
    );
  if (signals.socialCommerce)
    out.push(
      ...buildSocialCommerceChecks(signals.socialCommerce, leakFor("socialCommerce")),
    );

  // Free-tier strip: backend already drops `tips`/`steps`, but
  // remediation/code stamps from leak-merge live client-side and need
  // to be removed for free / anonymous viewers.
  return result.recommendationsLocked
    ? out.map((c) => ({ ...c, remediation: undefined, code: undefined }))
    : out;
}

/* ────────────────────────────────────────────────────────────────
   Per-dimension grouped output for the AnalysisResults accordion.
   Order: worst score first (so the dimension with the most issues
   surfaces at the top and gets opened by default). Dimensions
   without any signals on the result are skipped entirely.
   ──────────────────────────────────────────────────────────────── */

type DimensionBuilder = (
  result: FreeResult,
  leak: LeakCard | undefined,
) => DimensionCheck[];

const DIMENSION_BUILDERS: Record<string, DimensionBuilder> = {
  socialProof: (r, l) =>
    r.signals?.socialProof ? buildSocialProofChecks(r.signals.socialProof, l) : [],
  structuredData: (r, l) =>
    r.signals?.structuredData ? buildStructuredDataChecks(r.signals.structuredData, l) : [],
  checkout: (r, l) =>
    r.signals?.checkout ? buildCheckoutChecks(r.signals.checkout, l) : [],
  pricing: (r, l) =>
    r.signals?.pricing ? buildPricingChecks(r.signals.pricing, l) : [],
  images: (r, l) =>
    r.signals?.images ? buildImagesChecks(r.signals.images, l) : [],
  title: (r, l) =>
    r.signals?.title ? buildTitleChecks(r.signals.title, l) : [],
  description: (r, l) =>
    r.signals?.description ? buildDescriptionChecks(r.signals.description, l) : [],
  shipping: (r, l) =>
    r.signals?.shipping ? buildShippingChecks(r.signals.shipping, l) : [],
  trust: (r, l) =>
    r.signals?.trust ? buildTrustChecks(r.signals.trust, l) : [],
  pageSpeed: (r, l) =>
    r.signals?.pageSpeed ? buildPageSpeedChecks(r.signals.pageSpeed, l) : [],
  mobileCta: (r, l) =>
    r.signals?.mobileCta ? buildMobileCtaChecks(r.signals.mobileCta, l) : [],
  crossSell: (r, l) =>
    r.signals?.crossSell ? buildCrossSellChecks(r.signals.crossSell, l) : [],
  variantUx: (r, l) =>
    r.signals?.variantUx ? buildVariantUxChecks(r.signals.variantUx, l) : [],
  sizeGuide: (r, l) =>
    r.signals?.sizeGuide ? buildSizeGuideChecks(r.signals.sizeGuide, l) : [],
  aiDiscoverability: (r, l) =>
    r.signals?.aiDiscoverability
      ? buildAiDiscoverabilityChecks(r.signals.aiDiscoverability, l)
      : [],
  contentFreshness: (r, l) =>
    r.signals?.contentFreshness
      ? buildContentFreshnessChecks(r.signals.contentFreshness, l)
      : [],
  accessibility: (r, l) =>
    r.signals?.accessibility ? buildAccessibilityChecks(r.signals.accessibility, l) : [],
  socialCommerce: (r, l) =>
    r.signals?.socialCommerce
      ? buildSocialCommerceChecks(r.signals.socialCommerce, l)
      : [],
};

export function buildProductDimensions(
  result: FreeResult,
  productLeaks: LeakCard[],
): ProductDimensionGroup[] {
  const leakFor = (key: string) => productLeaks.find((l) => l.key === key);
  const categories = result.categories as Partial<CategoryScores>;
  // When signals are stripped (free / anonymous), we still want to
  // surface the per-dimension score breakdown grid. We emit a stub
  // group for every categorized dimension; the active-dimension
  // detail surface is then rendered as a BlurredPlaceholder.
  const isLocked = !result.signals;
  const groups: ProductDimensionGroup[] = [];

  for (const [key, build] of Object.entries(DIMENSION_BUILDERS)) {
    // Only product-scope dimensions appear on the per-product surface.
    // Store-wide dimensions (pageSpeed, checkout, accessibility, etc.)
    // are owned by the storewide route — duplicating them here would
    // confuse users and dilute the storewide page's purpose.
    if (!PRODUCT_LEVEL_DIMENSIONS.has(key)) continue;

    let checks: DimensionCheck[];
    if (isLocked) {
      if (!(key in categories)) continue;
      checks = [];
    } else {
      checks = build(result, leakFor(key));
      if (checks.length === 0) continue;
    }

    // For non-fixes tiers, drop per-row fix content and mark the row
    // with `lockedFix: true` so CheckRow keeps its caret and renders
    // the upgrade-CTA blur in its expand drawer. Mirrors the
    // server-side `_strip_check_fields` shape used for store-wide
    // checks; product checks are built client-side so the strip lives
    // here.
    const stripped = result.recommendationsLocked
      ? checks.map((c) => {
          const hadFix = c.remediation !== undefined || c.code !== undefined;
          return {
            ...c,
            remediation: undefined,
            code: undefined,
            ...(hadFix ? { lockedFix: true } : {}),
          };
        })
      : checks;

    const matchingLeak = leakFor(key);
    const score = (categories[key as keyof CategoryScores] ?? 100) as number;

    groups.push({
      key,
      label: CATEGORY_LABELS[key] ?? key,
      score,
      conversionLoss: matchingLeak?.conversionLoss ?? 0,
      checks: stripped,
    });
  }

  // Worst score first — pushes the most actionable dimension to the
  // top so the default-expanded section is the one users should fix.
  // Tie-breaker: more failing checks first.
  groups.sort((a, b) => {
    if (a.score !== b.score) return a.score - b.score;
    const aFail = a.checks.filter((c) => !c.passed).length;
    const bFail = b.checks.filter((c) => !c.passed).length;
    return bFail - aFail;
  });

  return groups;
}

/* ────────────────────────────────────────────────────────────────
   buildProductGroups — pool per-dimension data into the 5 thematic
   `DIMENSION_GROUPS` buckets. Sorted by avgScore ascending (worst
   first) so the default-selected card in the Score breakdown grid
   is the one users should fix.
   ──────────────────────────────────────────────────────────────── */
export function buildProductGroups(
  result: FreeResult,
  productLeaks: LeakCard[],
): ProductGroupView[] {
  const dimensions = buildProductDimensions(result, productLeaks);
  const dimByKey = new Map(dimensions.map((d) => [d.key, d]));

  const views: ProductGroupView[] = [];

  for (const group of DIMENSION_GROUPS) {
    const dims = group.keys
      .map((k) => dimByKey.get(k as string))
      .filter((d): d is ProductDimensionGroup => d !== undefined);
    if (dims.length === 0) continue;

    const checks = dims.flatMap((d) => d.checks);
    const checkDimensionKey: Record<string, string> = {};
    for (const dim of dims) {
      for (const c of dim.checks) checkDimensionKey[c.id] = dim.key;
    }

    const avgScore = Math.round(
      dims.reduce((s, d) => s + d.score, 0) / dims.length,
    );
    const conversionLoss =
      Math.round(dims.reduce((s, d) => s + d.conversionLoss, 0) * 10) / 10;

    views.push({
      id: group.id,
      label: group.label,
      question: group.question,
      avgScore,
      conversionLoss,
      checks,
      checkDimensionKey,
      dimensions: dims,
    });
  }

  views.sort((a, b) => {
    if (a.avgScore !== b.avgScore) return a.avgScore - b.avgScore;
    const aFail = a.checks.filter((c) => !c.passed).length;
    const bFail = b.checks.filter((c) => !c.passed).length;
    return bFail - aFail;
  });

  return views;
}
