import { CheckCircle2 } from "lucide-react";

export function SuccessState({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-mint/25 bg-mint/10 px-4 py-3 text-sm text-mint">
      <CheckCircle2 className="h-4 w-4" />
      {message}
    </div>
  );
}

