import type { ReactNode } from "react";

interface SimpleLayoutProps {
  children: ReactNode;
}

export function SimpleLayout({ children }: SimpleLayoutProps) {
  return (
    <div className="min-h-screen">
      {children}
    </div>
  );
}
