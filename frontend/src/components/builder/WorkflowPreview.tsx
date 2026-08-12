import { WORKFLOW_STAGES } from "../../types/workflow";
import type { ProjectState, StageKey } from "../../types/project";

type WorkflowPreviewProps = {
  project?: ProjectState;
  activeStage?: StageKey;
  variant?: "compact" | "full" | string;
};

export function WorkflowPreview({ project, activeStage = "PLAIN_TEXT", variant = "compact" }: WorkflowPreviewProps) {
  const compact = variant === "compact";
  const visibleStages = compact ? WORKFLOW_STAGES.slice(0, 8) : WORKFLOW_STAGES;

  return (
    <div className={compact ? "grid gap-3 sm:grid-cols-2" : "grid gap-3 sm:grid-cols-2 lg:grid-cols-4"}>
      {visibleStages.map((stage, index) => {
        const Icon = stage.icon;
        const done = Boolean(project?.project_data?.[stage.doneKey]);
        const active = stage.key === activeStage;
        return (
          <div
            key={stage.key}
            className={[
              "rounded-lg border p-4 transition",
              done ? "border-success/25 bg-success/10" : active ? "border-primary/35 bg-primary/10" : "border-white/10 bg-white/[0.045]",
            ].join(" ")}
          >
            <div className="mb-4 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">{String(index + 1).padStart(2, "0")}</span>
              <Icon className={done ? "h-4 w-4 text-success" : active ? "h-4 w-4 text-blue-300" : "h-4 w-4 text-electric"} />
            </div>
            <p className="text-sm font-semibold text-white">{stage.label}</p>
            {!compact ? <p className="mt-2 text-xs leading-5 text-slate-500">{stage.description}</p> : null}
          </div>
        );
      })}
    </div>
  );
}
