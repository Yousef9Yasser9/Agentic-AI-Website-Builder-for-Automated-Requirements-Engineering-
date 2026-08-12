import type { ReactNode } from "react";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info" | "purple";

const styles: Record<BadgeVariant, string> = {
  default: "border-white/10 bg-white/5 text-text-secondary",
  success: "border-success/25 bg-success/10 text-emerald-300",
  warning: "border-warning/25 bg-warning/10 text-amber-300",
  danger: "border-danger/25 bg-danger/10 text-red-300",
  info: "border-primary/25 bg-primary/10 text-blue-300",
  purple: "border-secondary/25 bg-secondary/10 text-violet-300",
};

export function Badge({
  children,
  variant = "default",
  size = "sm",
  className = "",
}: {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: "sm" | "md";
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${styles[variant]} ${size === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm"} ${className}`}>
      {children}
    </span>
  );
}
