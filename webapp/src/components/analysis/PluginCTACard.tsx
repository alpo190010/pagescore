"use client";

import { StorefrontIcon, ArrowRightIcon } from "@phosphor-icons/react";

interface PluginCTACardProps {
  variant?: "compact" | "full";
  onViewBreakdown: () => void;
}

export default function PluginCTACard({
  variant = "compact",
  onViewBreakdown,
}: PluginCTACardProps) {
  const full = variant === "full";

  return (
    <div
      className={`${full ? "md:col-span-4 p-8" : "md:col-span-5 p-6 sm:p-8"} rounded-3xl flex flex-col justify-between relative overflow-hidden`}
      style={{
        background: "linear-gradient(145deg, var(--primary) 0%, var(--primary-light) 55%, var(--primary) 100%)",
        boxShadow: "var(--shadow-brand-md)",
        animation: "fade-in-up 500ms var(--ease-out-quart) both",
      }}
    >
      {/* Subtle diagonal line texture */}
      <div
        className="absolute inset-0 opacity-[0.035] pointer-events-none"
        style={{
          backgroundImage:
            "repeating-linear-gradient(135deg, transparent, transparent 20px, rgba(255,255,255,0.5) 20px, rgba(255,255,255,0.5) 21px)",
        }}
      />

      <div className="relative z-10 space-y-2">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center border border-white/10">
            <StorefrontIcon
              size={full ? 20 : 18}
              weight="regular"
              className="text-white/70"
            />
          </div>
          <span className="text-[11px] font-bold uppercase tracking-widest text-white/40">
            Shopify Plugin
          </span>
        </div>
        <h3
          className={`${full ? "text-lg sm:text-xl" : "text-base sm:text-lg"} font-extrabold text-white leading-tight`}
          style={{ fontFamily: "var(--font-manrope), Manrope, sans-serif" }}
        >
          See your real dollar impact
        </h3>
      </div>

      <p
        className={`relative z-10 text-white/55 leading-relaxed ${full ? "text-sm my-5" : "text-[13px] my-4"}`}
      >
        Connect your Shopify store to turn conversion scores into
        real revenue estimates based on your actual traffic &amp; sales data.
      </p>

      <button
        type="button"
        onClick={onViewBreakdown}
        className={`relative z-10 cursor-pointer group w-full ${full ? "py-3" : "py-2.5"} rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 bg-white text-[var(--primary)] hover:bg-white/90 active:scale-[0.98]`}
      >
        Connect Your Store
        <ArrowRightIcon
          size={14}
          weight="bold"
          className="transition-transform group-hover:translate-x-0.5"
        />
      </button>
    </div>
  );
}
