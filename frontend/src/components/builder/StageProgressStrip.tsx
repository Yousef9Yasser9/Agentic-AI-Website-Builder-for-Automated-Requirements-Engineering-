import { clsx } from "clsx";
import type { ProjectState, ProjectSummary, StageKey } from "../../types/project";
import { stageOrder, WORKFLOW_STAGES } from "../../types/workflow";

type StageProgressStripProps = {
  project?: ProjectState | ProjectSummary;
  activeStage?: StageKey;
  className?: string;
};

function isDone(project: ProjectState | ProjectSummary | undefined, doneKey: string, stageKey: StageKey) {
  if (!project) return false;
  if (project.project_data && Boolean(project.project_data[doneKey])) return true;
  const activeIndex = stageOrder.indexOf((project.stage as StageKey) || "PLAIN_TEXT");
  const stageIndex = stageOrder.indexOf(stageKey);
  return activeIndex > stageIndex;
}

export function StageProgressStrip({ project, activeStage, className }: StageProgressStripProps) {
  const current = activeStage || (project?.stage as StageKey | undefined) || "PLAIN_TEXT";

  return (
    <div className={clsx("flex items-center gap-1.5", className)} aria-label="Workflow stage progress">
      {WORKFLOW_STAGES.map((stage) => {
        const active = stage.key === current;
        const done = isDone(project, stage.doneKey, stage.key);
        return (
          <span
            key={stage.key}
            title={stage.label}
            className={clsx(
              "h-2 flex-1 rounded-full transition",
              done && "bg-success",
              active && !done && "bg-gradient-to-r from-primary to-secondary",
              !done && !active && "bg-white/10",
            )}
          />
        );
      })}
    </div>
  );
}
