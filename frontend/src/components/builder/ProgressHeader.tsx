import { CircleDashed } from "lucide-react";
import type { ProjectState, StageKey } from "../../types/project";
import { WORKFLOW_STAGES } from "../../types/workflow";
import { getStageMeta, stageIndex } from "../../utils/stageUtils";
import { GlassCard } from "../ui/GlassCard";
import { StatusBadge } from "../ui/StatusBadge";
import { ProgressBar } from "../ui/ProgressBar";

interface ProgressHeaderProps {
  project?: ProjectState;
  activeStage: StageKey;
}

export function ProgressHeader({ project, activeStage }: ProgressHeaderProps) {
  const index = stageIndex(activeStage);
  const meta = getStageMeta(activeStage);
  const completeCount = WORKFLOW_STAGES.filter((stage) => Boolean(project?.project_data?.[stage.doneKey])).length;
  const percent = Math.round((completeCount / WORKFLOW_STAGES.length) * 100);
  const Icon = meta.icon;
  return (
    <GlassCard className="mb-4 overflow-hidden p-5">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-4">
          <div className="grid h-12 w-12 flex-none place-items-center rounded-lg border border-electric/25 bg-electric/10 text-electric">
            <Icon className="h-6 w-6" />
          </div>
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <StatusBadge tone="current">Stage {index + 1} of {WORKFLOW_STAGES.length}</StatusBadge>
              <StatusBadge tone="neutral">{completeCount} complete</StatusBadge>
            </div>
            <h1 className="truncate text-2xl font-semibold text-white">{meta.label}</h1>
            <p className="mt-1 text-sm text-slate-400">{meta.description}</p>
          </div>
        </div>
        <div className="w-full max-w-sm">
          <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-2">
              <CircleDashed className="h-3.5 w-3.5" />
              Workflow progress
            </span>
            <span>{percent}%</span>
          </div>
          <ProgressBar value={percent} />
        </div>
      </div>
    </GlassCard>
  );
}
