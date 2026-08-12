import { FileText } from "lucide-react";
import { GlassCard } from "./GlassCard";

interface MarkdownPreviewProps {
  markdown?: string;
  title?: string;
}

export function MarkdownPreview({ markdown, title = "Markdown Preview" }: MarkdownPreviewProps) {
  const lines = (markdown || "").split(/\r?\n/);
  return (
    <GlassCard className="overflow-hidden">
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3 text-sm font-semibold text-slate-200">
        <FileText className="h-4 w-4 text-electric" />
        {title}
      </div>
      <div className="thin-scrollbar max-h-[34rem] overflow-auto p-5 text-sm leading-7 text-slate-300">
        {lines.map((line, index) => {
          if (line.startsWith("# ")) {
            return (
              <h1 key={index} className="mb-4 mt-2 text-2xl font-semibold text-white">
                {line.replace(/^# /, "")}
              </h1>
            );
          }
          if (line.startsWith("## ")) {
            return (
              <h2 key={index} className="mb-3 mt-6 text-lg font-semibold text-electric">
                {line.replace(/^## /, "")}
              </h2>
            );
          }
          if (line.startsWith("### ")) {
            return (
              <h3 key={index} className="mb-2 mt-4 text-base font-semibold text-slate-100">
                {line.replace(/^### /, "")}
              </h3>
            );
          }
          if (line.trim().startsWith("- ")) {
            return (
              <p key={index} className="pl-4 text-slate-300">
                <span className="mr-2 text-mint">-</span>
                {line.trim().replace(/^- /, "")}
              </p>
            );
          }
          if (!line.trim()) return <div key={index} className="h-3" />;
          return <p key={index}>{line}</p>;
        })}
      </div>
    </GlassCard>
  );
}

