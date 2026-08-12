import clsx from "clsx";
import type { HTMLAttributes, ReactNode } from "react";

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  hover?: boolean;
  padding?: "none" | "sm" | "md" | "lg";
  intensity?: "soft" | "medium" | "strong";
}

export function GlassCard({
  children,
  className,
  hover = false,
  padding = "none",
  intensity = "soft",
  ...props
}: GlassCardProps) {
  const paddingClasses = { none: "", sm: "p-4", md: "p-6", lg: "p-8" };
  return (
    <div
      className={clsx(
        "glass-card",
        hover && "glass-card-hover",
        paddingClasses[padding],
        intensity === "strong"
          ? "bg-surface-2/90"
          : intensity === "medium"
            ? "bg-surface/85"
            : "bg-surface/70",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
