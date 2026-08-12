import type { ProjectSummary } from "../../types/project";
import { EmptyState } from "../ui/EmptyState";
import { ProjectCard } from "./ProjectCard";

interface ProjectListProps {
  projects?: ProjectSummary[];
  currentProjectId?: string;
  onLoad: (projectId: string) => void;
  onDelete: (project: ProjectSummary) => void;
}

export function ProjectList({ projects = [], currentProjectId, onLoad, onDelete }: ProjectListProps) {
  if (!projects.length) {
    return <EmptyState title="No saved projects" description="Your generated workflow checkpoints will appear here." />;
  }
  return (
    <div className="thin-scrollbar flex max-h-[22rem] flex-col gap-2 overflow-auto pr-1">
      {projects.map((project) => (
        <ProjectCard
          key={project.project_id}
          project={project}
          active={project.project_id === currentProjectId}
          onLoad={() => onLoad(project.project_id)}
          onDelete={() => onDelete(project)}
        />
      ))}
    </div>
  );
}

