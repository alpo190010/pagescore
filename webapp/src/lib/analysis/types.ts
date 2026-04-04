/* ══════════════════════════════════════════════════════════════
   Types — 20 Dimensions
   ══════════════════════════════════════════════════════════════ */

export interface CategoryScores {
  pageSpeed: number;
  images: number;
  socialProof: number;
  checkout: number;
  mobileCta: number;
  title: number;
  aiDiscoverability: number;
  structuredData: number;
  pricing: number;
  description: number;
  shipping: number;
  crossSell: number;
  cartRecovery: number;
  trust: number;
  merchantFeed: number;
  socialCommerce: number;
  sizeGuide: number;
  variantUx: number;
  accessibility: number;
  contentFreshness: number;
}

export interface CompetitorResult {
  competitors: Array<{
    name: string;
    url: string;
    score: number;
    summary: string;
    categories: CategoryScores;
  }>;
}

export interface SocialProofSignals {
  reviewApp: string | null;
  starRating: number | null;
  reviewCount: number | null;
  hasPhotoReviews: boolean;
  hasVideoReviews: boolean;
  starRatingAboveFold: boolean;
  hasReviewFiltering: boolean;
}

export interface StructuredDataSignals {
  hasProductSchema: boolean;
  hasName: boolean;
  hasImage: boolean;
  hasDescription: boolean;
  hasOffers: boolean;
  hasPrice: boolean;
  hasPriceCurrency: boolean;
  hasAvailability: boolean;
  hasBrand: boolean;
  hasSku: boolean;
  hasGtin: boolean;
  hasAggregateRating: boolean;
  hasPriceValidUntil: boolean;
  hasShippingDetails: boolean;
  hasReturnPolicy: boolean;
  hasBreadcrumbList: boolean;
  hasOrganization: boolean;
  hasMissingBrand: boolean;
  hasCurrencyInPrice: boolean;
  hasInvalidAvailability: boolean;
  jsonParseErrors: number;
  duplicateProductCount: number;
}

export interface CheckoutSignals {
  hasAcceleratedCheckout: boolean;
  hasDynamicCheckoutButton: boolean;
  hasPaypal: boolean;
  hasKlarna: boolean;
  hasAfterpay: boolean;
  hasAffirm: boolean;
  hasSezzle: boolean;
  paymentMethodCount: number;
  hasDrawerCart: boolean;
  hasAjaxCart: boolean;
  hasStickyCheckout: boolean;
}

export interface PricingSignals {
  hasCompareAtPrice: boolean;
  hasStrikethroughPrice: boolean;
  priceValue: number | null;
  hasCharmPricing: boolean;
  isRoundPrice: boolean;
  hasCountdownTimer: boolean;
  hasScarcityMessaging: boolean;
  hasFakeTimerRisk: boolean;
  hasKlarnaPlacement: boolean;
  hasAfterPayBadge: boolean;
  hasShopPayInstallments: boolean;
  hasBnplNearPrice: boolean;
}

export interface ImageSignals {
  imageCount: number;
  hasVideo: boolean;
  has360View: boolean;
  hasZoom: boolean;
  hasLifestyleImages: boolean;
  cdnHosted: boolean;
  hasModernFormat: boolean;
  hasHighRes: boolean;
  altTextScore: number;
}

export interface TitleSignals {
  h1Text: string | null;
  metaTitle: string | null;
  brandName: string | null;
  h1Count: number;
  h1Length: number;
  metaTitleLength: number;
  hasH1: boolean;
  hasSingleH1: boolean;
  hasBrandInTitle: boolean;
  hasKeywordStuffing: boolean;
  isAllCaps: boolean;
  hasPromotionalText: boolean;
  h1MetaDiffer: boolean;
  hasSpecifics: boolean;
}

export interface ShippingSignals {
  hasFreeShipping: boolean;
  hasFreeShippingThreshold: boolean;
  freeShippingThresholdValue: number | null;
  hasDeliveryDate: boolean;
  hasDeliveryEstimate: boolean;
  hasEddApp: boolean;
  hasShippingCostShown: boolean;
  hasShippingInStructuredData: boolean;
  hasShippingPolicyLink: boolean;
  hasReturnsMentioned: boolean;
}

export interface DescriptionSignals {
  descriptionFound: boolean;
  wordCount: number;
  fleschKincaidGrade: number;
  avgSentenceLength: number;
  sentenceCount: number;
  benefitRatio: number;
  benefitWordCount: number;
  featureWordCount: number;
  emotionalDensity: number;
  htmlTagVariety: number;
  hasHeadings: boolean;
  hasBulletLists: boolean;
  hasEmphasis: boolean;
}

export interface TrustSignals {
  trustBadgeApp: string | null;
  trustBadgeCount: number;
  hasPaymentIcons: boolean;
  hasMoneyBackGuarantee: boolean;
  hasReturnPolicy: boolean;
  hasFreeShippingBadge: boolean;
  hasSecureCheckoutText: boolean;
  hasSecurityBadge: boolean;
  hasSafeCheckoutBadge: boolean;
  hasLiveChat: boolean;
  hasPhoneNumber: boolean;
  hasContactEmail: boolean;
  hasTrustNearAtc: boolean;
  trustElementCount: number;
}

export interface DimensionSignals {
  socialProof?: SocialProofSignals;
  structuredData?: StructuredDataSignals;
  checkout?: CheckoutSignals;
  pricing?: PricingSignals;
  images?: ImageSignals;
  title?: TitleSignals;
  shipping?: ShippingSignals;
  description?: DescriptionSignals;
  trust?: TrustSignals;
}

export interface FreeResult {
  score: number;
  summary: string;
  tips: string[];
  /** Per-dimension tips keyed by dimension slug (e.g. socialProof, structuredData) */
  dimensionTips?: Record<string, string[]>;
  categories: CategoryScores;
  productPrice: number;
  productCategory: string;
  estimatedMonthlyVisitors: number;
  signals?: DimensionSignals;
}

/** Shape of each entry returned by `buildLeaks` */
export interface LeakCard {
  key: string;
  catScore: number;
  impact: string;
  revenue: string;
  revenueLow: number;
  revenueHigh: number;
  tip: string;
  problem: string;
  category: string;
  revenueImpact: string;
}
