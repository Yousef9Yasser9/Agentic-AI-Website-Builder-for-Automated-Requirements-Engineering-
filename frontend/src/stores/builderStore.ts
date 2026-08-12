import { create } from "zustand";
import type { StageKey } from "../types/project";

interface BuilderStore {
  currentProjectId?: string;
  activeStage: StageKey;
  sidebarOpen: boolean;
  setCurrentProjectId: (projectId?: string) => void;
  setActiveStage: (stage: StageKey) => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useBuilderStore = create<BuilderStore>((set) => ({
  currentProjectId: undefined,
  activeStage: "PLAIN_TEXT",
  sidebarOpen: false,
  setCurrentProjectId: (projectId) => set({ currentProjectId: projectId }),
  setActiveStage: (stage) => set({ activeStage: stage }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));

