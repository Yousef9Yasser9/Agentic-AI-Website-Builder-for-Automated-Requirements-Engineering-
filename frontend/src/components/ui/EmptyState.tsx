import type { LucideIcon } from "lucide-react";
import { Sparkles } from "lucide-react";
import { FloatingOrbs } from "../common/FloatingOrbs";
import { GlassCard } from "./GlassCard";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({ title, description, icon: Icon = Sparkles, actionLabel, onAction }: EmptyStateProps) {
  return (
    <GlassCard className="relative overflow-hidden p-10 text-center">
      <FloatingOrbs density="subtle" />
      <div className="relative z-10 mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-blue-300 shadow-depth-1">
        <Icon className="h-6 w-6" />
      </div>
      <div className="relative z-10">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-text-secondary">{description}</p>
        {actionLabel && onAction ? <button type="button" onClick={onAction} className="btn-primary mt-6">{actionLabel}</button> : null}
      </div>
    </GlassCard>
  );
}
