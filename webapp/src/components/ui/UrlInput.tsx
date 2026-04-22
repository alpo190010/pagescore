"use client";

import {
  forwardRef,
  useId,
  type FormEvent,
  type InputHTMLAttributes,
  type ReactNode,
} from "react";
import { GlobeIcon, LinkIcon } from "@phosphor-icons/react";
import Button, { type ButtonSize } from "./Button";

/* DS URL pill — the branded input used on the landing hero and any
   "paste-your-store" entry point.

   Two variants:
   - `pill` (default, compact)  — DS · Components spec: 420px max-width, small
     text, sm button. For docs, in-page "try it" slots, and tight contexts.
   - `hero`                    — DS · Landing Page spec: mobile-responsive
     (stacks column → row at sm), larger text, lg button. Fills its container. */

type UrlInputVariant = "pill" | "hero";

export interface UrlInputProps
  extends Omit<
    InputHTMLAttributes<HTMLInputElement>,
    "onSubmit" | "size" | "prefix"
  > {
  value: string;
  onValueChange?: (value: string) => void;
  onSubmit?: (value: string) => void;
  ctaLabel?: string;
  /** Optional trailing content inside the submit button (e.g. an arrow). */
  ctaTrailing?: ReactNode;
  submitting?: boolean;
  submitDisabled?: boolean;
  hideSubmit?: boolean;
  variant?: UrlInputVariant;
  wrapperClassName?: string;
  errorId?: string;
}

const UrlInput = forwardRef<HTMLInputElement, UrlInputProps>(
  (
    {
      value,
      onValueChange,
      onChange,
      onSubmit,
      ctaLabel = "Scan",
      ctaTrailing,
      submitting = false,
      submitDisabled = false,
      hideSubmit = false,
      variant = "pill",
      wrapperClassName = "",
      className = "",
      placeholder = "https://yourstore.com",
      errorId,
      ...rest
    },
    ref,
  ) => {
    const reactId = useId();
    const inputId = rest.id ?? `url-input-${reactId}`;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      onValueChange?.(e.target.value);
      onChange?.(e);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && onSubmit) {
        e.preventDefault();
        onSubmit(value);
      }
      rest.onKeyDown?.(e);
    };

    const handleSubmitClick = (e: FormEvent) => {
      e.preventDefault();
      onSubmit?.(value);
    };

    const isHero = variant === "hero";

    const wrapperClass = isHero
      ? `flex flex-col sm:flex-row w-full p-2 bg-[var(--paper)] border border-[var(--rule-2)] rounded-2xl sm:rounded-full shadow-[var(--shadow-subtle)] focus-within:border-[var(--ink)] transition-colors ${wrapperClassName}`
      : `flex items-center w-full max-w-[420px] bg-[var(--paper)] border border-[var(--rule-2)] rounded-full shadow-[var(--shadow-subtle)] focus-within:border-[var(--ink)] transition-colors pl-5 pr-1.5 py-1.5 gap-2.5 ${wrapperClassName}`;

    const inputClass = isHero
      ? `min-w-0 flex-1 bg-transparent border-0 outline-none text-[var(--ink)] placeholder:text-[var(--ink-3)] text-base sm:text-lg px-4 py-3 sm:py-0 ${className}`
      : `min-w-0 flex-1 bg-transparent border-0 outline-none text-[var(--ink)] placeholder:text-[var(--ink-3)] text-[14px] ${className}`;

    const btnSize: ButtonSize = isHero ? "lg" : "sm";
    const btnClass = isHero ? "w-full sm:w-auto" : "shrink-0";

    return (
      <div className={wrapperClass}>
        {isHero ? (
          <span className="hidden sm:flex items-center pl-6 pr-2 text-[var(--ink-3)] shrink-0">
            <LinkIcon size={20} weight="regular" aria-hidden />
          </span>
        ) : (
          <GlobeIcon
            size={16}
            weight="regular"
            className="shrink-0 text-[var(--ink-3)]"
            aria-hidden
          />
        )}

        <input
          ref={ref}
          id={inputId}
          type="text"
          inputMode="url"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          placeholder={placeholder}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          aria-describedby={errorId}
          aria-label={rest["aria-label"] ?? "Product page URL"}
          {...rest}
          className={inputClass}
        />

        {!hideSubmit && (
          <Button
            type="submit"
            variant="primary"
            size={btnSize}
            disabled={submitting || submitDisabled}
            onClick={handleSubmitClick}
            className={btnClass}
          >
            {submitting ? "Loading..." : ctaLabel}
            {!submitting && ctaTrailing}
          </Button>
        )}
      </div>
    );
  },
);

UrlInput.displayName = "UrlInput";
export default UrlInput;
