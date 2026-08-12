import clsx from "clsx";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";

interface TimelineItem {
  label: string;
  done?: boolean;
  active?: boolean;
}

export function GenerationTimeline({ items }: { items: TimelineItem[] }) {
  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={item.label} className="flex items-center gap-3">
          <div
            className={clsx(
              "grid h-8 w-8 place-items-center rounded-md border",
              item.done ? "border-mint/30 bg-mint/10 text-mint" : item.active ? "border-electric/35 bg-electric/10 text-electric" : "border-white/10 bg-white/5 text-slate-500",
            )}
          >
            {item.done ? <CheckCircle2 className="h-4 w-4" /> : item.active ? <Loader2 className="h-4 w-4 animate-spin" /> : <Circle className="h-4 w-4" />}
          </div>
          <div className="min-w-0 flex-1">
            <p className={clsx("text-sm font-semibold", item.done ? "text-mint" : item.active ? "text-white" : "text-slate-400")}>{item.label}</p>
            {index < items.length - 1 ? <div className="mt-3 h-px bg-white/10" /> : null}
          </div>
        </div>
      ))}
    </div>
  );
}

