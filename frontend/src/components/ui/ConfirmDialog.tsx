import { AlertTriangle } from "lucide-react";
import { GradientButton } from "./GradientButton";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ open, title, description, onConfirm, onCancel }: ConfirmDialogProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-lg border border-white/12 bg-slate-950 p-5 shadow-panel">
        <div className="mb-4 flex items-center gap-3">
          <div className="rounded-lg border border-ember/30 bg-ember/10 p-2 text-ember">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <h3 className="text-lg font-semibold text-white">{title}</h3>
        </div>
        <p className="text-sm leading-6 text-slate-400">{description}</p>
        <div className="mt-5 flex justify-end gap-3">
          <GradientButton variant="ghost" onClick={onCancel}>
            Cancel
          </GradientButton>
          <GradientButton variant="danger" onClick={onConfirm}>
            Delete
          </GradientButton>
        </div>
      </div>
    </div>
  );
}

