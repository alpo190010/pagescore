"use client";

import { TrendUpIcon } from "@phosphor-icons/react";

interface RevenueLossCardProps {
  lossLow: number;
  lossHigh: number;
  onViewBreakdown: () => void;
  variant?: "compact" | "full";
}

export default function RevenueLossCard({
  lossLow,
  lossHigh,
  onViewBreakdown,
  variant = "compact",
}: RevenueLossCardProps) {
  const full = variant === "full";

  return (
    <div
      className={`${full ? "md:col-span-4 p-8" : "md:col-span-5 p-6 sm:p-8"} rounded-3xl text-white flex flex-col justify-between`}
      style={{
        background: "var(--gradient-error)",
        boxShadow: "var(--shadow-error)",
        animation: "fade-in-up 500ms var(--ease-out-quart) both",
      }}
    >
      <div className="space-y-2">
        <TrendUpIcon size={full ? 32 : 28} weight="regular" color="white" className="opacity-50" />
        <h3 className={`${full ? "text-base sm:text-lg" : "text-sm sm:text-base"} font-semibold opacity-80 leading-tight`}>
          Estimated Monthly Revenue Loss for This Product
        </h3>
      </div>
      <div className={`space-y-1 ${full ? "my-6" : "my-4"}`}>
        <div
          className="font-extrabold tracking-tighter"
          style={{
            fontSize: full ? "clamp(28px, 5vw, 44px)" : "clamp(24px, 4vw, 36px)",
            fontFamily: "var(--font-manrope), Manrope, sans-serif",
          }}
        >
          -${lossLow.toLocaleString()}&ndash;${lossHigh.toLocaleString()}
        </div>
        <p className="text-sm font-medium opacity-70">Based on estimated traffic to this product</p>
      </div>
      <button
        type="button"
        onClick={onViewBreakdown}
        className={`cursor-pointer w-full ${full ? "py-3" : "py-2.5"} bg-white/10 backdrop-blur-md rounded-xl font-bold border border-white/20 hover:bg-white/20 transition-all text-sm`}
      >
        View Issue Breakdown &darr;
      </button>
    </div>
  );
}
