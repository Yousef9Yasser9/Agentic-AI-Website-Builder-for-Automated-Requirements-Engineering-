import clsx from "clsx";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

interface GradientButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  loading?: boolean;
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  icon?: ReactNode;
  fullWidth?: boolean;
}

export function GradientButton({
  children,
  loading,
  variant = "primary",
  size = "md",
  icon,
  fullWidth = false,
  className,
  disabled,
  ...props
}: GradientButtonProps) {
  const variants = {
    primary: "border-transparent bg-gradient-to-r from-primary to-secondary text-white hover:shadow-glow",
    secondary: "border-white/10 bg-white/[0.06] text-text-primary hover:border-white/20 hover:bg-white/10",
    danger: "border-danger/30 bg-danger/10 text-red-300 hover:bg-danger/20",
    ghost: "border-transparent bg-transparent text-text-secondary hover:bg-white/5 hover:text-white",
  };

  const sizes = {
    sm: "min-h-9 px-3.5 py-2 text-xs",
    md: "min-h-10 px-5 py-2.5 text-sm",
    lg: "min-h-12 px-7 py-3.5 text-base",
  };

  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-xl border font-semibold transition-all duration-200 hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:translate-y-0",
        variants[variant],
        sizes[size],
        fullWidth && "w-full",
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
      <span className="truncate">{children}</span>
    </button>
  );
}
