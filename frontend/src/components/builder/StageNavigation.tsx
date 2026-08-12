import { ArrowLeft, ArrowRight } from "lucide-react";
import type { ProjectState, StageKey } from "../../types/project";
import { canMoveNext, nextStage, previousStage, stageIndex } from "../../utils/stageUtils";
import { WORKFLOW_STAGES } from "../../types/workflow";
import { GradientButton } from "../ui/GradientButton";

interface StageNavigationProps {
  project?: ProjectState;
  activeStage: StageKey;
  onStageChange: (stage: StageKey) => void;
}

export function StageNavigation({ project, activeStage, onStageChange }: StageNavigationProps) {
  const index = stageIndex(activeStage);
  const hasPrevious = index > 0;
  const hasNext = index < WORKFLOW_STAGES.length - 1;
  return (
    <div className="mt-6 flex items-center justify-between gap-3">
      <GradientButton variant="secondary" disabled={!hasPrevious} onClick={() => onStageChange(previousStage(activeStage))}>
        <ArrowLeft className="h-4 w-4" />
        Back
      </GradientButton>
      <GradientButton disabled={!hasNext || !canMoveNext(project, activeStage)} onClick={() => onStageChange(nextStage(activeStage))}>
        Next
        <ArrowRight className="h-4 w-4" />
      </GradientButton>
    </div>
  );
}

