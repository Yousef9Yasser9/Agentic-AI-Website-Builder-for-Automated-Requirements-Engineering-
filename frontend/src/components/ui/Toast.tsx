import { AlertTriangle, CheckCircle2, Info, X, XCircle } from "lucide-react";
import { useToastStore, type ToastType } from "../../stores/toastStore";

const iconMap = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
} satisfies Record<ToastType, typeof Info>;

const toneMap: Record<ToastType, string> = {
  success: "border-success/30 text-success",
  error: "border-danger/30 text-danger",
  warning: "border-warning/30 text-warning",
  info: "border-primary/30 text-blue-300",
};

export function ToastContainer() {
  const toasts = useToastStore((state) => state.toasts);
  const removeToast = useToastStore((state) => state.removeToast);

  return (
    <div className="pointer-events-none fixed right-4 top-4 z-[100] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-3">
      {toasts.map((toast) => {
        const Icon = iconMap[toast.type];
        return (
          <div key={toast.id} className={`pointer-events-auto animate-slide-in-right rounded-2xl border bg-surface-2/95 p-4 shadow-panel backdrop-blur-xl ${toneMap[toast.type]}`} role="status">
            <div className="flex items-start gap-3">
              <Icon className="mt-0.5 h-5 w-5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-text-primary">{toast.title}</p>
                {toast.description ? <p className="mt-1 text-sm leading-5 text-text-secondary">{toast.description}</p> : null}
              </div>
              <button type="button" className="rounded-lg p-1 text-text-muted transition hover:bg-white/5 hover:text-white" onClick={() => removeToast(toast.id)} aria-label="Dismiss notification">
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
