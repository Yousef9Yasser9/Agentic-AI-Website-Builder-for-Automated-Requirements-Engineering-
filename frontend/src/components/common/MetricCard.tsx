import type { LucideIcon } from "lucide-react";
import { GlassCard } from "../ui/GlassCard";

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  accent?: string;
}

export function MetricCard({ label, value, icon: Icon, accent = "text-electric" }: MetricCardProps) {
  return (
    <GlassCard className="p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
        </div>
        <Icon className={`h-5 w-5 ${accent}`} />
      </div>
    </GlassCard>
  );
}

