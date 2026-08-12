import { WORKFLOW_STAGES, stageOrder } from "../types/workflow";
import type { ProjectState, StageKey } from "../types/project";

export function stageIndex(stage: StageKey | string | undefined) {
  const index = stageOrder.indexOf(stage as StageKey);
  return index < 0 ? 0 : index;
}

export function getStageMeta(stage: StageKey | string | undefined) {
  return WORKFLOW_STAGES[stageIndex(stage)];
}

export function isStageComplete(project: ProjectState | undefined, stage: StageKey) {
  const meta = WORKFLOW_STAGES.find((item) => item.key === stage);
  if (!meta || !project) return false;
  return Boolean(project.project_data?.[meta.doneKey]);
}

export function canMoveNext(project: ProjectState | undefined, stage: StageKey) {
  return isStageComplete(project, stage);
}

export function nextStage(stage: StageKey) {
  const index = stageIndex(stage);
  return stageOrder[Math.min(stageOrder.length - 1, index + 1)];
}

export function previousStage(stage: StageKey) {
  const index = stageIndex(stage);
  return stageOrder[Math.max(0, index - 1)];
}

