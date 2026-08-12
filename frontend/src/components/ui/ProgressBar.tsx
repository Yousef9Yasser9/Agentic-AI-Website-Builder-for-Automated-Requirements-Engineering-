export function ProgressBar({
  value,
  showLabel = false,
  animated = false,
  className = "",
}: {
  value: number;
  showLabel?: boolean;
  animated?: boolean;
  color?: string;
  className?: string;
}) {
  const normalized = Math.max(0, Math.min(100, value));
  return (
    <div className={className}>
      {showLabel ? <div className="mb-2 text-right text-xs font-semibold text-text-secondary">{normalized}%</div> : null}
      <progress className={`premium-progress ${animated ? "animate-pulse" : ""}`} value={normalized} max={100} aria-label={`${normalized}% complete`} />
    </div>
  );
}
