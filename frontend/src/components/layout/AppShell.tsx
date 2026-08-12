import type { ReactNode } from "react";
import type { ProjectState, ProjectSummary, OllamaStatus } from "../../types/project";
import { AnimatedBackground } from "../common/AnimatedBackground";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

interface AppShellProps {
  children: ReactNode;
  project?: ProjectState;
  projects?: ProjectSummary[];
  ollamaStatus?: OllamaStatus;
  busy?: boolean;
  onNewProject: () => void;
  onLoadProject: (projectId: string) => void;
  onDeleteProject: (project: ProjectSummary) => void;
}

export function AppShell({
  children,
  project,
  projects,
  ollamaStatus,
  busy,
  onNewProject,
  onLoadProject,
  onDeleteProject,
}: AppShellProps) {
  return (
    <div className="min-h-screen text-slate-100">
      <AnimatedBackground />
      <div className="flex min-h-screen">
        <Sidebar
          projects={projects}
          currentProjectId={project?.project_id}
          ollamaStatus={ollamaStatus}
          onNewProject={onNewProject}
          onLoadProject={onLoadProject}
          onDeleteProject={onDeleteProject}
        />
        <main className="min-w-0 flex-1">
          <Topbar project={project} busy={busy} />
          <div className="mx-auto max-w-7xl px-4 py-6 lg:px-8">{children}</div>
        </main>
      </div>
    </div>
  );
}

