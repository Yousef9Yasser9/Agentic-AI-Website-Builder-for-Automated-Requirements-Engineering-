import { Terminal } from "lucide-react";
import { GlassCard } from "./GlassCard";

interface CodeBlockProps {
  code?: string;
  title?: string;
}

export function CodeBlock({ code = "", title = "Code" }: CodeBlockProps) {
  return (
    <GlassCard className="overflow-hidden">
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3 text-sm font-semibold text-slate-200">
        <Terminal className="h-4 w-4 text-mint" />
        {title}
      </div>
      <pre className="thin-scrollbar max-h-96 overflow-auto p-4 text-xs leading-5 text-slate-300">
        <code>{code || "No output yet."}</code>
      </pre>
    </GlassCard>
  );
}

