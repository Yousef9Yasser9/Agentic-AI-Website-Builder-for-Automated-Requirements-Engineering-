import { AlertTriangle, X } from "lucide-react";
import { GradientButton } from "./GradientButton";

export function ConfirmModal({
  isOpen,
  onConfirm,
  onCancel,
  title,
  message,
  confirmText = "Confirm",
  variant = "default",
  loading = false,
}: {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  title: string;
  message: string;
  confirmText?: string;
  variant?: "danger" | "default";
  loading?: boolean;
}) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-[80] grid place-items-center bg-black/70 p-4 backdrop-blur-sm" role="dialog" aria-modal="true">
      <div className="glass-card w-full max-w-md animate-scale-in p-6">
        <div className="flex items-start gap-4">
          <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl ${variant === "danger" ? "bg-danger/10 text-red-300" : "bg-primary/10 text-blue-300"}`}>
            <AlertTriangle className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-bold text-white">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-text-secondary">{message}</p>
          </div>
          <button type="button" onClick={onCancel} className="rounded-lg p-1 text-text-muted hover:bg-white/5 hover:text-white" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <GradientButton variant="ghost" onClick={onCancel}>Cancel</GradientButton>
          <GradientButton variant={variant === "danger" ? "danger" : "primary"} onClick={onConfirm} loading={loading}>{confirmText}</GradientButton>
        </div>
      </div>
    </div>
  );
}
