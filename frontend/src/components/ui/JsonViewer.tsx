import { Braces, Copy } from "lucide-react";
import { asJson } from "../../utils/formatters";
import { GlassCard } from "./GlassCard";

interface JsonViewerProps {
  value: unknown;
  title?: string;
  maxHeight?: string;
}

export function JsonViewer({ value, title = "Raw JSON", maxHeight = "max-h-96" }: JsonViewerProps) {
  const text = asJson(value);
  return (
    <GlassCard className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <Braces className="h-4 w-4 text-electric" />
          {title}
        </div>
        <button
          className="rounded-md p-2 text-slate-400 transition hover:bg-white/8 hover:text-white"
          onClick={() => navigator.clipboard.writeText(text)}
          title="Copy JSON"
          type="button"
        >
          <Copy className="h-4 w-4" />
        </button>
      </div>
      <pre className={`thin-scrollbar overflow-auto ${maxHeight} p-4 text-xs leading-5 text-slate-300`}>
        <code>{text}</code>
      </pre>
    </GlassCard>
  );
}

