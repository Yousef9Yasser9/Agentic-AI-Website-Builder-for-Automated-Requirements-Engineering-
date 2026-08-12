import { Menu, Save, Sparkles } from "lucide-react";
import type { ProjectState } from "../../types/project";
import { compactPath } from "../../utils/formatters";
import { useBuilderStore } from "../../stores/builderStore";
import { StatusBadge } from "../ui/StatusBadge";

interface TopbarProps {
  project?: ProjectState;
  busy?: boolean;
}

export function Topbar({ project, busy }: TopbarProps) {
  const setSidebarOpen = useBuilderStore((state) => state.setSidebarOpen);
  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-ink/72 px-4 py-3 backdrop-blur-xl lg:px-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <button
            className="rounded-md border border-white/10 p-2 text-slate-300 lg:hidden"
            onClick={() => setSidebarOpen(true)}
            type="button"
            title="Open sidebar"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">{project?.project_title || "AI Website Builder"}</p>
            <p className="truncate text-xs text-slate-500">{project ? compactPath(project.checkpoint_path) : "No active checkpoint"}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge tone={busy ? "generating" : "success"}>
            {busy ? <Sparkles className="h-3.5 w-3.5" /> : <Save className="h-3.5 w-3.5" />}
            {busy ? "AI Active" : "Auto Saved"}
          </StatusBadge>
          {project?.server_port ? <StatusBadge tone="neutral">Port {project.server_port}</StatusBadge> : null}
        </div>
      </div>
    </header>
  );
}

