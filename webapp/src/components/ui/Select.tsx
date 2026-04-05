import { forwardRef } from "react";

const Select = forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className = "", ...props }, ref) => (
  <select
    ref={ref}
    className={`px-3 py-2.5 text-sm rounded-xl border-[1.5px] border-[var(--border)] bg-[var(--bg)] text-[var(--text-primary)] outline-none polish-focus-ring ${className}`}
    {...props}
  />
));

Select.displayName = "Select";
export default Select;
