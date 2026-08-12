import clsx from "clsx";
import { Check } from "lucide-react";
import type { ProjectState, StageKey } from "../../types/project";
import { WORKFLOW_STAGES } from "../../types/workflow";
import { isStageComplete, stageIndex } from "../../utils/stageUtils";

interface StageStepperProps {
  project?: ProjectState;
  activeStage: StageKey;
  onStageChange: (stage: StageKey) => void;
}

export function StageStepper({ project, activeStage, onStageChange }: StageStepperProps) {
  const activeIndex = stageIndex(activeStage);
  return (
    <div className="thin-scrollbar -mx-1 flex gap-2 overflow-x-auto px-1 pb-2">
      {WORKFLOW_STAGES.map((stage, index) => {
        const complete = isStageComplete(project, stage.key);
        const active = stage.key === activeStage;
        const Icon = stage.icon;
        return (
          <button
            key={stage.key}
            className={clsx(
              "group flex min-w-36 items-center gap-3 rounded-lg border px-3 py-3 text-left transition",
              active
                ? "border-electric/55 bg-electric/12 text-white"
                : complete
                  ? "border-mint/30 bg-mint/8 text-slate-200"
                  : index <= activeIndex + 1
                    ? "border-white/12 bg-white/[0.035] text-slate-300 hover:border-electric/30"
                    : "border-white/8 bg-white/[0.02] text-slate-500",
            )}
            onClick={() => onStageChange(stage.key)}
            type="button"
          >
            <span
              className={clsx(
                "grid h-8 w-8 flex-none place-items-center rounded-md border",
                complete ? "border-mint/30 bg-mint/10 text-mint" : active ? "border-electric/35 bg-electric/10 text-electric" : "border-white/10 bg-slate-950/50",
              )}
            >
              {complete ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold">{stage.shortLabel}</span>
              <span className="block truncate text-xs text-slate-500">{index + 1}. {stage.label}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

