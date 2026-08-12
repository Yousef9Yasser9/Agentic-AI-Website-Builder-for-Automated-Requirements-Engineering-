import type { ReactNode } from "react";

export function PageWrapper({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`animate-fade-in-up ${className}`}>{children}</div>;
}
