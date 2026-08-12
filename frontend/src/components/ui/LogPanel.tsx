import { useEffect, useRef } from "react";
import { Activity, Copy } from "lucide-react";
import { GlassCard } from "./GlassCard";

interface LogPanelProps {
  logs?: string[];
  title?: string;
  subtitle?: string;
}

function toneFor(line: string) {
  const text = line.toLowerCase();
  if (text.includes("error") || text.includes("failed") || text.includes("traceback")) return "text-red-300";
  if (text.includes("warn") || text.includes("retry") || text.includes("timeout")) return "text-amber-300";
  if (text.includes("success") || text.includes("completed") || text.includes("passed")) return "text-emerald-300";
  return "text-slate-300";
}

export function LogPanel({ logs = [], title = "Live Logs", subtitle = "This can take a few minutes on local Ollama models." }: LogPanelProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const text = logs.length ? logs.join("\n") : "Waiting for activity...";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [logs.length]);

  return (
    <GlassCard className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <Activity className="h-4 w-4 text-mint" />
            {title}
          </div>
          <p className="mt-1 text-xs text-text-muted">{subtitle}</p>
        </div>
        <button
          className="rounded-md p-2 text-slate-400 transition hover:bg-white/8 hover:text-white"
          onClick={() => navigator.clipboard.writeText(text)}
          title="Copy logs"
          type="button"
        >
          <Copy className="h-4 w-4" />
        </button>
      </div>
      <div className="thin-scrollbar max-h-[28rem] min-h-52 overflow-auto bg-slate-950/60 p-4 font-mono text-xs leading-5">
        {logs.length ? logs.map((line, index) => (
          <p key={`${index}-${line.slice(0, 18)}`} className={toneFor(line)}>
            <span className="mr-2 text-slate-600">{String(index + 1).padStart(3, "0")}</span>
            {line}
          </p>
        )) : <p className="text-slate-500">Waiting for activity...</p>}
        <div ref={bottomRef} />
      </div>
    </GlassCard>
  );
}
