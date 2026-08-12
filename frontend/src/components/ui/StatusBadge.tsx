import clsx from "clsx";
import type { ReactNode } from "react";

type Tone = "success" | "current" | "pending" | "error" | "generating" | "neutral" | "warning";

interface StatusBadgeProps {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}

export function StatusBadge({ children, tone = "neutral", className }: StatusBadgeProps) {
  const tones: Record<Tone, string> = {
    success: "border-mint/35 bg-mint/10 text-mint",
    current: "border-electric/35 bg-electric/10 text-electric",
    pending: "border-slate-500/25 bg-slate-500/10 text-slate-300",
    error: "border-rose-400/35 bg-rose-400/10 text-rose-300",
    generating:
      "border-pulse/40 bg-[linear-gradient(90deg,rgba(56,189,248,.16),rgba(139,92,246,.18),rgba(52,211,153,.12))] bg-[length:200%_100%] text-slate-100 animate-shimmer",
    neutral: "border-white/12 bg-white/8 text-slate-300",
    warning: "border-ember/35 bg-ember/10 text-ember",
  };

  return (
    <span
      className={clsx(
        "inline-flex max-w-full items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold",
        tones[tone],
        className,
      )}
    >
      <span className="truncate">{children}</span>
    </span>
  );
}

