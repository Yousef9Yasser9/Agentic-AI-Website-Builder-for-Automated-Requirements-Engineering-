import { Sparkles } from "lucide-react";

interface PromptEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function PromptEditor({ value, onChange, placeholder }: PromptEditorProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-white/12 bg-slate-950/72 shadow-panel">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <Sparkles className="h-4 w-4 text-electric" />
          Project Prompt
        </div>
        <span className="text-xs text-slate-500">{value.length} characters</span>
      </div>
      <textarea
        className="thin-scrollbar min-h-[22rem] w-full resize-y bg-transparent p-5 text-base leading-7 text-slate-100 outline-none placeholder:text-slate-600"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={
          placeholder ||
          "Build a rental platform where admins manage inventory, customers reserve items, payments are tracked, and dashboards show revenue and active bookings."
        }
      />
    </div>
  );
}

