import type { LucideIcon } from "lucide-react";
import { GlassCard } from "../ui/GlassCard";

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export function FeatureCard({ icon: Icon, title, description }: FeatureCardProps) {
  return (
    <GlassCard className="p-5 transition hover:-translate-y-1 hover:border-electric/35">
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg border border-electric/20 bg-electric/10 text-electric">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="text-base font-semibold text-white">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-400">{description}</p>
    </GlassCard>
  );
}

