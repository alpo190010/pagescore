type StatusVariant = "success" | "error" | "email";

interface StatusIconProps {
  variant: StatusVariant;
}

const wrapperStyles: Record<StatusVariant, string> = {
  success:
    "bg-[var(--success-light)] border border-[var(--success-border)]",
  error:
    "bg-[var(--error-light)] border border-[var(--error-border-light)]",
  email:
    "bg-[var(--success-light)] border border-[var(--success-border)]",
};

const strokeColors: Record<StatusVariant, string> = {
  success: "var(--success)",
  error: "var(--error)",
  email: "var(--success)",
};

function IconPath({ variant }: { variant: StatusVariant }) {
  switch (variant) {
    case "success":
      return <polyline points="20 6 9 17 4 12" />;
    case "error":
      return (
        <>
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </>
      );
    case "email":
      return (
        <>
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <polyline points="22,4 12,13 2,4" />
        </>
      );
  }
}

export default function StatusIcon({ variant }: StatusIconProps) {
  return (
    <div
      className={`w-14 h-14 mx-auto rounded-full flex items-center justify-center ${wrapperStyles[variant]}`}
    >
      <svg
        width="28"
        height="28"
        viewBox="0 0 24 24"
        fill="none"
        stroke={strokeColors[variant]}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <IconPath variant={variant} />
      </svg>
    </div>
  );
}
