import { Loader2 } from "lucide-react";

export function LoadingState({ label = "Working" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-electric/20 bg-electric/10 px-4 py-3 text-sm text-electric">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

