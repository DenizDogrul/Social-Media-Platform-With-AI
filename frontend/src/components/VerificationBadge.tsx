type VerificationBadgeProps = {
  verified?: boolean;
  compact?: boolean;
};

export default function VerificationBadge({ verified, compact = false }: VerificationBadgeProps) {
  if (!verified) return null;

  return (
    <span
      className={compact ? "verification-badge verification-badge-compact" : "verification-badge"}
      title="Verified account"
      aria-label="Verified account"
    >
      Verified
    </span>
  );
}
