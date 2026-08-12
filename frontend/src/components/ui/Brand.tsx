import { Link } from "react-router-dom";
import { useId } from "react";

type BrandVariant = "full" | "compact" | "icon";

interface BrandProps {
  compact?: boolean;
  variant?: BrandVariant;
  showTagline?: boolean;
  showStagePips?: boolean;
  className?: string;
  to?: string;
}

function OrbitLogo({ compact = false }: { compact?: boolean }) {
  const gradientId = useId().replace(/:/g, "");
  const sizeClass = compact ? "h-10 w-10" : "h-12 w-12";

  return (
    <span className={`orbit-logo relative grid shrink-0 place-items-center ${sizeClass}`} aria-hidden="true">
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full overflow-visible">
        <defs>
          <linearGradient id={`${gradientId}-orbit`} x1="12" y1="16" x2="88" y2="84" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="58%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="38" className="orbit-logo__halo" />
        <circle cx="50" cy="50" r="38" className="orbit-logo__ring" stroke={`url(#${gradientId}-orbit)`} />
        <circle cx="50" cy="12" r="4.8" className="orbit-logo__node orbit-logo__node-primary" />
        <circle cx="50" cy="88" r="3.6" className="orbit-logo__node orbit-logo__node-secondary" />
      </svg>
      <span className="orbit-logo__core grid place-items-center rounded-[1rem] bg-gradient-to-br from-primary via-secondary to-accent text-[0.68rem] font-black tracking-[-0.08em] text-white shadow-glow">
        AI
      </span>
    </span>
  );
}

export function Brand({
  compact = false,
  variant,
  showTagline = false,
  showStagePips = false,
  className = "",
  to = "/",
}: BrandProps) {
  const resolvedVariant: BrandVariant = variant ?? (compact ? "compact" : "full");
  const iconOnly = resolvedVariant === "icon";
  const isCompact = resolvedVariant === "compact" || iconOnly;

  return (
    <Link to={to} className={`group inline-flex items-center gap-3 rounded-2xl outline-none transition focus-visible:ring-4 focus-visible:ring-primary/25 ${className}`} aria-label="AI Builder home">
      <OrbitLogo compact={isCompact} />
      {!iconOnly ? (
        <span className="min-w-0">
          <span className="brand-wordmark block text-[1rem] font-black leading-none tracking-[-0.04em] text-text-primary">
            <span className="text-text-primary">AI</span><span className="bg-gradient-to-r from-blue-300 via-violet-300 to-cyan-300 bg-clip-text text-transparent">Builder</span>
          </span>
          <span className="mt-1 block text-[0.62rem] font-bold uppercase tracking-[0.22em] text-text-muted">
            {showTagline ? "describe -> spec -> ship" : "Production studio"}
          </span>
          {showStagePips ? (
            <span className="mt-2 flex max-w-[10.5rem] items-center gap-1" aria-hidden="true">
              {Array.from({ length: 11 }).map((_, index) => (
                <span key={index} className="brand-stage-pip h-1.5 flex-1 rounded-full bg-white/10" style={{ animationDelay: `${index * 70}ms` }} />
              ))}
            </span>
          ) : null}
        </span>
      ) : null}
    </Link>
  );
}
