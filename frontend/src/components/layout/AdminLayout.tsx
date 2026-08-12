import type { ReactNode } from "react";
import { PageHeader } from "../ui/PageHeader";
import { PageWrapper } from "./PageWrapper";

export function AdminLayout({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <PageWrapper>
      <PageHeader title={title} subtitle={subtitle} eyebrow="Admin Panel" />
      {children}
    </PageWrapper>
  );
}
