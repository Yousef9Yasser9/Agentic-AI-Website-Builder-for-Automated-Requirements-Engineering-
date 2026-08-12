import { Plus, Sparkles, X } from "lucide-react";
import type { ProjectSummary } from "../../types/project";
import type { OllamaStatus } from "../../types/project";
import { useBuilderStore } from "../../stores/builderStore";
import { GradientButton } from "../ui/GradientButton";
import { ProjectList } from "../projects/ProjectList";
import { ModelSettingsPanel } from "../settings/ModelSettingsPanel";
import { OllamaStatusBadge } from "../settings/OllamaStatusBadge";
import { CleanupPanel } from "../settings/CleanupPanel";

interface SidebarProps {
  projects?: ProjectSummary[];
  currentProjectId?: string;
  ollamaStatus?: OllamaStatus;
  onNewProject: () => void;
  onLoadProject: (projectId: string) => void;
  onDeleteProject: (project: ProjectSummary) => void;
}

export function Sidebar({
  projects,
  currentProjectId,
  ollamaStatus,
  onNewProject,
  onLoadProject,
  onDeleteProject,
}: SidebarProps) {
  const sidebarOpen = useBuilderStore((state) => state.sidebarOpen);
  const setSidebarOpen = useBuilderStore((state) => state.setSidebarOpen);
  return (
    <>
      {sidebarOpen ? <button className="fixed inset-0 z-30 bg-black/60 lg:hidden" onClick={() => setSidebarOpen(false)} type="button" /> : null}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-[22rem] max-w-[calc(100vw-1rem)] flex-col border-r border-white/10 bg-slate-950/88 p-4 backdrop-blur-2xl transition lg:sticky lg:top-0 lg:z-10 lg:h-screen lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-5 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-lg border border-electric/30 bg-electric/10 text-electric">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">AI Website Builder</p>
              <p className="text-xs text-slate-500">Local generation studio</p>
            </div>
          </div>
          <button className="rounded-md p-2 text-slate-400 lg:hidden" onClick={() => setSidebarOpen(false)} type="button" title="Close">
            <X className="h-5 w-5" />
          </button>
        </div>

        <GradientButton className="mb-4 w-full" onClick={onNewProject}>
          <Plus className="h-4 w-4" />
          New Project
        </GradientButton>

        <div className="mb-5">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Projects</p>
            <OllamaStatusBadge status={ollamaStatus} />
          </div>
          <ProjectList projects={projects} currentProjectId={currentProjectId} onLoad={onLoadProject} onDelete={onDeleteProject} />
        </div>

        <div className="thin-scrollbar flex-1 space-y-5 overflow-auto pr-1">
          <section>
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Models</p>
            <ModelSettingsPanel />
          </section>
          <section>
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Maintenance</p>
            <CleanupPanel />
          </section>
        </div>
      </aside>
    </>
  );
}

