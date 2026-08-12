import { AlertTriangle } from "lucide-react";

export function ErrorState({ message }: { message?: string }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-rose-400/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
      <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" />
      <span>{message || "Something went wrong."}</span>
    </div>
  );
}

