export function LoadingSpinner({
  variant = "spinner",
  className = "",
}: {
  variant?: "spinner" | "dots" | "skeleton";
  className?: string;
}) {
  if (variant === "dots") {
    return (
      <span className={`inline-flex items-center gap-1 ${className}`} aria-label="Loading">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:120ms]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:240ms]" />
      </span>
    );
  }
  if (variant === "skeleton") {
    return <span className={`block animate-shimmer rounded-xl bg-[linear-gradient(90deg,rgba(255,255,255,.04),rgba(255,255,255,.1),rgba(255,255,255,.04))] bg-[length:200%_100%] ${className}`} />;
  }
  return <span className={`inline-block h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`} aria-label="Loading" />;
}
