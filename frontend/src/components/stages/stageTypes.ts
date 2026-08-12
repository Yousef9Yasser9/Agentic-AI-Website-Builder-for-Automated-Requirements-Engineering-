import type { ProjectState, StageKey } from "../../types/project";

export interface StageProps {
  project?: ProjectState;
  onProjectChange: (project: ProjectState) => void;
  onStageChange: (stage: StageKey) => void;
}

