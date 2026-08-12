import { Clock3, FolderOpen, Trash2 } from "lucide-react";
import clsx from "clsx";
import type { ProjectSummary } from "../../types/project";
import { formatDate } from "../../utils/formatters";
import { StatusBadge } from "../ui/StatusBadge";

interface ProjectCardProps {
  project: ProjectSummary;
  active?: boolean;
  onLoad: () => void;
  onDelete: () => void;
}

export function ProjectCard({ project, active, onLoad, onDelete }: ProjectCardProps) {
  return (
    <div
      className={clsx(
        "rounded-lg border p-3 transition",
        active ? "border-electric/45 bg-electric/10" : "border-white/10 bg-white/[0.035] hover:border-white/20",
      )}
    >
      <div className="flex items-start gap-3">
        <button
          className="min-w-0 flex-1 text-left"
          onClick={onLoad}
          type="button"
          title="Load project"
        >
          <div className="flex items-center gap-2">
            <FolderOpen className="h-4 w-4 flex-none text-electric" />
            <p className="truncate text-sm font-semibold text-white">{project.project_title || project.project_id}</p>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <Clock3 className="h-3.5 w-3.5" />
            <span>{formatDate(project.saved_at)}</span>
          </div>
          <div className="mt-3">
            <StatusBadge tone={active ? "current" : "pending"}>{project.stage}</StatusBadge>
          </div>
        </button>
        <button
          className="rounded-md p-2 text-slate-500 transition hover:bg-rose-500/10 hover:text-rose-300"
          onClick={onDelete}
          title="Delete project"
          type="button"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

